from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import streamlit as st

from scripts.data_cleaning.calculated_columns import add_total_price
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
from scripts.views.views import top_bottom


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "cleaned_data.csv"


st.set_page_config(
    page_title="Automated Analytics Dashboard",
    layout="wide",
)


@st.cache_data
def load_default_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH, encoding="utf-8", low_memory=False)
    return clean_data(df)


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = handle_duplicates(df)
    df = handle_null_values(df)
    df = add_total_price(df)
    return df.dropna(subset=["date"])


def validate_columns(df: pd.DataFrame) -> list[str]:
    required_columns = {
        "Invoice",
        "StockCode",
        "Description",
        "Quantity",
        "Price",
        "Country",
        "cust_id",
        "date",
    }
    return sorted(required_columns - set(df.columns))


def format_currency(value: float) -> str:
    return f"${value:,.2f}"


def format_number(value: float) -> str:
    return f"{value:,.0f}"


def format_decimal(value: float) -> str:
    return f"{value:,.2f}"


def format_percent(value: float) -> str:
    return f"{value * 100:,.2f}%"


def build_kpis(filtered_df: pd.DataFrame, original_df: pd.DataFrame) -> list[tuple[str, str]]:
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
    new_customers, returning_customers = repeat_customer(filtered_df) if customers else (0, 0)
    frequency = purachese_frequency(filtered_df) if customers else 0

    years = sorted(original_df["date"].dt.year.dropna().unique())
    clv_period = int(years[0]) if years else None
    try:
        lifetime_value = (
            customer_lifetime_value(
                original_df,
                period=clv_period,
                average_order_value=avg_order,
                purchase_frequency=frequency,
            )
            if clv_period is not None and frequency
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


def render_date_trend(df: pd.DataFrame, date_part: str) -> None:
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
    ax.set_xlabel(date_part.title())
    ax.set_ylabel("Revenue")
    ax.set_title(f"Revenue Trend by {date_part.title()}")
    ax.grid(True, alpha=0.25)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_product_bar(df: pd.DataFrame, top_or_bottom: str) -> None:
    product_df = top_bottom(
        df,
        top_or_bottom=top_or_bottom,
        n=10,
        on="Description",
        metric="total_price",
    ).reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))
    sns.barplot(data=product_df, x="total_price", y="Description", ax=ax)
    ax.set_xlabel("Revenue")
    ax.set_ylabel("Product")
    ax.set_title(f"{top_or_bottom.title()} 10 Products by Revenue")
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)


def render_customer_mix(df: pd.DataFrame) -> None:
    customers = total_customers(df)
    new_customers, returning_customers = repeat_customer(df) if customers else (0, 0)

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


def reset_filters() -> None:
    defaults = {
        "product_filter": [],
        "country_filter": "All",
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

    if "product_filter" not in st.session_state:
        st.session_state.product_filter = []
    else:
        st.session_state.product_filter = [
            product for product in st.session_state.product_filter if product in products
        ]

    if st.session_state.get("country_filter") not in countries:
        st.session_state.country_filter = "All"

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

uploaded_file = st.file_uploader("Upload CSV file", type=["csv"])

if uploaded_file is not None:
    uploaded_df = pd.read_csv(uploaded_file, encoding="utf-8", low_memory=False)
    missing_columns = validate_columns(uploaded_df)
    if missing_columns:
        st.error(
            "Uploaded CSV is missing required columns: "
            + ", ".join(missing_columns)
        )
        st.stop()
    df = clean_data(uploaded_df)
    st.caption(f"Using uploaded file: {uploaded_file.name}")
else:
    df = load_default_data()
    st.caption("Using default file: data/cleaned_data.csv")

original_df = df.copy()

if df.empty:
    st.error("No usable rows found. Please upload a CSV with valid date values.")
    st.stop()

day_min = int(df["date"].dt.day.min())
day_max = int(df["date"].dt.day.max())
month_min = int(df["date"].dt.month.min())
month_max = int(df["date"].dt.month.max())
year_min = int(df["date"].dt.year.min())
year_max = int(df["date"].dt.year.max())
countries = ["All"] + sorted(df["Country"].dropna().unique().tolist())
products = sorted(df["Description"].dropna().unique().tolist())

sync_filter_state()

st.button("Remove Filters", on_click=reset_filters)

product_col, country_col, day_col, month_col, year_col = st.columns(5)
filters = []

with product_col:
    selected_products = st.multiselect(
        "Product",
        products,
        key="product_filter",
    )
    if selected_products:
        filters.append({"type": "product", "data": selected_products})

with country_col:
    country = st.selectbox("Country", countries, key="country_filter")
    if country != "All":
        filters.append({"type": "country", "data": [country]})

with day_col:
    filters.append(date_filter_control("Day", "day", day_min, day_max))
with month_col:
    filters.append(date_filter_control("Month", "month", month_min, month_max))
with year_col:
    filters.append(date_filter_control("Year", "year", year_min, year_max))

filtered_df = apply_filters(df.copy(), filters) if filters else df.copy()

with st.expander("Current filter JSON"):
    st.json(filters)

st.subheader("KPIs")
render_kpis(build_kpis(filtered_df, original_df))

st.subheader("Views")
if filtered_df.empty:
    st.warning("No records match the selected filters.")
else:
    chart_tab, data_tab = st.tabs(["Charts", "Filtered Data"])

    with chart_tab:
        trend_part = st.radio(
            "Trend level",
            ["year", "month", "day"],
            horizontal=True,
        )

        first_row_left, first_row_right = st.columns(2)
        with first_row_left:
            render_date_trend(filtered_df, trend_part)
        with first_row_right:
            render_product_bar(filtered_df, "top")

        second_row_left, second_row_right = st.columns(2)
        with second_row_left:
            render_product_bar(filtered_df, "bottom")
        with second_row_right:
            render_customer_mix(filtered_df)

    with data_tab:
        st.dataframe(filtered_df, use_container_width=True, hide_index=True)
