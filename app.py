# %%
from flask import Flask, jsonify, render_template, request, jsonify
from fuzzywuzzy import fuzz
from filelock import FileLock
import pandas as pd
import numpy as np
import sqlite3
from inspect import currentframe
import sys
import os
import time
import re
import sqlite3
from prettytable import PrettyTable
from langchain.chains.question_answering import load_qa_chain
from langchain.chat_models import ChatOpenAI
from langchain.utilities import GoogleSerperAPIWrapper
from langchain.llms.openai import OpenAI
from langchain.agents import initialize_agent, Tool
from langchain.agents import AgentType
from langchain import OpenAI, LLMChain, PromptTemplate
from langchain.memory import ConversationBufferWindowMemory
from datetime import datetime
# %%

app = Flask(__name__)
os.environ["SERPER_API_KEY"] = "f1d76cfda54d3b248d9bd7d931d794f4af123eb8"
os.environ["OPENAI_API_KEY"] = "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"


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
            cur.execute("ALTER TABLE comments ADD COLUMN username TEXT")
            print("Username column added to existing Comments table.")
        else:
            print("Comments table already has a username column.")
    
    conn.close()


create_comments_table()


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
    referral_id = request.args.get('recordId')  # Using 'recordId' from frontend to match with 'referral_id' in backend
    
    if not referral_id:
        return jsonify({"error": "recordId parameter is required"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM comments WHERE referral_id=?", (referral_id,))
    comments = [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]
    print(f"Returned comments: {comments}")
    conn.close()
    return jsonify(comments)



@app.route('/add_comment', methods=['POST'])
def add_comment():
    referral_id = request.form.get('recordId')
    comment_text = request.form.get('text')
    
    print(f"Referral_id: {referral_id} \ncomment_text: {comment_text}")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Insert the comment into the database
    # Insert the comment into the database
    cur.execute("INSERT INTO comments (referral_id, comment, username) VALUES (?, ?, ?)", (referral_id, comment_text, "johndoe"))

    
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




@app.route('/search_and_parse', methods=['POST'])
def search_and_parse_route():
    record_id = request.form.get('record_id')  # Assuming you're sending the record ID from the frontend
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM referrals WHERE id=?", (record_id,))
    record = cur.fetchone()
    conn.close()
    if not record:
        return jsonify({"status": "error", "message": "Record not found!"})
    
    parsed_details = search_and_parse(record)
    accepted_details = user_choice(parsed_details, record["SPECIALTY"])
    
    return jsonify(accepted_details)



if __name__ == '__main__':
    app.run(debug=True,port=5005)


