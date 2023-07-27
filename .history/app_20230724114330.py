from flask import Flask, jsonify, render_template, request, jsonify
from fuzzywuzzy import fuzz
from filelock import FileLock
import pandas as pd
import numpy as np

app = Flask(__name__)
lock = FileLock("data/referrals.csv.lock")

def mod_df(df): 
    # Sort the DataFrame by 'SPECIALTY' but keep the original index values
    df = df.sort_values(by='SPECIALTY').reset_index(drop=True)

    print(len(df))
    # Fill NaN values in NAME_OF_ORGANIZATION with 'Unknown Organization'
    df['NAME_OF_ORGANIZATION'].fillna('Unknown Organization', inplace=True)

    df['NAME'].fillna('', inplace=True)
    return df


def load_data():
    return pd.read_csv('data/referrals.csv')





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
        with lock:
            # Extract index from POST request
            index = int(request.form.get('index', -1))

            # Debug Log
            print(f"Received Data for index {index}:")

            if index != -1 and index in df.index:
                # Update existing record
                for key in request.form:
                    if key != "index":
                        df.loc[index, key] = request.form.get(key)
                        print(f"{key}={request.form.get(key)}")

                print(f"Updated DataFrame: \n{df}")
                
                message = "Record updated successfully in memory!"

            else:
                # Add new record
                new_record = {}
                for key in request.form:
                    if key != "index":
                        new_record[key] = request.form.get(key)
                df = df.append(new_record, ignore_index=True)
                print(f"Added new record. DataFrame: \n{df}")

                message = "Record added successfully in memory!"

            # Save the dataframe to CSV
            df.to_csv('data/referrals.csv', index=False)

        

    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})
    return jsonify({"status": "success", "message": message})





if __name__ == '__main__':
    app.run(debug=True,port=5005)

# %%
