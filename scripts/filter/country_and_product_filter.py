import pandas as pd



def country_filter(df, country):
    if not country:
        return df
    return df[df['Country'].isin(country)]


def product_filter(df, product):
    if not product:
        return df
    return df[df['Description'].isin(product)]


def gender_filter(df, gender):
    if not gender:
        return df
    return df[df['Gender'].isin(gender)]


def age_filter(df, age_range):
    if not age_range:
        return df
    start, end = age_range
    return df[(df['Age'] >= start) & (df['Age'] <= end)]
