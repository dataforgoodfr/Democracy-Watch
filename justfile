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

# Detect external-collaboration mentions in amendments with regexes
# Extra flags pass through, e.g.: just detect-mentions-regex --persist --limit 100
detect-mentions-regex *ARGS:
  uv run python -m analysis.detect_mentions_regex {{ARGS}}

# Nommer les entités des mentions par NER zéro-shot local (GLiNER)
# Extra flags pass through, e.g.: just extract-entities-gliner --dossier DLR5L17N53187 --persist
extract-entities-gliner *ARGS:
  uv run python -m analysis.extract_entities_gliner {{ARGS}}

# Drop the DuckDB vector tables
vector-db-rebuild:
  uv run main.py --rebuild-vector-database

# Embed the amendments into the vector database
# Extra flags pass through, e.g.: just embed --backend foo --model bar
# Restrict to a single dossier: just embed --dossier DLR5L16N47129
embed *ARGS:
  uv run main.py --embed {{ARGS}}

# Serve the whole app: HTML pages on / and the read API on /api (docs on /docs)
# Extra flags pass through, e.g.: just serve --port 8001
serve *ARGS:
  uv run uvicorn api.main:app --reload --host 127.0.0.1 --port 8000 {{ARGS}}
