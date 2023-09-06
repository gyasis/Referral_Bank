import pandas as pd
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "../data/referrals.db"

def process_data(hashed_password):
    df = pd.read_csv('/home/gyasis/Documents/code/Herself/dump/user.csv')
    
    # Filter rows based on the email address pattern
    filtered_df = df[df['EMAIL'].str.endswith('@herself-health.com')].copy()  # Create a copy to avoid SettingWithCopyWarning
    
    # Create a new column "username" with the desired format
    filtered_df['username'] = filtered_df['FIRST_NAME'] + filtered_df['LAST_NAME'].str[0]
    
    # Extract and rename the columns, then set the hashed password
    final_df = filtered_df[['username', 'EMAIL']].rename(columns={'EMAIL': 'email'})
    final_df['password'] = hashed_password
    
    return final_df

def insert_or_update_users(df, hashed_password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Insert or Replace users
    for _, row in df.iterrows():
        cur.execute("""
            INSERT OR REPLACE INTO users (email, password, username) 
            VALUES (?, ?, ?)
        """, (row['email'], row['password'], row['username']))
    
    # Update all passwords
    cur.execute("UPDATE users SET password = ?", (hashed_password,))
    
    conn.commit()
    conn.close()

# Generate the hash once
hashed_password = generate_password_hash('h3r$3lf', method='sha256')

df = process_data(hashed_password)
insert_or_update_users(df, hashed_password)
