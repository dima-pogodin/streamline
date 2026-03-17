import pandas as pd

URL = "https://datahub.io/core/commodity-prices/_r/-/data/commodity-prices_v2.csv"

def load_commodity_data():
    """
    Загружает исторические данные по commodity из DataHub.io
    """
    df = pd.read_csv(URL, parse_dates=["Date"])
    df.rename(columns={"Date": "date"}, inplace=True)
    return df

if __name__ == "__main__":
    df = load_commodity_data()
    print(df.head())