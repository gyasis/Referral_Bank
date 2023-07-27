from flask import Flask, jsonify, render_template, request
from fuzzywuzzy import fuzz
import sqlite3

app = Flask(__name__)
DATABASE = 'data/referrals.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY,
                NAME_OF_ORGANIZATION TEXT DEFAULT 'Unknown Organization',
                NAME TEXT DEFAULT '',
                SPECIALTY TEXT,
                NOTES TEXT,
                LOCATION TEXT,
                PHONE_NUMBER TEXT
            )
        """)
        conn.commit()

def query_db(query, args=(), one=False):
    with get_db() as conn:
        cur = conn.execute(query, args)
        rv = cur.fetchall()
        conn.commit()
        return (rv[0] if rv else None) if one else rv

@app.route('/')
def home():
    data = load_data()
    specialties = list(set([item['SPECIALTY'] for item in data]))
    return render_template('dashboard.html', specialties=specialties)

@app.route('/search')
def search():
    term = request.args.get('q', '')
    results = search_data(term)
    # Convert rows to dicts for jsonify compatibility
    results = [dict(row) for row in results]
    return jsonify(results)

@app.route('/filter')
def filter_by_specialty():
    specialty = request.args.get('q', '')
    results = filter_specialty(specialty)
    # Convert rows to dicts for jsonify compatibility
    results = [dict(row) for row in results]
    return jsonify(results)

@app.route('/details')
def details():
    index = int(request.args.get('index', -1))
    result = get_detail(index)
    if result:
        return jsonify(dict(result))
    else:
        return jsonify({"error": "Invalid index provided."})

@app.route('/update', methods=['POST'])
def update():
    try:
        index = int(request.form.get('index', -1))
        
        with get_db() as conn:
            cursor = conn.cursor()

            referral = cursor.execute("SELECT * FROM referrals WHERE id = ?", (index,)).fetchone()
            
            if referral:
                # Update existing record
                for key in request.form:
                    if key != "index":
                        cursor.execute(f"UPDATE referrals SET {key} = ? WHERE id = ?", (request.form.get(key), index))

                message = "Record updated successfully!"
            
            else:
                # Add new record
                columns = ', '.join(request.form.keys())
                placeholders = ', '.join('?' for _ in request.form)
                values = tuple(request.form.values())

                cursor.execute(f"INSERT INTO referrals ({columns}) VALUES ({placeholders})", values)

                message = "Record added successfully!"
            conn.commit()

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "success", "message": message})

def load_data():
    return query_db("SELECT * FROM referrals")

def search_data(term):
    return query_db("""
        SELECT * FROM referrals 
        WHERE NAME_OF_ORGANIZATION LIKE ? OR SPECIALTY LIKE ? OR NOTES LIKE ? OR NAME LIKE ? OR LOCATION LIKE ? OR PHONE_NUMBER LIKE ?
    """, (f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%", f"%{term}%"))

def filter_specialty(specialty):
    return query_db("SELECT * FROM referrals WHERE SPECIALTY = ?", (specialty,))

def get_detail(index):
    return query_db("SELECT * FROM referrals WHERE id = ?", (index,), one=True)

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5005)
