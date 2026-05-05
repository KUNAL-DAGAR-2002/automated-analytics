from pathlib import Path
from io import BytesIO

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from scripts.data_cleaning.calculated_columns import add_age_groups, add_total_price
from scripts.data_cleaning.null_and_duplicate_handling import (
    handle_duplicates,
    handle_null_values,
)
from scripts.filter.apply_filter import apply_filters
from scripts.kpi.kpi import (
    average_order_value,
    customer_lifetime_value,
    purachese_frequency,
    refund_rate,
    repeat_customer,
    total_customers,
    total_orders,
    total_revenue,
    total_units_sold,
)
from scripts.views.age_wise import (
    metric_wise_average_order_value,
    revenue_contib_by_metric,
)
from scripts.views.views import top_bottom


REQUIRED_COLUMNS = [
    "Invoice",
    "StockCode",
    "Description",
    "Quantity",
    "Price",
    "Country",
    "cust_id",
    "date",
    "Age",
    "Gender",
]
UNAVAILABLE_COLUMN = "Column not available in dataset"
DATA_DIR = Path(__file__).resolve().parent / "data"
COLUMN_ALIASES = {
    "Invoice": ["Invoice", "Transaction ID", "Order ID", "OrderID", "InvoiceNo"],
    "StockCode": ["StockCode", "Stock Code", "ITEM CODE", "SKU", "Product ID"],
    "Description": [
        "Description",
        "product",
        "Product",
        "Product Category",
        "ITEM DESCRIPTION",
        "Item Description",
    ],
    "Quantity": ["Quantity", "Qty", "Units", "RETAIL SALES"],
    "Price": ["Price", "Price per Unit", "Unit Price", "Amount", "Total Amount"],
    "Country": ["Country", "Region", "Location", "Market"],
    "cust_id": ["cust_id", "Customer ID", "CustomerID", "Customer Id"],
    "date": ["date", "Date", "InvoiceDate"],
    "Age": ["Age", "Customer Age"],
    "Gender": ["Gender", "Sex"],
}


st.set_page_config(
    page_title="Automated Analytics Dashboard",
    layout="wide",
)


@st.cache_data(show_spinner=False)
def read_csv_file(path: str) -> pd.DataFrame:
    return pd.read_csv(path, encoding="utf-8", low_memory=False)


@st.cache_data(show_spinner=False)
def read_uploaded_csv(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_csv(BytesIO(file_bytes), encoding="utf-8", low_memory=False)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    if "Description" not in df.columns and "product" in df.columns:
        df["Description"] = df["product"]
    if "product" not in df.columns and "Description" in df.columns:
        df["product"] = df["Description"]

    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce").fillna(0)
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce").fillna(0)
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")
    df["Gender"] = df["Gender"].fillna("Unknown")
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = handle_duplicates(df)
    df = handle_null_values(df)
    df = add_total_price(df)
    df = add_age_groups(df)
    return df.dropna(how="all")


def get_data_files() -> list[Path]:
    return sorted(DATA_DIR.glob("*.csv"))


def get_default_mapping_column(required_column: str, uploaded_columns: list[str]) -> str:
    lower_lookup = {column.lower(): column for column in uploaded_columns}
    for alias in COLUMN_ALIASES.get(required_column, [required_column]):
        if alias in uploaded_columns:
            return alias
        if alias.lower() in lower_lookup:
            return lower_lookup[alias.lower()]
    return UNAVAILABLE_COLUMN


def validate_columns(df: pd.DataFrame) -> list[str]:
    return sorted(set(REQUIRED_COLUMNS) - set(df.columns))


def build_column_mapping(uploaded_df: pd.DataFrame) -> dict[str, str]:
    uploaded_columns = uploaded_df.columns.tolist()
    mapping_options = [UNAVAILABLE_COLUMN] + uploaded_columns
    mapping = {}

    st.subheader("Map Columns")
    label_col, mapping_col = st.columns([1, 2])
    with label_col:
        st.markdown("**Required column**")
    with mapping_col:
        st.markdown("**CSV column**")

    for required_column in REQUIRED_COLUMNS:
        row_label_col, row_mapping_col = st.columns([1, 2])
        default_column = get_default_mapping_column(required_column, uploaded_columns)
        default_index = mapping_options.index(default_column)
        state_key = f"map_{required_column}"
        if st.session_state.get(state_key) not in mapping_options:
            st.session_state[state_key] = mapping_options[default_index]

        with row_label_col:
            display_name = "Product" if required_column == "Description" else required_column
            st.write(display_name)
        with row_mapping_col:
            mapping[required_column] = st.selectbox(
                f"Map {display_name}",
                mapping_options,
                index=default_index,
                key=state_key,
                label_visibility="collapsed",
            )

    return mapping


def apply_column_mapping(uploaded_df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    mapped_columns = {}
    row_count = len(uploaded_df)
    for required_column, uploaded_column in mapping.items():
        if uploaded_column != UNAVAILABLE_COLUMN:
            mapped_columns[required_column] = uploaded_df[uploaded_column]
        elif required_column in {"Invoice", "cust_id"}:
            mapped_columns[required_column] = pd.RangeIndex(1, row_count + 1)
        elif required_column in {"Quantity", "Price"}:
            mapped_columns[required_column] = 0
        elif required_column == "Age":
            mapped_columns[required_column] = pd.NA
        elif required_column == "date":
            mapped_columns[required_column] = pd.NaT
        else:
            mapped_columns[required_column] = "Unknown"

    mapped_df = pd.DataFrame(mapped_columns)
    mapped_df["product"] = mapped_df["Description"]
    return mapped_df


def get_available_columns(mapping: dict[str, str]) -> set[str]:
    return {
        required_column
        for required_column, uploaded_column in mapping.items()
        if uploaded_column != UNAVAILABLE_COLUMN
    }


def get_display_label(mapping: dict[str, str], required_column: str, fallback: str) -> str:
    uploaded_column = mapping.get(required_column)
    if uploaded_column and uploaded_column != UNAVAILABLE_COLUMN:
        if required_column == "Description" and uploaded_column == "Description":
            return "Product"
        return uploaded_column
    return fallback


def get_mapping_signature(mapping: dict[str, str]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(mapping.items()))


def get_processed_data(
    source_signature: str,
    uploaded_df: pd.DataFrame,
    column_mapping: dict[str, str],
) -> pd.DataFrame:
    processing_key = (source_signature, get_mapping_signature(column_mapping))
    if st.session_state.get("processed_data_key") != processing_key:
        mapped_df = apply_column_mapping(uploaded_df, column_mapping)
        missing_columns = validate_columns(mapped_df)
        if missing_columns:
            st.error("Please map all required columns before continuing.")
            st.stop()

        st.session_state.processed_data = clean_data(mapped_df)
        st.session_state.processed_data_key = processing_key

    return st.session_state.processed_data.copy()


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def format_decimal(value: float) -> str:
    return f"{value:,.2f}"


def format_percent(value: float) -> str:
    return f"{value * 100:,.2f}%"


def build_kpis(
    filtered_df: pd.DataFrame,
    original_df: pd.DataFrame,
    clv_period: int | None,
) -> list[tuple[str, str]]:
    if filtered_df.empty:
        return [
            ("Total Revenue", format_currency(0)),
            ("Total Orders", "0"),
            ("Average Order Value", format_currency(0)),
            ("Units Sold", "0"),
            ("Refund Rate", "0.00%"),
            ("Customers", "0"),
            ("New Customers", "0.00%"),
            ("Returning Customers", "0.00%"),
            ("Purchase Frequency", "0.00"),
            ("Customer Lifetime Value", format_currency(0)),
        ]

    revenue = total_revenue(filtered_df)
    orders = total_orders(filtered_df)
    avg_order = average_order_value(filtered_df, revenue, orders) if orders else 0
    units_sold = total_units_sold(filtered_df)
    refunds = refund_rate(filtered_df) if orders else 0
    customers = total_customers(filtered_df)
    has_date_values = "date" in filtered_df.columns and filtered_df["date"].notna().any()
    new_customers, returning_customers = (
        repeat_customer(filtered_df) if customers and has_date_values else (0, 0)
    )
    frequency = purachese_frequency(filtered_df) if customers else 0

    try:
        lifetime_value = (
            customer_lifetime_value(
                original_df,
                period=clv_period,
                average_order_value=avg_order,
                purchase_frequency=frequency,
            )
            if clv_period is not None and frequency and has_date_values
            else 0
        )
    except (ZeroDivisionError, ValueError):
        lifetime_value = 0

    return [
        ("Total Revenue", format_currency(revenue)),
        ("Total Orders", format_number(orders)),
        ("Average Order Value", format_currency(avg_order)),
        ("Units Sold", format_number(units_sold)),
        ("Refund Rate", format_percent(refunds)),
        ("Customers", format_number(customers)),
        ("New Customers", f"{new_customers:,.2f}%"),
        ("Returning Customers", f"{returning_customers:,.2f}%"),
        ("Purchase Frequency", format_decimal(frequency)),
        ("Customer Lifetime Value", format_currency(lifetime_value)),
    ]


def render_kpis(kpis: list[tuple[str, str]]) -> None:
    for start in range(0, len(kpis), 5):
        cols = st.columns(5)
        for col, (label, value) in zip(cols, kpis[start : start + 5]):
            col.metric(label, value)


def render_date_trend(df: pd.DataFrame, date_part: str, date_label: str) -> None:
    month_labels = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    chart_df = df.copy()
    chart_df[date_part] = getattr(chart_df["date"].dt, date_part)
    chart_df = (
        chart_df.groupby(date_part, as_index=False)["total_price"]
        .sum()
        .sort_values(date_part)
    )

    if date_part == "month":
        chart_df[date_part] = chart_df[date_part].map(month_labels)
    else:
        chart_df[date_part] = chart_df[date_part].astype(str)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.lineplot(data=chart_df, x=date_part, y="total_price", marker="o", ax=ax)
    ax.set_xlabel(date_label)
    ax.set_ylabel("Revenue")
    ax.set_title(f"Revenue Trend by {date_label} ({date_part.title()})")
    ax.grid(True, alpha=0.25)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_product_bar(df: pd.DataFrame, top_or_bottom: str, product_label: str) -> None:
    product_df = top_bottom(
        df,
        top_or_bottom=top_or_bottom,
        n=10,
        on="product",
        metric="total_price",
    ).reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=product_df, x="total_price", y="product", ax=ax)
    ax.set_xlabel("Revenue")
    ax.set_ylabel(product_label)
    ax.set_title(f"{top_or_bottom.title()} 10 {product_label} by Revenue")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_customer_mix(df: pd.DataFrame) -> None:
    customers = total_customers(df)
    has_date_values = "date" in df.columns and df["date"].notna().any()
    new_customers, returning_customers = (
        repeat_customer(df) if customers and has_date_values else (0, 0)
    )

    fig, ax = plt.subplots(figsize=(7, 7))
    ax.pie(
        [new_customers, returning_customers],
        labels=["New Customers", "Returning Customers"],
        autopct="%1.1f%%",
        startangle=140,
    )
    ax.set_title("Customer Mix")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_metric_view(df: pd.DataFrame, metric: str, metric_label: str, view_type: str) -> None:
    if view_type == "average_order_value":
        metric_df = metric_wise_average_order_value(df, metric)
        value_col = "average_order_value"
        y_label = "Average Order Value"
        title = f"Average Order Value by {metric_label}"
    else:
        metric_df = revenue_contib_by_metric(df, metric)
        value_col = "revenue_contribution"
        y_label = "Revenue Contribution (%)"
        title = f"Revenue Contribution by {metric_label}"

    metric_df = metric_df.sort_values(value_col, ascending=False)

    fig, ax = plt.subplots(figsize=(12, 5))
    sns.barplot(data=metric_df, x=metric, y=value_col, ax=ax)
    ax.set_xlabel(metric_label)
    ax.set_ylabel(y_label)
    ax.set_title(title)
    ax.tick_params(axis="x", rotation=25)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    display_df = metric_df.copy()
    if value_col == "revenue_contribution":
        display_df[value_col] = display_df[value_col].map(lambda value: f"{value:,.2f}%")
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def reset_filters() -> None:
    defaults = {
        "product_filter": [],
        "country_filter": "All",
        "gender_filter": [],
    }
    if has_age:
        defaults["age_filter"] = (age_min, age_max)
    if has_date:
        defaults.update(
            {
                "day_token": "between",
                "month_token": "between",
                "year_token": "between",
                "day_between": (day_min, day_max),
                "month_between": (month_min, month_max),
                "year_between": (year_min, year_max),
                "day_value": day_min,
                "month_value": month_min,
                "year_value": year_min,
            }
        )
    for key, value in defaults.items():
        st.session_state[key] = value


def clamp_slider_range(value: tuple[int, int], min_value: int, max_value: int) -> tuple[int, int]:
    if not isinstance(value, tuple) or len(value) != 2:
        return (min_value, max_value)
    start = min(max(int(value[0]), min_value), max_value)
    end = min(max(int(value[1]), min_value), max_value)
    return (start, end) if start <= end else (min_value, max_value)


def clamp_slider_value(value: int, min_value: int, max_value: int) -> int:
    try:
        return min(max(int(value), min_value), max_value)
    except (TypeError, ValueError):
        return min_value


def sync_filter_state() -> None:
    valid_tokens = {"between", "more", "less", "equal"}

    if has_product and "product_filter" not in st.session_state:
        st.session_state.product_filter = []
    elif has_product:
        st.session_state.product_filter = [
            product for product in st.session_state.product_filter if product in products
        ]

    if has_country and st.session_state.get("country_filter") not in countries:
        st.session_state.country_filter = "All"

    if has_gender and "gender_filter" not in st.session_state:
        st.session_state.gender_filter = []
    elif has_gender:
        st.session_state.gender_filter = [
            gender for gender in st.session_state.gender_filter if gender in genders
        ]

    if has_age:
        st.session_state.age_filter = clamp_slider_range(
            st.session_state.get("age_filter"),
            age_min,
            age_max,
        )

    if not has_date:
        return

    for filter_type, min_value, max_value in [
        ("day", day_min, day_max),
        ("month", month_min, month_max),
        ("year", year_min, year_max),
    ]:
        token_key = f"{filter_type}_token"
        between_key = f"{filter_type}_between"
        value_key = f"{filter_type}_value"

        if st.session_state.get(token_key) not in valid_tokens:
            st.session_state[token_key] = "between"
        st.session_state[between_key] = clamp_slider_range(
            st.session_state.get(between_key),
            min_value,
            max_value,
        )
        st.session_state[value_key] = clamp_slider_value(
            st.session_state.get(value_key),
            min_value,
            max_value,
        )


def date_filter_control(label: str, filter_type: str, min_value: int, max_value: int) -> dict:
    token = st.selectbox(
        f"{label} condition",
        ["between", "more", "less", "equal"],
        key=f"{filter_type}_token",
    )

    if token == "between":
        value = st.slider(
            label,
            min_value,
            max_value,
            (min_value, max_value),
            key=f"{filter_type}_between",
        )
        data = [int(value[0]), int(value[1])]
    else:
        value = st.slider(
            label,
            min_value,
            max_value,
            min_value,
            key=f"{filter_type}_value",
        )
        data = [int(value)]

    return {"type": filter_type, "data": data, "token": token}


st.title("Automated Analytics Dashboard")

data_files = get_data_files()
data_source_options = [file.name for file in data_files] + ["Upload CSV"]

with st.sidebar:
    st.header("Data Source")
    selected_source = st.radio(
        "Choose a CSV",
        data_source_options,
        label_visibility="collapsed",
    )
    uploaded_file = None
    if selected_source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if selected_source == "Upload CSV":
    if uploaded_file is None:
        st.info("Upload a CSV file in the sidebar to start building the dashboard.")
        st.stop()

    uploaded_bytes = uploaded_file.getvalue()
    uploaded_df = read_uploaded_csv(uploaded_bytes)
    source_name = uploaded_file.name
    source_signature = f"upload:{uploaded_file.name}:{len(uploaded_bytes)}"
else:
    selected_path = next(file for file in data_files if file.name == selected_source)
    uploaded_df = read_csv_file(str(selected_path))
    source_name = selected_path.name
    source_signature = f"data:{selected_path.name}:{selected_path.stat().st_mtime_ns}:{selected_path.stat().st_size}"

if st.session_state.get("source_signature") != source_signature:
    st.session_state.source_signature = source_signature
    st.session_state.mapping_locked = False
    st.session_state.column_mapping = {}
    st.session_state.pop("processed_data", None)
    st.session_state.pop("processed_data_key", None)
    for required_column in REQUIRED_COLUMNS:
        st.session_state.pop(f"map_{required_column}", None)

mapping_locked = st.session_state.get("mapping_locked", False)
with st.expander("Column Mapping", expanded=not mapping_locked):
    if mapping_locked:
        st.caption("Mappings are locked.")
        st.json(st.session_state.column_mapping)
        if st.button("Edit Mapping"):
            st.session_state.mapping_locked = False
            st.rerun()
    else:
        column_mapping = build_column_mapping(uploaded_df)
        st.json(column_mapping)
        if st.button("Apply Mapping"):
            st.session_state.column_mapping = column_mapping
            st.session_state.mapping_locked = True
            st.rerun()

if not st.session_state.get("mapping_locked", False):
    st.info("Map the uploaded CSV columns, then click Apply Mapping.")
    st.stop()

column_mapping = st.session_state.column_mapping
available_columns = get_available_columns(column_mapping)

df = get_processed_data(source_signature, uploaded_df, column_mapping)
st.caption(f"Using file: {source_name}")

original_df = df.copy()

if df.empty:
    st.error("No usable rows found. Please upload a CSV with valid values.")
    st.stop()

has_product = "Description" in available_columns
has_country = "Country" in available_columns
has_date = "date" in available_columns and df["date"].notna().any()
has_age = "Age" in available_columns and df["Age"].notna().any()
has_gender = "Gender" in available_columns
product_label = get_display_label(column_mapping, "Description", "Product")
country_label = get_display_label(column_mapping, "Country", "Country")
date_label = get_display_label(column_mapping, "date", "Date")
age_label = get_display_label(column_mapping, "Age", "Age")
age_group_label = f"{age_label} Group"
gender_label = get_display_label(column_mapping, "Gender", "Gender")

if has_date:
    day_min = int(df["date"].dt.day.min())
    day_max = int(df["date"].dt.day.max())
    month_min = int(df["date"].dt.month.min())
    month_max = int(df["date"].dt.month.max())
    year_min = int(df["date"].dt.year.min())
    year_max = int(df["date"].dt.year.max())
if has_country:
    countries = ["All"] + sorted(df["Country"].dropna().unique().tolist())
if has_product:
    products = sorted(df["product"].dropna().unique().tolist())
if has_age:
    age_min = int(df["Age"].min())
    age_max = int(df["Age"].max())
if has_gender:
    genders = sorted(df["Gender"].dropna().unique().tolist())

sync_filter_state()

st.button("Remove Filters", on_click=reset_filters)

filters = []
filter_slots = []

if has_product:
    filter_slots.append("product")
if has_country:
    filter_slots.append("country")
if has_age:
    filter_slots.append("age")
if has_gender:
    filter_slots.append("gender")
if has_date:
    filter_slots.extend(["day", "month", "year"])

if filter_slots:
    filter_cols = st.columns(len(filter_slots))
else:
    filter_cols = []

for filter_name, filter_col in zip(filter_slots, filter_cols):
    with filter_col:
        if filter_name == "product":
            selected_products = st.multiselect(
                product_label,
                products,
                key="product_filter",
            )
            if selected_products:
                filters.append({"type": "product", "data": selected_products})
        elif filter_name == "country":
            country = st.selectbox(country_label, countries, key="country_filter")
            if country != "All":
                filters.append({"type": "country", "data": [country]})
        elif filter_name == "age":
            age_range = st.slider(
                age_label,
                age_min,
                age_max,
                (age_min, age_max),
                key="age_filter",
            )
            filters.append(
                {"type": "age", "data": [int(age_range[0]), int(age_range[1])]}
            )
        elif filter_name == "gender":
            selected_genders = st.multiselect(
                gender_label,
                genders,
                key="gender_filter",
            )
            if selected_genders:
                filters.append({"type": "gender", "data": selected_genders})
        elif filter_name == "day":
            filters.append(date_filter_control(f"{date_label} Day", "day", day_min, day_max))
        elif filter_name == "month":
            filters.append(date_filter_control(f"{date_label} Month", "month", month_min, month_max))
        elif filter_name == "year":
            filters.append(date_filter_control(f"{date_label} Year", "year", year_min, year_max))

filtered_df = apply_filters(df, filters) if filters else df

with st.expander("Current filter JSON"):
    st.json(filters)

if has_date:
    clv_year_min = int(original_df["date"].dt.year.min())
    clv_year_max = int(original_df["date"].dt.year.max())
    clv_period = st.number_input(
        "CLV Period Year",
        min_value=clv_year_min,
        max_value=clv_year_max,
        value=clv_year_min,
        step=1,
    )
else:
    clv_period = None

st.subheader("KPIs")
render_kpis(build_kpis(filtered_df, original_df, clv_period))

st.subheader("Views")
if filtered_df.empty:
    st.warning("No records match the selected filters.")
else:
    chart_tab, metric_tab, data_tab = st.tabs(
        ["Charts", "Metric Wise", "Filtered Data"]
    )

    with chart_tab:
        first_row_left, first_row_right = st.columns(2)
        with first_row_left:
            if has_date:
                trend_part = st.radio(
                    f"{date_label} trend level",
                    ["year", "month", "day"],
                    horizontal=True,
                )
                render_date_trend(filtered_df, trend_part, date_label)
            else:
                st.info("Date trend is hidden because date is not mapped.")
        with first_row_right:
            if has_product:
                render_product_bar(filtered_df, "top", product_label)
            else:
                st.info("Top products chart is hidden because product is not mapped.")

        second_row_left, second_row_right = st.columns(2)
        with second_row_left:
            if has_product:
                render_product_bar(filtered_df, "bottom", product_label)
            else:
                st.info("Bottom products chart is hidden because product is not mapped.")
        with second_row_right:
            if has_date:
                render_customer_mix(filtered_df)
            else:
                st.info("Customer mix is hidden because date is not mapped.")

    with metric_tab:
        metric_options = []
        if has_age:
            metric_options.append(("age_group", age_group_label))
        if has_gender:
            metric_options.append(("Gender", gender_label))
        if has_product:
            metric_options.append(("product", product_label))
        if has_country:
            metric_options.append(("Country", country_label))

        if not metric_options:
            st.info("Metric-wise view is hidden because no metric columns are mapped.")
        else:
            metric_labels = {metric: label for metric, label in metric_options}
            selected_metric = st.radio(
                "Metric",
                [metric for metric, _ in metric_options],
                format_func=lambda metric: metric_labels[metric],
                horizontal=True,
            )
            selected_label = metric_labels[selected_metric]

            revenue_col, aov_col = st.columns(2)
            with revenue_col:
                render_metric_view(
                    filtered_df,
                    selected_metric,
                    selected_label,
                    "revenue_contribution",
                )
            with aov_col:
                render_metric_view(
                    filtered_df,
                    selected_metric,
                    selected_label,
                    "average_order_value",
                )

    with data_tab:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
