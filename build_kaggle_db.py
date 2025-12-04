"""
Скрипт для подготовки SQLite-базы из CSV датасета Kaggle.

Шаги использования:
1) Скачай CSV с Kaggle (IMDb Top 1000) и положи в data/imdb_top_1000.csv
2) Запусти этот скрипт:
   python build_kaggle_db.py
3) В результате появится файл data/imdb_top_1000.db с таблицей 'movies'.
"""

import os
import sqlite3

import pandas as pd

DATA_DIR = "data"
CSV_PATH = os.path.join(DATA_DIR, "imdb_top_1000.csv")
DB_PATH = os.path.join(DATA_DIR, "imdb_top_1000.db")
TABLE_NAME = "movies"


def main():
    if not os.path.exists(CSV_PATH):
        print(f"❌ CSV файл не найден: {CSV_PATH}")
        print("Скачай датасет с Kaggle и положи его по этому пути.")
        return

    os.makedirs(DATA_DIR, exist_ok=True)

    print(f"📥 Читаю CSV: {CSV_PATH}")
    df = pd.read_csv(CSV_PATH)

    print(f"🗄 Создаю SQLite базу: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)

    try:
        df.to_sql(TABLE_NAME, conn, if_exists="replace", index=False)
        print(f"✅ Таблица '{TABLE_NAME}' успешно создана в {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
