#!/bin/bash

PGUSER="postgres"
PGDB="postgres"
PGHOST="localhost"
PG_PASSWORD="FdwbffDS82zbsq6qymPS"

for i in $(seq 1 14000); do
    schema="schema_${i}"

    sql="INSERT INTO ${schema}.mock_data (name)
         SELECT 'mock-' || gs FROM generate_series(6, 2000) AS gs;"

    echo "Inserting 2000 rows into $schema..."
    PGPASSWORD=$PG_PASSWORD psql -U $PGUSER -h $PGHOST -d $PGDB -c "$sql"

    if (( i % 100 == 0 )); then
        echo "Completed $i schemas"
    fi
done

