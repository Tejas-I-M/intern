import pandas as pd

def standardize_columns(df):
    df.columns = df.columns.str.lower().str.strip().str.replace(" ", "_")
    return df

def clean_sales(path):
    df = pd.read_csv(path, encoding='latin1')
    df = standardize_columns(df)

    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    df = df.drop_duplicates()
    df = df.fillna(0)

    return df


def clean_hr(path):
    df = pd.read_csv(path, encoding='latin1')
    df = standardize_columns(df)

    df = df.drop_duplicates()
    df = df.fillna("Unknown")

    return df


def clean_finance(path):
    df = pd.read_csv(path, encoding='latin1')
    df = standardize_columns(df)

    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')

    df = df.drop_duplicates()
    df = df.fillna(0)

    return df