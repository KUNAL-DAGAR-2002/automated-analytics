import pandas as pd
from scripts.filter.date_filter import DateFilter

def total_revenue(df):
    return df['total_price'].sum()

def total_orders(df):
    return df['Invoice'].nunique()

def average_order_value(df, total_revenue, total_orders):
    return (total_revenue / total_orders)

def total_units_sold(df):
    return df[df['Quantity']>0]['Quantity'].sum()

def refund_rate(df):
    total_orders= df['Invoice'].nunique()
    refunded_orders = df[df['Quantity']<0]['Invoice'].nunique()
    return (refunded_orders/total_orders)

def total_customers(df):
    return df['cust_id'].nunique()

def repeat_customer(df):
    cust_seg = df.groupby('cust_id').agg({
    "date":"nunique"
    }).reset_index().sort_values("date", ascending=False)


    cust_seg['segment'] = cust_seg['date'].apply(lambda x: 'New' if x == 1 else 'Returning')

    new_cust = ((cust_seg[cust_seg['segment'] == 'New'].shape[0] / cust_seg.shape[0]) * 100)
    returning_cust = ((cust_seg[cust_seg['segment'] == 'Returning'].shape[0] / cust_seg.shape[0]) * 100)

    return new_cust, returning_cust


def purachese_frequency(df):
    return float(df.groupby('cust_id')['Invoice'].nunique().mean())

def customer_lifetime_value(df, period = None, average_order_value = None, purchase_frequency = None):
    filters = [
    {"type": "year", "data": [period], "token": "less"}
    ]

    for i in filters:
        type =i['type']
        data = i['data']
        token = i['token']

        date_filter = DateFilter(df, filter_type=type, filter_data=data, token=token)
        req_cust = date_filter.apply()

    customer_after_period = df[df['date'].dt.year > period]

    cust_before = set(req_cust['cust_id'].unique())
    cust_after = set(customer_after_period['cust_id'].unique())


    customer_lost = len(cust_before - cust_after)
    churn_rate = (customer_lost / len(cust_before))
    average_lifespan = 1/(churn_rate)


    return float(average_order_value) * float(purchase_frequency) * float(average_lifespan)



    