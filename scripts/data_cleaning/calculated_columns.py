import pandas as pd


def add_total_price(df):
    df['total_price'] = df['Quantity'] * df['Price']
    return df



def add_age_groups(df):
    if 'Age' not in df.columns:
        return df

    df['Age'] = pd.to_numeric(df['Age'], errors='coerce')
    
    df['age_group'] = [
        "early earners" if age >=18 and age <=24 
        else "Young professionals" if age >=25 and age <=34 
        else "Stable income" if age >=35 and age <= 44 
        else "Senior citizens" if pd.notna(age)
        else "Unknown"
        for age in df['Age']
    ]


    return df

