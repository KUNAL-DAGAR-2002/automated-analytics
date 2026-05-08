import pandas as pd
import matplotlib.pyplot as plt

def date_wise_trends(df, date_part, on=None, metric=None):
    attr_map = {
        "year": "year",
        "month": "month",
        "day": "day"
    }

    month_name = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
        5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
        9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }

    attr = attr_map.get(date_part)
    if not attr:
        return

    # extract date part
    df[date_part] = getattr(df['date'].dt, attr)

    year_group = (
        df.groupby(date_part)
        .agg({on: metric})
        .reset_index()
        .sort_values(date_part, ascending=True)
    )

    # ✅ Fix only for month
    if date_part == "month":
        year_group[date_part] = year_group[date_part].map(month_name)

    plt.plot(year_group[date_part], year_group[on], marker="o")
    plt.savefig("./plots/date_wise_trends.png", dpi=300, bbox_inches='tight')
    plt.close()




def top_bottom(df, top_or_bottom = None, n = None, on = None, metric = None):
    if not top_or_bottom or not n or not on or not metric:
        return df
    
    cust_revenue = df.groupby(on).agg({
        metric : "sum"
    }).sort_values(metric, ascending = False)

    if top_or_bottom == "top":
        return cust_revenue.head(n)
    
    elif top_or_bottom == "bottom":
        return cust_revenue.tail(n)
    

def pie_char(new_customers, returning_customers):
    lables = ["New Customers", "Returning Customers"]
    sizes = [new_customers, returning_customers]
    plt.figure(figsize=(6,6))
    plt.pie(sizes, labels=lables, autopct='%1.1f%%', startangle=140)
    plt.plot()
    plt.savefig("./plots/customer_pie_chart.png", dpi=300, bbox_inches='tight')
