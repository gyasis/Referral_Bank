import sqlite3

DB_PATH = "../data/referrals.db"

def list_usernames():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Select distinct usernames from the comments table
    cur.execute("""
        SELECT DISTINCT username
        FROM comments
    """)

    usernames = [row[0] for row in cur.fetchall()]

    conn.close()

    return usernames

def delete_comments(username):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Delete rows with the selected username
    cur.execute("""
        DELETE FROM comments
        WHERE username = ?
    """, (username,))

    conn.commit()
    conn.close()

def main():
    usernames = list_usernames()

    # Prompt for a username to delete comments from
    username = input("Enter the username to delete comments from: ")

    # Check if the username is valid
    if username not in usernames:
        print("Invalid username")
        return

    # Confirm the deletion
    confirm = input(f"Are you sure you want to delete all comments from {username}? (y/n): ")

    if confirm.lower() == "y":
        delete_comments(username)
        print(f"All comments from {username} have been deleted.")
    else:
        print("Deletion canceled.")

if __name__ == "__main__":
    main()
