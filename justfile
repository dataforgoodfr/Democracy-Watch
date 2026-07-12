# List all just recipes
recipes:
  just --list

# Download all data from Tricoteuse: modify APIS in ./etl/download.py to add endpoints
download:
  uv run etl/download.py

# Drop all tables and recreate the database
db-rebuild:
  uv run main.py -r

# Run the ETL: extract data from files in ./data and load them in Postgres
etl:
  uv run main.py -e

# Drop all tables, recreate db and run etl
all:
  uv run main.py -a

# Run psql to explore the database
psql:
  psql -h localhost -U postgres -d ipolitics

# Detect external-collaboration mentions on a sample of amendments (v1, no pre-filter)
detect-mentions limit="50":
  uv run python -m analysis.detect_mentions --limit {{limit}}
