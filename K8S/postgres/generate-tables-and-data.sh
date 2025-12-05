#!/bin/bash

# Set environment variables
PG_USER="postgres"            # The superuser or role to connect with PostgreSQL
PG_DB="postgres"         # The database name to use
PG_HOST="localhost"           # PostgreSQL server host
PG_PORT="5432"                # PostgreSQL server port
PG_PASSWORD="FdwbffDS82zbsq6qymPS"   # Password for the user (ensure it's securely handled, e.g., .pgpass)
SCHEMA_COUNT=14000            # Number of schemas to use
TABLE_NAME="mock_data"        # Table name to be created in each schema

# Function to execute SQL commands
exec_sql() {
    PGPASSWORD=$PG_PASSWORD psql -U $PG_USER -h $PG_HOST -p $PG_PORT -d $PG_DB -c "$1"
}

# Function to create table in a schema
create_table_in_schema() {
    local schema=$1
    echo "Creating table in schema $schema..."
    exec_sql "
        CREATE TABLE IF NOT EXISTS $schema.$TABLE_NAME (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    "
}

# Function to insert mock data into the table
insert_mock_data_into_table() {
    local schema=$1
    echo "Inserting mock data into $schema.$TABLE_NAME..."
    exec_sql "
        INSERT INTO $schema.$TABLE_NAME (name)
        VALUES
        ('Mock Name 1'),
        ('Mock Name 2'),
        ('Mock Name 3'),
        ('Mock Name 4'),
        ('Mock Name 5');
    "
}

# Step 1: Create tables and insert data into each schema
echo "Creating tables and inserting data into $SCHEMA_COUNT schemas..."

for i in $(seq 1 $SCHEMA_COUNT); do
    schema_name="schema_$i"
    
    # Create table in each schema
    create_table_in_schema $schema_name
    
    # Insert mock data into the table
    insert_mock_data_into_table $schema_name

    # Print progress
    if ((i % 100 == 0)); then
        echo "Processed $i schemas..."
    fi
done

echo "Finished creating tables and inserting mock data into $SCHEMA_COUNT schemas."

