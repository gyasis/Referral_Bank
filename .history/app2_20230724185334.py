@app.route('/update', methods=['POST'])
def update():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    try:
        # Extract index from POST request
        index = int(request.form.get('index', -1))
        
        # Debug Log
        print(f"Received Data for index {index}:")

        # Check if record exists
        cur.execute("SELECT * FROM referrals WHERE id=?", (index,))
        referral = cur.fetchone()

        if referral:
            # Update existing record
            update_values = [(request.form.get(key), key, index) for key in request.form if key != "index"]
            for value, key, idx in update_values:
                cur.execute(f"UPDATE referrals SET {key}=? WHERE id=?", (value, idx))
            message = "Record updated successfully!"
        else:
            # Add new record
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
        print(f"Unexpected error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

    return jsonify({"status": "success", "message": message})
