import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "../data/referrals.db"

def insert_or_update_single_user(email, full_name, hashed_password):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Extract first name and last name
    first_name, last_name = full_name.split(' ', 1)
    username = first_name + last_name[0]
    
    # Insert or Replace user
    cur.execute("""
        INSERT OR REPLACE INTO users (email, password, username) 
        VALUES (?, ?, ?)
    """, (email, hashed_password, username))
    
    conn.commit()
    conn.close()

def main():
    # Prompt user for input
    email = input("Please enter the email: ")
    full_name = input("Please enter the full name (First Last): ")
    
    # Generate the hash once
    hashed_password = generate_password_hash('h3r$3lf', method='sha256')
    
    insert_or_update_single_user(email, full_name, hashed_password)

if __name__ == "__main__":
    main()
