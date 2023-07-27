from flask import Flask, jsonify, render_template, request, jsonify
from fuzzywuzzy import fuzz
from filelock import FileLock
import pandas as pd
import numpy as np

app = Flask(__name__)
lock = FileLock("data/referrals.csv.lock")

def load_data():
    return pd.read_csv('data/referrals.csv')

@app.route('/')
def home():
    df = load_data()
    
    specialties = df['SPECIALTY'].unique().tolist()
    return render_template('dashboard.html', specialties=specialties)

@app.route('/search')
def search():
    df = load_data()
    term = request.args.get('q', '')
    # ... rest of the logic ...

@app.route('/filter')
def filter_by_specialty():
    df = load_data()
    specialty = request.args.get('q', '')
    # ... rest of the logic ...

@app.route('/details')
def details():
    df = load_data()
    index = int(request.args.get('index', -1))
    # ... rest of the logic ...

@app.route('/update', methods=['POST'])
def update():
    df = load_data()

    try:
        with lock:  # Acquiring lock before any write operation
            # ... your logic ...
            df.to_csv('data/referrals.csv', index=False)
    except Exception as e:
        print(f"Unexpected error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "success", "message": message})

if __name__ == '__main__':
    app.run(debug=True, port=5005)
