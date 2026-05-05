import pandas as pd


def handle_null_values(df):
    #drop null values in column cust_id, invoice
    df = df.dropna(subset=["cust_id", "Invoice"])


    #handling null values for country
    df["Country"] = df["Country"].fillna(df['Country'].mode()[0])


    #handling null values for description, stock code
    df["Description"] = df["Description"].fillna("Unknown")
    df["StockCode"] = df["StockCode"].fillna("Unknown")


    #handling nulls in quantity and price
    df["Quantity"] = df["Quantity"].fillna(1)
    df["Price"] = df["Price"].fillna(df["Price"].median())

    return df


def handle_duplicates(df):
    #drop duplicates
    df = df.drop_duplicates()

    return df



