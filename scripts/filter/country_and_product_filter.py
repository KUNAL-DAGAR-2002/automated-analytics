import pandas as pd



def country_filter(df, country):
    if not country:
        return df
    return df[df['Country'].isin(country)]


def product_filter(df, product):
    if not product:
        return df
    return df[df['Description'].isin(product)]