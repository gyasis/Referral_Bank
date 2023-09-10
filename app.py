# %%
from flask import Flask, jsonify, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from fuzzywuzzy import fuzz
from filelock import FileLock
import pandas as pd
import numpy as np
from inspect import currentframe
import sys
import os
import time
import re
import sqlite3
from prettytable import PrettyTable
# from langchain.chains.question_answering import load_qa_chain
# from langchain.chat_models import ChatOpenAI
# from langchain.utilities import GoogleSerperAPIWrapper
# from langchain.llms.openai import OpenAI
# from langchain.agents import initialize_agent, Tool
# from langchain.agents import AgentType
# from langchain import OpenAI, LLMChain, PromptTemplate
# from langchain.memory import ConversationBufferWindowMemory
from datetime import datetime

import secrets

app = Flask(__name__)
os.environ["SERPER_API_KEY"] = "f1d76cfda54d3b248d9bd7d931d794f4af123e35756"
os.environ["OPENAI_API_KEY"] = "sk-KcsvnmTqOD0LnJTovqUwT3BlbkFJeN7Ux0M22244"

app.secret_key = secrets.token_hex(16)
# Database setup
DB_PATH = "data/referrals.db"
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()
# Assuming the table has already been created and structured correctly


def mod_df(df): 
    # Sort the DataFrame by 'SPECIALTY' but keep the original index values
    df = df.sort_values(by='SPECIALTY').reset_index(drop=True)

    print(len(df))
    # Fill NaN values in NAME_OF_ORGANIZATION with 'Unknown Organization'
    df['NAME_OF_ORGANIZATION'].fillna('Unknown Organization', inplace=True)

    df['NAME'].fillna('', inplace=True)
    print(f"modified df: {df.head()}")
    return df


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM referrals", conn)
    conn.close()
  
    return df

def create_comments_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if the comments table exists
    cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='comments' ''')
    
    if cur.fetchone()[0] == 0:
        cur.execute('''
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY,
                referral_id INTEGER,
                comment TEXT,
                username TEXT,  
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(referral_id) REFERENCES referrals(id)
            )
        ''')
        print("Comments table created successfully.")
    else:
        # If the table already exists, check if the username column exists
        cur.execute("PRAGMA table_info(comments)")
        columns = [column[1] for column in cur.fetchall()]
        if "username" not in columns:
            cur.execute("ALTER TABLE comments ADD COLUMN user_id integer")
            print("user_id column added to existing Comments table.")
        else:
            print("Comments table already has a username column.")
    
    conn.close()


# Creating the users table
def create_users_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Check if the users table exists
    cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='users' ''')
    
    if cur.fetchone()[0] == 0:
        cur.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL
            )
        ''')
        print("Users table created successfully.")
    else:
        print("Users table already exists.")
    
    conn.commit()
    conn.close()
    
def create_comment_emojis_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check if the comment_emojis table exists
    cur.execute(''' SELECT count(name) FROM sqlite_master WHERE type='table' AND name='comment_emojis' ''')
    
    if cur.fetchone()[0] == 0:
        cur.execute('''
            CREATE TABLE comment_emojis (
                id INTEGER PRIMARY KEY,
                username TEXT,
                comment_id INTEGER,
                emoji_type TEXT,
                FOREIGN KEY(comment_id) REFERENCES comments(id)
            )
        ''')
        print("Comment Emojis table created successfully.")
    else:
        print("Comment Emojis table already exists.")
    
    conn.commit()
    conn.close()
    

create_comments_table()
create_users_table()
create_comment_emojis_table()


def get_username(user_id):
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("SELECT username FROM users WHERE id=?", (user_id,))
        user = cur.fetchone()
        return user[0] if user else None

#Login and Registration sections

def register_user(email, password, username):
    hashed_password = generate_password_hash(password, method='sha256')
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, password, username) VALUES (?, ?, ?)", (email, hashed_password, username))
        conn.commit()
        conn.close()
        return True
    except:
        return False
    
    
def login_user(email, password):
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()
            cur.execute("SELECT id, username, password FROM users WHERE email=?", (email,))
            user = cur.fetchone()
            
            if not user:
                print("No user with email:", email)
                return None
            
            user_id, username, hashed_password_from_db = user
            
            is_password_correct = check_password_hash(hashed_password_from_db, password)
            print("Is password correct?", is_password_correct)
            
            if is_password_correct:
                return user_id, username, hashed_password_from_db # include the hashed_password in return
            else:
                print("Debug: Failed password check!")
                print(f"Debug: Hashed password from DB: {hashed_password_from_db}")
                
    except Exception as e:
        print("Error during login:", e)
    return None

#emoji code
def user_has_emoji(username, comment_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute('''
        SELECT emoji_type FROM comment_emojis WHERE username=? AND comment_id=?
    ''', (username, comment_id))
    
    result = cur.fetchone()
    conn.close()
    
    return result[0] if result else None


            

@app.route('/')
def home():
    df = load_data()
    df = mod_df(df)
    specialties = df['SPECIALTY'].unique().tolist()
    return render_template('dashboard.html', specialties=specialties)

@app.route('/search')
def search():
    df = load_data()
    df = mod_df(df)
    
    
    term = request.args.get('q', '')
    
    results = df[df.apply(lambda row: fuzz.token_set_ratio(row['NAME_OF_ORGANIZATION'], term) > 70 or
                                     fuzz.token_set_ratio(row['SPECIALTY'], term) > 70 or
                                     fuzz.token_set_ratio(row['NOTES'], term) > 70 or
                                     fuzz.token_set_ratio(row['NAME'], term) > 70 or
                                     fuzz.token_set_ratio(row['LOCATION'], term) > 70 or
                                     fuzz.token_set_ratio(row['PHONE_NUMBER'], term) > 70, axis=1)]
    
    print(f"Search term: {term}, results count: {len(results)}") 
    
    # Return the desired columns
    return results[['id','NAME_OF_ORGANIZATION', 'NAME', 'SPECIALTY']].to_html(index=True)




@app.route('/filter')
def filter_by_specialty():
    df = load_data()
    df = mod_df(df)
    specialty = request.args.get('q', '')
    results = df[df['SPECIALTY'] == specialty]
    print(f"Filter by specialty: {specialty}, results count: {len(results)}") 
    print(results)
    return results[['id','NAME_OF_ORGANIZATION','NAME', 'SPECIALTY']].to_html(index=True)


@app.route('/details')
def details():
    df = load_data()
    df = mod_df(df)
    row_id = int(request.args.get('index', -1))  # Get the id from the request
    print(f"Row ID: {row_id}")
    print(type(row_id))
    
    # Check if a valid id is provided
    if row_id != -1:
        try:
            # Use the 'id' column to retrieve the row
            result = df[df['id'] == row_id].iloc[0].to_dict()  
            print(result)

            # Convert NaN or NA values to an empty string
            for key in result.keys():
                if pd.isnull(result[key]):
                    result[key] = ''

            # Fetch comments for the referral
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT * FROM comments WHERE referral_id=?", (row_id,))
            comments = cur.fetchall()
            print(f"Comments from Details: {comments}")
            conn.close()

            # Add comments to the result
            result['comments'] = comments

        except Exception as e:
            print(f"Unexpected error occurred: {str(e)}")
            result = {}

        return jsonify({str(k): str(v) for k, v in result.items()})  # Converts all keys and values to string
    else:
        return jsonify({"error": "Invalid id provided."})

@app.route('/update', methods=['POST'])
def update():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # Extract index from POST request
        index = request.form.get('index')
        index = int(index) if index else -1

        
        # Debug Log
        print(f"Received Data for index {index}:")

        # Check if record exists
        cur.execute("SELECT * FROM referrals WHERE id=?", (index,))
        referral = cur.fetchone()

        if referral:
            # Update fields based on the form data, including empty fields
            update_values = [(key, request.form.get(key)) for key in request.form if key != "index"]
            for key, value in update_values:
                sql = f'UPDATE referrals SET "{key}"=? WHERE id=?'

                print(f"Executing SQL: {sql} with values: ({value}, {index})")
                cur.execute(sql, (value, index))
            message = "Record updated successfully!"
        else:
            # Exclude 'index' from columns and values since SQLite will auto-generate id
            columns = ', '.join([key for key in request.form if key != "index"])
            placeholders = ', '.join(['?'] * len(columns.split(', ')))
            values = tuple([request.form.get(key) for key in request.form if key != "index"])
            cur.execute(f"INSERT INTO referrals ({columns}) VALUES ({placeholders})", values)
            message = "Record added successfully!"


        # Commit changes to the database
        conn.commit()
        conn.close()

    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Unexpected error occurred at line {sys.exc_info()[-1].tb_lineno}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "success", "message": message})

@app.route('/delete', methods=['POST'])
def delete():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        # Extract index from POST request
        index = request.form.get('index')
        index = int(index) if index else -1

        # Check if record exists
        cur.execute("SELECT * FROM referrals WHERE id=?", (index,))
        referral = cur.fetchone()

        if referral:
            # Delete the record
            cur.execute("DELETE FROM referrals WHERE id=?", (index,))
            conn.commit()
            conn.close()
            return jsonify({"status": "success", "message": "Record deleted successfully!"})
        else:
            conn.close()
            return jsonify({"status": "error", "message": "Record not found!"})
    except Exception as e:
        conn.rollback()
        conn.close()
        print(f"Unexpected error occurred at line {sys.exc_info()[-1].tb_lineno}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})
     
@app.route('/comments')
def get_comments():
    try:
        current_user = session['user_id']
    except KeyError:
        current_user = None
    referral_id = request.args.get('recordId')
    
    if not referral_id:
        return jsonify({"error": "recordId parameter is required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Fetch comments and their respective emoji counts
    cur.execute("""
        SELECT c.*, 
               COALESCE(ce.emoji_count, 0) as emoji_count
        FROM comments c
        LEFT JOIN (
            SELECT comment_id, COUNT(emoji_type) as emoji_count
            FROM comment_emojis
            WHERE emoji_type = '❤️'
            GROUP BY comment_id
        ) ce ON c.id = ce.comment_id
        WHERE c.referral_id = ?
    """, (referral_id,))
    
    comments = [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]
    print(f"Returned comments: {comments}")
    conn.close()
    return jsonify(comments=comments, current_user=session.get('username'))


@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))


@app.route('/add_comment', methods=['POST'])
def add_comment():
    if 'user_id' not in session:
        return jsonify({"status": "error", "message": "Please login first!"})
    username = session['username']
    referral_id = request.form.get('recordId')
    comment_text = request.form.get('text')
    
    print(f"Referral_id: {referral_id} \ncomment_text: {comment_text}")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Insert the comment into the database
    # Insert the comment into the database
    cur.execute("INSERT INTO comments (referral_id, comment, username) VALUES (?, ?, ?)", (referral_id, comment_text, username))

    
    # Fetch the last inserted comment's details
    comment_id = cur.lastrowid  # Get the ID of the last inserted row
    cur.execute("SELECT * FROM comments WHERE id=?", (comment_id,))
    comment = cur.fetchone()

    # Populate the response data
    response_data = {
    "status": "success",
    "message": "Comment added successfully!",
    "commentId": comment[0],  # Assuming 'id' is the first column
    "commentText": comment[2],  # Assuming 'comment' is the third column
    "username": comment[4],    # Assuming 'username' is the fifth column after adding it
    "timestamp": comment[3]    # Assuming 'timestamp' is the fourth column
}

    print(f"Response data: {response_data}")
    conn.commit()
    conn.close()
    
    return jsonify(response_data)


@app.route('/edit_comment', methods=['POST'])
def edit_comment():
    comment_id = request.form.get('comment_id')
    updated_text = request.form.get('updated_text')
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        cur.execute("UPDATE comments SET comment = ? WHERE id = ?", (updated_text, comment_id))
        conn.commit()
        return jsonify({"status": "success", "message": "Comment updated successfully!"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})
    finally:
        conn.close()

    
@app.route('/delete_comment', methods=['POST'])
def delete_comment():
    comment_id = request.form.get('comment_id')
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # First, check if the comment exists
    cur.execute("SELECT * FROM comments WHERE id=?", (comment_id,))
    comment = cur.fetchone()

    if comment:
        # Delete the comment
        cur.execute("DELETE FROM comments WHERE id=?", (comment_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "success", "message": "Comment deleted successfully!"})
    else:
        conn.close()
        return jsonify({"status": "error", "message": "Comment not found!"})

import sqlite3
@app.route('/register', methods=['POST'])
def register():
    email = request.form['email']
    password = request.form['password']
    username = request.form['username']
    update_password_flag = request.form.get('updatePasswordFlag', 'false') == 'true'

    try:
        with sqlite3.connect(DB_PATH) as conn:
            cur = conn.cursor()

            if update_password_flag:
                # Update the password for the user with the given email
                new_hashed_password = generate_password_hash(password)
                cur.execute("UPDATE users SET password=? WHERE email=?", (new_hashed_password, email))
                conn.commit()

                if cur.rowcount == 0:  # No rows updated, possibly invalid email
                    return jsonify(status="error", message="Failed to update password."), 400

                # Optionally: Log the user in after updating the password
                cur.execute("SELECT id FROM users WHERE email=?", (email,))
                user_id = cur.fetchone()[0]
                session['user_id'] = user_id
                return jsonify(status="success", message="Password updated successfully")

            else:
                # Standard registration logic
                hashed_password = generate_password_hash(password)
                cur.execute("INSERT INTO users (email, password, username) VALUES (?, ?, ?)", (email, hashed_password, username))
                conn.commit()
                return jsonify(status="success", message="Registration successful")

    except sqlite3.IntegrityError:
        # This error occurs if the email or username is not unique
        return jsonify(status="error", message="Registration failed, email or username might be taken."), 400

    except Exception as e:
        print(f"Error during registration/update: {e}")
        return jsonify(status="error", message="An unexpected error occurred."), 500


@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']
    
    user = login_user(email, password)
    if user:
        user_id, username, stored_hashed_password = user  # Unpacking the three values

        # Check if the user's hashed password matches the hash of the generic password
        is_generic_password = check_password_hash(stored_hashed_password, 'h3r$3lf')
        
        session['user_id'] = user_id
        session['username'] = username

        response_data = {
            "status": "success",
            "message": "Logged in successfully",
            "username": username,
            "email": email,
            "generic_password_used": is_generic_password
        }
        
        return jsonify(response_data)
    else:
        return jsonify(status="error", message="Login failed, check your credentials."), 400



# @app.route('/search_and_parse', methods=['POST'])
# def search_and_parse_route():
#     record_id = request.form.get('record_id')  # Assuming you're sending the record ID from the frontend
#     conn = sqlite3.connect(DB_PATH)
#     cur = conn.cursor()
#     cur.execute("SELECT * FROM referrals WHERE id=?", (record_id,))
#     record = cur.fetchone()
#     conn.close()
#     if not record:
#         return jsonify({"status": "error", "message": "Record not found!"})
    
#     parsed_details = search_and_parse(record)
#     accepted_details = user_choice(parsed_details, record["SPECIALTY"])
    
#     return jsonify(accepted_details)



@app.route('/is_logged_in', methods=['GET'])
def check_login_status():
    if 'user_id' in session:
        user_id = session['user_id']
        username = get_username(user_id)
        # Fetch the username using the user_id from your database
        # Let's say you fetch it and the username is 'JohnDoe'
        return jsonify(logged_in=True, username=username)
    return jsonify(logged_in=False)



    
@app.route('/add_emoji', methods=['POST'])
def add_emoji():
    # Get data from request
    username = session["username"]
    data = request.get_json()
    comment_id = data['comment_id']
    emoji_type = data['emoji_type']
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    existing_emoji = user_has_emoji(username, comment_id)
    
    if existing_emoji:
        if emoji_type == "none":  # Handle the removal of a like
            # Delete the entry
            cur.execute('''
                DELETE FROM comment_emojis WHERE username=? AND comment_id=?
            ''', (username, comment_id))
        else:
            # Update the entry
            cur.execute('''
                UPDATE comment_emojis SET emoji_type=? WHERE username=? AND comment_id=?
            ''', (emoji_type, username, comment_id))
    else:
        # Insert the new emoji
        cur.execute('''
            INSERT INTO comment_emojis (username, comment_id, emoji_type) VALUES (?, ?, ?)
        ''', (username, comment_id, emoji_type))
    
    conn.commit()
    conn.close()

    return jsonify(status="success")

@app.route('/get_emoji_counts')
def get_emoji_counts():
    comment_id = request.args.get('comment_id')
    
    if not comment_id:
        return jsonify({"error": "comment_id parameter is required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT comment_id, COUNT(emoji_type) as emoji_count FROM comment_emojis WHERE comment_id=? GROUP BY comment_id", (comment_id,))
    counts = cur.fetchone()
    conn.close()

    if counts:
        return jsonify(comment_id=counts[0], emoji_count=counts[1])
    else:
        return jsonify(comment_id=comment_id, emoji_count=0)



if __name__ == '__main__':
    app.run(host='0.0.0.0',debug=True,port=5005)


