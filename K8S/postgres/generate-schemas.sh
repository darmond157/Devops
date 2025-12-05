#!/bin/bash

PG_USER="postgres"            # The superuser or role to connect with PostgreSQL
PG_DB="postgres"              # The database name to use
PG_HOST="localhost"           # PostgreSQL server host
PG_PORT="5432"                # PostgreSQL server port
PG_PASSWORD="FdwbffDS82zbsq6qymPS"   # Password for the user (ensure it's securely handled, e.g., .pgpass)
SCHEMA_COUNT=14000            # Number of schemas to create

# Function to execute SQL commands
exec_sql() {
    PGPASSWORD=$PG_PASSWORD psql -U $PG_USER -h $PG_HOST -p $PG_PORT -d $PG_DB -c "$1"
}

# Step 1: Create 14,000 schemas
echo "Creating $SCHEMA_COUNT schemas..."
for i in $(seq 8438 $SCHEMA_COUNT); do
    echo "$i"
    schema_name="schema_$i"
    exec_sql "CREATE SCHEMA $schema_name;"
    if ((i % 100 == 0)); then
        echo "Created $i schemas..."
    fi
done
echo "Finished creating $SCHEMA_COUNT schemas."
