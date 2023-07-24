from flask import Flask, jsonify, render_template, request, jsonify
from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np

app = Flask(__name__)

df = pd.read_csv('data/referrals.csv')

# Sort the DataFrame by 'SPECIALTY' but keep the original index values
df = df.sort_values(by='SPECIALTY').reset_index(drop=True)

print(len(df))
# Fill NaN values in NAME_OF_ORGANIZATION with 'Unknown Organization'
df['NAME_OF_ORGANIZATION'].fillna('Unknown Organization', inplace=True)

df['NAME'].fillna('', inplace=True)
# %%
df2 = pd.read_csv('../ec_score_file.csv')
# %%

# Assuming df and df2 are your dataframes loaded earlier in the code
# df is the one from the Excel and df2 is the one with provider details

@app.route('/')
def home():
    specialties = df['SPECIALTY'].unique().tolist()
    return render_template('dashboard.html', specialties=specialties)

@app.route('/search')
def search():
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
    specialty = request.args.get('q', '')
    results = df[df['SPECIALTY'] == specialty]
    print(f"Filter by specialty: {specialty}, results count: {len(results)}") 
    print(results)
    return results[['NAME_OF_ORGANIZATION','NAME', 'SPECIALTY']].to_html(index=True)


@app.route('/details')
def details():
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
    try:
        # Extract index from POST request
        index = int(request.form.get('index', -1))

        # Debug Log
        print(f"Received Data for index {index}:")

        # Check if a valid index is provided
        if index != -1:
            # Update all fields in the DataFrame based on the keys in the request.form
            for key in request.form:
                # Skip the index key as it's just for locating the record
                if key != "index":
                    df.loc[index, key] = request.form.get(key)
                    print(f"{key}={request.form.get(key)}")

            # Debug Log
            print(f"Updated DataFrame: \n{df}")
            
            #save dataframe to CSV
            df.to_csv('referrals.csv', index=False) 

            return jsonify({"status": "success", "message": "Record updated successfully in memory!"})
        else:
            return jsonify({"status": "error", "message": "Invalid index provided."})

    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})





if __name__ == '__main__':
    app.run(debug=True,port=5001)

# %%
