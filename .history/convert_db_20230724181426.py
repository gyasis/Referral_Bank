import pandas as pd
import sqlite3

def df_to_sqlite(df, table_name, db_path):
    # Step 1: Create a connection to SQLite database
    conn = sqlite3.connect(db_path)
    
    # Step 2: Generate the CREATE TABLE SQL statement dynamically
    create_table_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ("
    for col, dtype in df.dtypes.items():
        if "int" in str(dtype):
            sql_type = "INTEGER"
        elif "float" in str(dtype):
            sql_type = "REAL"
        else:
            sql_type = "TEXT"
        create_table_sql += f"{col} {sql_type}, "
    create_table_sql = create_table_sql.rstrip(", ") + ")"
    
    # Step 3: Create the table
    with conn:
        cursor = conn.cursor()
        cursor.execute(create_table_sql)
        
    # Step 4: Insert data from the DataFrame into the SQLite table
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    conn.close()

# Example usage:
df = pd.read_csv('data/referrals.csv')
df_to_sqlite(df, 'referrals', 'data/referrals.db')
