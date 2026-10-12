from flask import Flask, render_template, request, jsonify
import os

app = Flask(__name__)

# Demo data lets the website run before Oracle is configured.
demo_mode = True

inventory = {
    "A+": 10, "A-": 5, "B+": 8, "B-": 4,
    "AB+": 3, "AB-": 2, "O+": 12, "O-": 4
}

donors = [
    {"id": 1, "name": "Demo Donor 1", "age": 21,
     "blood_group": "A+", "phone": "9000000001", "city": "Tirupati"},
    {"id": 2, "name": "Demo Donor 2", "age": 22,
     "blood_group": "B+", "phone": "9000000002", "city": "Tirupati"},
    {"id": 3, "name": "Demo Donor 3", "age": 20,
     "blood_group": "O+", "phone": "9000000003", "city": "Tirupati"}
]

requests_list = []

def get_connection():
    import oracledb
    return oracledb.connect(
        user=os.environ["ORACLE_USER"],
        password=os.environ["ORACLE_PASSWORD"],
        dsn=os.environ["ORACLE_DSN"]
    )


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/dashboard")
def dashboard():
    if demo_mode:
        return jsonify({
            "donor_count": len(donors),
            "units": sum(inventory.values()),
            "request_count": len(requests_list),
            "inventory": [
                {"blood_group": k, "units": v}
                for k, v in inventory.items()
            ],
            "donors": donors
        })

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM DONORS")
            donor_count = cur.fetchone()[0]
            cur.execute("SELECT NVL(SUM(UNITS_AVAILABLE),0) FROM INVENTORY")
            units = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM BLOOD_REQUESTS")
            request_count = cur.fetchone()[0]
            cur.execute("SELECT BLOOD_GROUP, UNITS_AVAILABLE FROM INVENTORY")
            stock = [{"blood_group": r[0], "units": r[1]}
                     for r in cur.fetchall()]
            cur.execute("""SELECT DONOR_ID, DONOR_NAME, AGE,
                BLOOD_GROUP, PHONE, CITY FROM DONORS ORDER BY DONOR_ID""")
            people = [{"id": r[0], "name": r[1], "age": r[2],
                       "blood_group": r[3], "phone": r[4], "city": r[5]}
                      for r in cur.fetchall()]
        return jsonify({
            "donor_count": donor_count, "units": units,
            "request_count": request_count,
            "inventory": stock, "donors": people
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/donors", methods=["POST"])
def add_donor():
    data = request.get_json(silent=True) or {}
    try:
        name = data.get("name", "").strip()
        age = int(data.get("age", 0))
        bg = data.get("blood_group", "")
        if not name or age < 18 or bg not in inventory:
            return jsonify({"error": "Enter a name, valid age (18+), and blood group."}), 400

        if demo_mode:
            donors.append({
                "id": len(donors) + 1, "name": name, "age": age,
                "blood_group": bg, "phone": data.get("phone", ""),
                "city": data.get("city", "Tirupati")
            })
        else:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute("""INSERT INTO DONORS
                    (DONOR_NAME, AGE, BLOOD_GROUP, PHONE, CITY)
                    VALUES (:1, :2, :3, :4, :5)""",
                    [name, age, bg, data.get("phone", ""),
                     data.get("city", "Tirupati")])
                conn.commit()

        return jsonify({"message": "Donor registered successfully."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/requests", methods=["POST"])
def add_request():
    data = request.get_json(silent=True) or {}
    try:
        patient = data.get("patient_name", "").strip()
        bg = data.get("blood_group", "")
        units = int(data.get("units", 0))
        if not patient or bg not in inventory or units < 1:
            return jsonify({"error": "Enter valid request details."}), 400

        if demo_mode:
            status = "Pending"
            if inventory[bg] >= units:
                inventory[bg] -= units
                status = "Fulfilled"
            requests_list.append({
                "patient": patient, "blood_group": bg,
                "units": units, "status": status
            })
        else:
            with get_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT UNITS_AVAILABLE FROM INVENTORY "
                    "WHERE BLOOD_GROUP=:1 FOR UPDATE", [bg])
                row = cur.fetchone()
                if row is None:
                    return jsonify({"error": "Blood group not found."}), 400
                status = "Pending"
                if row[0] >= units:
                    cur.execute(
                        "UPDATE INVENTORY SET UNITS_AVAILABLE="
                        "UNITS_AVAILABLE-:1 WHERE BLOOD_GROUP=:2",
                        [units, bg])
                    status = "Fulfilled"
                cur.execute("""INSERT INTO BLOOD_REQUESTS
                    (PATIENT_NAME, BLOOD_GROUP, UNITS_REQUIRED,
                     HOSPITAL_NAME, REQUEST_STATUS)
                    VALUES (:1, :2, :3, :4, :5)""",
                    [patient, bg, units,
                     data.get("hospital_name", ""), status])
                conn.commit()

        return jsonify({"message": "Request recorded: " + status})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)