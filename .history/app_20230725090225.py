# %%
from flask import Flask, jsonify, render_template, request, jsonify
from fuzzywuzzy import fuzz
from filelock import FileLock
import pandas as pd
import numpy as np
import sqlite3
from inspect import currentframe
import sys

# %%

app = Flask(__name__)


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
    print(df.head())
    return df





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




if __name__ == '__main__':
    app.run(debug=True,port=5005)

# %%
