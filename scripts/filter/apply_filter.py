from scripts.filter.country_and_product_filter import (
    age_filter,
    country_filter,
    gender_filter,
    product_filter,
)
from scripts.filter.date_filter import DateFilter 
import pandas as pd

filter_map = {
    "product" : product_filter,
    "country" : country_filter,
    "age": age_filter,
    "gender": gender_filter,
}

def apply_filters(df, filters):
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df = df.copy(deep=False)
        df['date'] = pd.to_datetime(df['date'])  # ensure date is datetime
    for i in filters:
        type =i['type']
        data = i['data']

        if type in filter_map:
            filter_func = filter_map[type]
            df = filter_func(df, data)
            
        elif type in ["year", "month", "day"]:
            token = i['token']
            date_filter = DateFilter(df, filter_type=type, filter_data=data, token=token)
            df = date_filter.apply()

    return df
