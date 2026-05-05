import pandas as pd

class DateFilter:
    def __init__(self, df, filter_type=None, filter_data=None, token=None):
        self.df = df
        self.filter_type = filter_type
        self.filter_data = filter_data
        self.token = token

    def apply(self):
        
        if not self.filter_type or not self.filter_data or not self.token:
            return self.df  # nothing to apply

        token = "equal" if self.token == "equl" else self.token

        # map filter type → pandas datetime accessor
        attr_map = {
            "year": "year",
            "month": "month",
            "day": "day"
        }

        attr = attr_map.get(self.filter_type)

        if not attr:
            return self.df

        series = getattr(self.df['date'].dt, attr)

        if token == "between":
            start, end = self.filter_data
            return self.df[(series >= start) & (series <= end)]

        elif token == "more":
            return self.df[series >= self.filter_data[0]]

        elif token == "less":
            return self.df[series <= self.filter_data[0]]
        
        elif token == "equal":
            return self.df[series == self.filter_data[0]]

        return self.df
