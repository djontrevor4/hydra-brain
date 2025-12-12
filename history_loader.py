import requests
import sqlite3
import time
from datetime import datetime, timedelta

from config import TICKERS
DB = "history.db"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS prices (ticker TEXT, date TEXT, close REAL, volume INTEGER, PRIMARY KEY(ticker, date))")
    conn.commit()
    conn.close()

def fetch_prices(ticker, year):
    url = "https://iss.moex.com/iss/history/engines/stock/markets/shares/boards/TQBR/securities/" + ticker + ".json"
    start = str(year) + "-01-01"
    end = str(year) + "-12-31"
    all_data = []
    cursor = 0
    while True:
        params = {"from": start, "till": end, "start": cursor, "limit": 100}
        r = requests.get(url, params=params, timeout=15)
        if r.status_code != 200:
            break
        data = r.json()
        rows = data.get("history", {}).get("data", [])
        if not rows:
            break
        for row in rows:
            if row[11]:
                all_data.append((ticker, row[1], row[11], row[12] or 0))
        cursor += 100
        if len(rows) < 100:
            break
    return all_data

def save_prices(data):
    conn = sqlite3.connect(DB)
    conn.executemany("INSERT OR REPLACE INTO prices VALUES (?,?,?,?)", data)
    conn.commit()
    conn.close()

def main():
    init_db()
    years = [2020, 2021, 2022, 2023, 2024, 2025]
    for ticker in TICKERS:
        print(ticker, "...", end=" ")
        total = 0
        for year in years:
            data = fetch_prices(ticker, year)
            save_prices(data)
            total += len(data)
            time.sleep(0.3)
        print(total, "days")
    conn = sqlite3.connect(DB)
    cnt = conn.execute("SELECT COUNT(*) FROM prices").fetchone()[0]
    conn.close()
    print("Total:", cnt, "records in history.db")

if __name__ == "__main__":
    main()
