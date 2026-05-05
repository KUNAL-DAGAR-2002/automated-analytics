import pandas as pd


def add_total_price(df):
    df['total_price'] = df['Quantity'] * df['Price']
    return df


