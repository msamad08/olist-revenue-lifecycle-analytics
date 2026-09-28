.PHONY: all setup data load dbt analysis export clean

all: load dbt analysis export

setup:
	pip install -r requirements.txt

data:
	bash scripts/download_data.sh

load:
	python scripts/load_raw.py

dbt:
	cd dbt && dbt build --profiles-dir .

analysis:
	cd src && python forecast.py && python funnel.py && python retention.py && python data_quality_report.py

export:
	cd src && python export_powerbi.py

clean:
	rm -rf data/warehouse.duckdb data/exports dbt/target dbt/logs
