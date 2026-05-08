import pandas as pd 


def metric_wise_average_order_value(df,metric):
    if metric not in df.columns:
        return df
    
    metric_aov = df.groupby(metric).agg(
      total_revenue = ('total_price', 'sum'),
      total_orders = ('Invoice', 'nunique')
   ).reset_index()
    
    metric_aov['average_order_value'] = metric_aov['total_revenue'] / metric_aov['total_orders']
    return metric_aov[[metric, 'average_order_value']].head(10)


def revenue_contib_by_metric(df, metric):
    if metric not in df.columns:
        return df
    
    contribution = df.groupby(metric).agg(
        total_revenue = ('total_price', 'sum')
    ).reset_index()

    total_revenue = contribution['total_revenue'].sum()
    contribution['revenue_contribution'] = (contribution['total_revenue'] / total_revenue) * 100

    return contribution[[metric, 'revenue_contribution']].head(10)
