import sqlite3

DB_PATH = "../data/referrals.db"

def drop_comments_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Drop the comments table if it exists
    cur.execute("""
        DROP TABLE IF EXISTS comments
    """)
    
    conn.commit()
    conn.close()

def main():
    drop_comments_table()

if __name__ == "__main__":
    main()
