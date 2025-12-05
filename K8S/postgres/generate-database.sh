#!/usr/bin/env bash
set -euo pipefail

#######################################
# Connection settings (override via env)
#######################################
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-nwuJmAngGPxEKEWmRsbS}"  # override in env for safety
export PGPASSWORD

#######################################
# Workload settings (override via env)
#######################################
NUM_DBS="${NUM_DBS:-14000}"       # how many databases to create
DB_PREFIX="${DB_PREFIX:-testdb_}" # db names like testdb_1, testdb_2, ...
ROWS_PER_DB="${ROWS_PER_DB:-10}"  # how many rows to insert per DB

echo "Connecting to Postgres at ${PGHOST}:${PGPORT} as ${PGUSER}"
echo "Will create ${NUM_DBS} databases with prefix '${DB_PREFIX}'"
echo "Each DB will get ${ROWS_PER_DB} rows in test_table"
echo

for i in $(seq 2895 "${NUM_DBS}"); do
  db_name="${DB_PREFIX}${i}"

  echo "[$i/${NUM_DBS}] Creating database ${db_name}..."
  # Connect to the 'postgres' database to create new DBs
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres \
    -v ON_ERROR_STOP=1 \
    -c "CREATE DATABASE \"${db_name}\";"

  echo "[$i/${NUM_DBS}] Creating table and inserting data in ${db_name}..."

  # Now connect to the new DB and create table + insert mock data
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${db_name}" \
    -v ON_ERROR_STOP=1 <<SQL
CREATE TABLE IF NOT EXISTS test_table (
    id SERIAL PRIMARY KEY,
    payload TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

INSERT INTO test_table (payload)
SELECT 'mock row ' || g
FROM generate_series(1, ${ROWS_PER_DB}) AS g;
SQL

done

echo "Done. Created ${NUM_DBS} databases with test_table + mock data."

