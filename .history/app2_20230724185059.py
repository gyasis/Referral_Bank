@app.route('/update', methods=['POST'])
def update():
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
