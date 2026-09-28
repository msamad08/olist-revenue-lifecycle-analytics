"""Load raw Olist CSVs into a local DuckDB warehouse (schema: raw).

DuckDB is used as a local stand-in for Snowflake so the whole project runs
on a laptop. The dbt models use ANSI SQL and can be pointed at Snowflake by
switching the dbt profile (see dbt/profiles.yml).
"""
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "warehouse.duckdb"

TABLES = {
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "products": "olist_products_dataset.csv",
    "category_translation": "product_category_name_translation.csv",
    "marketing_qualified_leads": "olist_marketing_qualified_leads_dataset.csv",
    "closed_deals": "olist_closed_deals_dataset.csv",
}


def main() -> None:
    missing = [f for f in TABLES.values() if not (RAW / f).exists()]
    if missing:
        raise SystemExit(f"Missing files in data/raw: {missing}. Run scripts/download_data.sh")
    con = duckdb.connect(str(DB))
    con.execute("create schema if not exists raw")
    for table, fname in TABLES.items():
        # all_varchar keeps raw data untouched; typing happens in dbt staging models
        con.execute(
            f"create or replace table raw.{table} as "
            f"select * from read_csv('{RAW / fname}', header=true, all_varchar=true)"
        )
        n = con.execute(f"select count(*) from raw.{table}").fetchone()[0]
        print(f"raw.{table:<28} {n:>8,} rows")
    con.close()


if __name__ == "__main__":
    main()
