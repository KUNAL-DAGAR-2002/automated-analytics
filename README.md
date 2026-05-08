#### Live Demo Link
https://kunal-dagar-2002-automated-analytics-app-eb1bmg.streamlit.app/

# Automated Analytics Dashboard

A Streamlit dashboard for quickly analyzing retail/customer transaction data from CSV files. The app supports built-in CSV files from the `data/` folder as well as user-uploaded CSV files, then lets the user map their dataset columns to the app's expected schema.

## Features

- Select a CSV file from the sidebar.
- Upload a custom CSV file.
- Map uploaded/custom column names to fixed dashboard columns.
- Mark missing columns as `Column not available in dataset`.
- Automatically hide filters and views when their required columns are not available.
- Filter data by product, country, age, gender, day, month, and year.
- View KPI cards in rows of five.
- Analyze charts, metric-wise revenue contribution, average order value, and filtered data.
- Dynamically set the CLV period year from the app.

## How To Run

Install dependencies:

```powershell
pip install -r requirements.txt
```

Start the Streamlit app:

```powershell
streamlit run app.py
```

Open the local URL shown by Streamlit, usually:

```text
http://localhost:8501
```

## Data Sources

The app has a sidebar called **Data Source**.

You can either:

- Choose one of the CSV files already present in the `data/` folder.
- Select `Upload CSV` and upload your own file.

Uploaded files are not permanently stored by the app. They are only used during the current Streamlit session.

## Column Mapping

After selecting or uploading a CSV, the app shows a **Column Mapping** section.

The dashboard works with these fixed internal columns:

- `Invoice`
- `StockCode`
- `Description`
- `Quantity`
- `Price`
- `Country`
- `cust_id`
- `date`
- `Age`
- `Gender`

If your CSV has different column names, map them using the dropdowns. For example:

- `Transaction ID` -> `Invoice`
- `Customer ID` -> `cust_id`
- `Product Category` -> `Description`
- `Price per Unit` -> `Price`

If a column is not available in the dataset, select:

```text
Column not available in dataset
```

Then click **Apply Mapping**. The mapping locks and collapses to save space. Use **Edit Mapping** if you need to change it.

## Conditional Filters And Views

The app only shows filters and views for columns that are available.

Examples:

- If `Country` is not mapped, the country filter is hidden.
- If `Age` is not mapped, the age filter and age group metric option are hidden.
- If `Gender` is not mapped, the gender filter and gender metric option are hidden.
- If `date` is not mapped, day/month/year filters and date trend charts are hidden.
- If `Description` is not mapped, product filters and product charts are hidden.

## Filters

Available filters depend on the mapped columns:

- Product multi-select
- Country dropdown
- Age range slider
- Gender multi-select
- Day filter with `between`, `more`, `less`, `equal`
- Month filter with `between`, `more`, `less`, `equal`
- Year filter with `between`, `more`, `less`, `equal`

The app builds filter JSON internally and applies it through the existing scalable filter logic.

Example:

```python
[
    {"type": "country", "data": ["Germany"]},
    {"type": "age", "data": [25, 40]},
    {"type": "year", "data": [2010], "token": "equal"}
]
```

Use **Remove Filters** to reset all filters.

## KPIs

The app shows KPI cards, five per row:

- Total Revenue
- Total Orders
- Average Order Value
- Units Sold
- Refund Rate
- Customers
- New Customers
- Returning Customers
- Purchase Frequency
- Customer Lifetime Value

For **Customer Lifetime Value**, use the **CLV Period Year** input to set the period passed into the CLV calculation.

## Views

### Charts

The Charts tab shows up to four charts in a two-by-two layout:

- Revenue trend by year, month, or day
- Top products by revenue
- Bottom products by revenue
- Customer mix pie chart

Month trend values are displayed as month names such as `Jan`, `Feb`, and `Mar`.

### Metric Wise

The Metric Wise tab lets you choose the breakdown metric from available mapped columns:

- Age Group
- Gender
- Product
- Country

It shows two charts in the same row:

- Revenue Contribution
- Average Order Value

Each chart has its respective table below it. Revenue contribution values in the table include a `%` sign.

### Filtered Data

The Filtered Data tab shows the final dataframe after mappings, cleaning, and filters are applied.

## Project Structure

```text
Excel Project/
  app.py
  requirements.txt
  data/
  plots/
  scripts/
    data_cleaning/
    filter/
    kpi/
    views/
```

Important files:

- `app.py`: Main Streamlit dashboard.
- `scripts/filter/apply_filter.py`: Applies filter JSON to the dataframe.
- `scripts/filter/date_filter.py`: Handles day/month/year filter logic.
- `scripts/kpi/kpi.py`: KPI calculations.
- `scripts/views/views.py`: Product and date chart helper logic.
- `scripts/views/age_wise.py`: Metric-wise revenue contribution and average order value logic.
- `scripts/data_cleaning/calculated_columns.py`: Adds calculated fields like `total_price` and `age_group`.

## Performance Notes

The app includes caching and session-state optimization:

- CSV reads are cached.
- Uploaded CSV parsing is cached.
- Mapped and cleaned data is cached after mapping is locked.
- Data is reprocessed only when the selected file or locked mapping changes.

This keeps filter changes and view switches faster.

## Troubleshooting

If the app looks stuck after changing files, refresh the Streamlit page.

If a view is missing, check whether the required column was mapped or marked as unavailable.

If uploaded data does not load correctly, confirm that important numeric/date columns are mapped properly:

- `Quantity`
- `Price`
- `date`
- `Invoice`
- `cust_id`

If Streamlit says the port is already in use, run it on another port:

```powershell
streamlit run app.py --server.port 8502
```
