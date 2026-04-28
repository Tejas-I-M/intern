from statsmodels.tsa.arima.model import ARIMA

def prepare_timeseries(df,metric):
    ts = df.resample("M", on="date")[metric].sum()
    return ts

def forecast_metric(df,metric, steps=3):
    ts = prepare_timeseries(df, metric)

    model = ARIMA(ts, order=(1,1,1))
    model_fit = model.fit()

    forecast = model_fit.forecast(steps=steps)

    return forecast.tolist()