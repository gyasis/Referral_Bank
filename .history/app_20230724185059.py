from flask import Flask, jsonify, render_template, request, jsonify
from fuzzywuzzy import fuzz
from filelock import FileLock
import pandas as pd
import numpy as np
import sqlite3

app = Flask(__name__)


# Database setup
DB_PATH = "data/referrals.sqlite"
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
    return df


def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM referrals", conn)
    conn.close()
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
    return results[['NAME_OF_ORGANIZATION', 'NAME', 'SPECIALTY']].to_html(index=True)




@app.route('/filter')
def filter_by_specialty():
    df = load_data()
    df = mod_df(df)
    specialty = request.args.get('q', '')
    results = df[df['SPECIALTY'] == specialty]
    print(f"Filter by specialty: {specialty}, results count: {len(results)}") 
    print(results)
    return results[['NAME_OF_ORGANIZATION','NAME', 'SPECIALTY']].to_html(index=True)


@app.route('/details')
def details():
    df = load_data()
    df = mod_df(df)
    index = int(request.args.get('index', -1))  # Get the index from the request
    print(f"Index: {index}")
    print(type(index))
    # Check if a valid index is provided
    if index != -1:
        try:
            result = df.loc[index].to_dict()  # Use the index to retrieve the row
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
        return jsonify({"error": "Invalid index provided."})

@app.route('/update', methods=['POST'])
def update():
    df = load_data()
    df = mod_df(df)
    try:
        # Extract index from POST request
        index = int(request.form.get('index', -1))

        # Debug Log
        print(f"Received Data for index {index}:")

        # Check if record exists
        referral = Referral.query.get(index)
        if referral:
            # Update existing record
            for key in request.form:
                if key != "index" and hasattr(referral, key):  # Ensure the attribute exists in the model
                    setattr(referral, key, request.form.get(key))
                    print(f"{key}={request.form.get(key)}")
            message = "Record updated successfully!"

        else:
            # Add new record
            new_record = {key: value for key, value in request.form.items() if key != "index"}
            new_referral = Referral(**new_record)
            db.session.add(new_referral)
            message = "Record added successfully!"

        # Commit changes to the database
        db.session.commit()

    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "success", "message": message})





if __name__ == '__main__':
    app.run(debug=True,port=5005)

# %%
