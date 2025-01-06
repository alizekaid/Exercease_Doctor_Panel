import bcrypt
from flask import Flask, render_template, request, redirect, url_for, flash, session
from firebase_admin import credentials, firestore, initialize_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask app and Firebase
app = Flask(__name__)
app.secret_key = "ExercEaseMobileApplicationDevelopment"  # You can change this to a more secure key

# Initialize Firestore
cred = credentials.Certificate("exercease-d82ad-firebase-adminsdk-2e77p-ba3b9e9f3a.json")
initialize_app(cred)
db = firestore.client()

today_date = datetime.now().strftime("%B %d, %Y") 

@app.route("/", methods=["GET", "POST"])
def index():
    # Render the index page
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        useremail = request.form["useremail"]
        userpassword = request.form["userpassword"]

        # Retrieve the user document from Firestore
        user_ref = db.collection("Doctors").document(useremail)
        user = user_ref.get()

        # Check if the user is a doctor
        if user.exists:
            user_data = user.to_dict()
            stored_password = user_data["password"]
            stored_role = user_data["role"]

            # Use bcrypt to check if the entered password matches the stored bcrypt hash
            if stored_role == "doctor" and check_password_hash(stored_password, userpassword):
                session["user_email"] = useremail
                session["role"] = stored_role
                return redirect(url_for("doctor_dashboard"))  # Redirect to the doctor dashboard

        # Check if the user is an admin
        admin_ref = db.collection("Admin").document("Admin_Info")
        admin = admin_ref.get()

        if admin.exists:
            admin_data = admin.to_dict()
            stored_password = admin_data["password"]
            stored_role = admin_data["role"]

            # Use bcrypt to check if the entered password matches the stored bcrypt hash
            if stored_role == "admin" and bcrypt.checkpw(userpassword.encode('utf-8'), stored_password.encode('utf-8')):
                session["admin_email"] = useremail
                session["role"] = stored_role
                return redirect(url_for("admin_index"))  # Redirect to the admin index page
            else:
                flash("Invalid password or role for admin", "danger")
        else:
            flash("Admin account does not exist", "danger")

        flash("Invalid login credentials", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    # Clear all session data
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("index"))  # Redirect to the login page

@app.route("/admin/index")
def admin_index():
    # This will render the admin index page located in the "admin" folder
    if session.get("role") != "admin":
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))
    admin_email = session.get("admin_email", "Unknown Email")
    today_date = datetime.now().strftime("%B %d, %Y")
    return render_template("admin/index.html", admin_email=admin_email, today_date=today_date)

@app.route("/admin/doctors", methods=["GET"])
def doctors():
    # Only allow admin to view this page
    if session.get("role") != "admin":
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))

    # Retrieve the list of doctors
    doctors_ref = db.collection("Doctors")
    docs = doctors_ref.stream()
    doctors_list = [{"email": doc.id} for doc in docs]

    return render_template("admin/doctors.html", doctors=doctors_list)

@app.route("/admin/patients", methods=["GET"])
def all_patients():
    # Only allow admin to view this page
    if session.get("role") != "admin":
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))

    patients_list = []

    # Retrieve all users (patients)
    users_ref = db.collection("Users")
    all_users = users_ref.stream()

    for user in all_users:
        user_data = user.to_dict()
        injuries_ref = users_ref.document(user.id).collection("Injuries")
        injuries = injuries_ref.stream()

        # Check if the user has injuries
        patient_injuries = []
        for injury in injuries:
            injury_data = injury.to_dict()
            patient_injuries.append({
                "body_part": injury.id,
                "muscle_name": injury_data.get("muscleName", "Unknown"),
                "pain_level": injury_data.get("painLevel", "Unknown"),
                "progress": injury_data.get("progress", "Unknown"),
            })

        if patient_injuries:
            patients_list.append({
                "name_surname": user_data.get("name_surname", "Unknown"),
                "age": user_data.get("age", "Unknown"),
                "email": user_data.get("email", "Unknown"),
                "uid": user_data.get("uid", "Unknown"),
                "injuries": patient_injuries
            })

    return render_template("admin/patient.html", patients=patients_list, today_date=today_date)


@app.route("/admin/dashboard")
def admin_dashboard():
    # Only allow admin to view this page
    if session.get("role") != "admin":
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))

    admin_email = session.get("admin_email", "Unknown Email")
    today_date = datetime.now().strftime("%B %d, %Y")

    # Retrieve the total number of doctors and users
    doctors_ref = db.collection("Doctors")
    total_doctors = len([doc.id for doc in doctors_ref.stream()])

    users_ref = db.collection("Users")
    total_users = len([user.id for user in users_ref.stream()])

    # Retrieve patient data (limit to first 3 patients with injuries)
    patients_list = []
    all_users = users_ref.stream()

    for user in all_users:
        user_data = user.to_dict()
        injuries_ref = users_ref.document(user.id).collection("Injuries")
        injuries = injuries_ref.stream()

        patient_injuries = []
        for injury in injuries:
            injury_data = injury.to_dict()
            patient_injuries.append({
                "body_part": injury.id,
                "muscle_name": injury_data.get("muscleName", "Unknown"),
                "pain_level": injury_data.get("painLevel", "Unknown"),
                "progress": injury_data.get("progress", "Unknown"),
            })

        if patient_injuries:
            patients_list.append({
                "name_surname": user_data.get("name_surname", "Unknown"),
                "age": user_data.get("age", "Unknown"),
                "email": user_data.get("email", "Unknown"),
                "uid": user_data.get("uid", "Unknown"),
                "injuries": patient_injuries
            })

    # Limit the displayed patients to the first 3
    limited_patients = patients_list[:3]

    return render_template(
        "admin/index.html",
        admin_email=admin_email,
        today_date=today_date,
        total_doctors=total_doctors,
        total_users=total_users,
        patients=limited_patients,
    )


@app.route("/add_doctor", methods=["GET", "POST"])
def add_doctor():
    # Only allow admin to add a doctor
    if session.get("role") != "admin":
        flash("You are not authorized to add doctors", "danger")
        return redirect(url_for("login"))

    if request.method == "POST":
        doctor_name = request.form["doctor_name"]
        email = request.form["email"]
        password = request.form["password"]
        field = request.form["field"]
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        try:
            # Add doctor to Firestore
            db.collection("Doctors").document(email).set({
                "doctor_name": doctor_name,
                "email": email,
                "password": hashed_password,
                "role": "doctor",  # Set the role of the new doctor
                "field": field
            })
            flash("Doctor added successfully", "success")
        except Exception as e:
            flash(f"Error adding doctor: {e}", "danger")

        return redirect(url_for("doctors"))
    
    return render_template("admin/add_doctor.html")

@app.route("/doctor/dashboard")
def doctor_dashboard():
    # Render the doctor dashboard page
    if session.get("role") != "doctor":
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))
    
    doctor_email = session.get("user_email", "Unknown Email")
    today_date = datetime.now().strftime("%B %d, %Y")

    doctor_ref = db.collection("Doctors").document(doctor_email)
    doctor = doctor_ref.get()

    if doctor.exists:
        doctor_data = doctor.to_dict()
        doctor_field = doctor_data.get("field", "No field assigned")
        doctor_name = doctor_data.get("doctor_name", "Doctor")
    else:
        doctor_field = "No field assigned"


    # Count the number of patients for this doctor's field
    users_ref = db.collection("Users")
    all_users = users_ref.stream()
    patient_count = 0

    for user in all_users:
        injuries_ref = users_ref.document(user.id).collection("Injuries")
        injuries = injuries_ref.stream()

        for injury in injuries:
            if injury.id.lower() == doctor_field:
                patient_count += 1
                break  # Stop checking injuries for this user once a match is found

    return render_template(
        "doctor/index.html",
        doctor_email=doctor_email,
        today_date=today_date,
        doctor_field=doctor_field,
        doctor_name=doctor_name,
        patient_count=patient_count,  # Pass the patient count to the template
    )

@app.route("/doctor/patients", methods=["GET", "POST"])
def doctor_patients():
    if session.get("role") != "doctor":
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))

    doctor_email = session["user_email"]
    doctor_ref = db.collection("Doctors").document(doctor_email)
    doctor = doctor_ref.get()

    if doctor.exists:
        doctor_data = doctor.to_dict()
        doctor_field = doctor_data.get("field", "No field assigned").lower()
    else:
        flash("Doctor's information not found", "danger")
        return redirect(url_for("login"))

    patients_list = []

    # Retrieve patients with relevant injuries
    users_ref = db.collection("Users")
    all_users = users_ref.stream()

    for user in all_users:
        user_data = user.to_dict()
        injuries_ref = users_ref.document(user.id).collection("Injuries")
        injuries = injuries_ref.stream()

        # Check if the user has relevant injuries
        for injury in injuries:
            if injury.id.lower() == doctor_field:
                patients_list.append({
                    "name_surname": user_data.get("name_surname", "Unknown"),
                    "age": user_data.get("age", "Unknown"),
                    "email": user_data.get("email", "Unknown"),
                    "uid": user_data.get("uid", "Unknown"),
                })
                break  # Stop checking injuries for this user once a match is found

    return render_template(
        "doctor/patient.html", 
        patients=patients_list, 
        doctor_field=doctor_field, 
        today_date=today_date,
        doctor_email=doctor_email
    )

@app.route("/doctor/patient/<uid>/exercises", methods=["GET"])
def see_exercises(uid):
    if session.get("role") not in ["doctor", "admin"]:
        flash("You are not authorized to view this page", "danger")
        return redirect(url_for("login"))
    
    # Retrieve injuries for the specific patient
    patient_injuries_ref = db.collection("Users").document(uid).collection("Injuries")
    injuries = patient_injuries_ref.stream()

    exercises = []
    for injury in injuries:
        injury_data = injury.to_dict()
        exercises.append({
            "body_part": injury.id,
            "gif_urls": injury_data.get("gifUrls", []),
            "muscle_name": injury_data.get("muscleName", "Unknown"),
            "pain_level": injury_data.get("painLevel", "Unknown"),
            "timestamp": injury_data.get("timestamp", "Unknown"),
            "progress": injury_data.get("progress", "Unknown"),
        })
    
    return render_template(
        "doctor/exercises.html",
        exercises=exercises,
        uid=uid
    )

@app.route("/send_notification", methods=["POST"])
def send_notification():
    if session.get("role") not in ["doctor", "admin"]:
        return {"error": "Unauthorized"}, 403  # Only doctors can send notifications

    data = request.json
    uid = data.get("uid")
    title = data.get("title", "").strip()
    message = data.get("message", "").strip()

    if not uid:
        return {"error": "User UID is required"}, 400
    if not title:
        return {"error": "Title is required"}, 400
    if not message:
        return {"error": "Message is required"}, 400


    try:
        # Add notification to the user's "notifications" collection
        notification_ref = db.collection("Users").document(uid).collection("notifications")
        print(uid)
        notification_ref.add({
            "title": title,
            "message": message,
            "timestamp": datetime.now()
        })
        return {"success": True, "message": "Notification sent successfully"}
    except Exception as e:
        return {"error": str(e)}, 500


if __name__ == "__main__":
    app.run(debug=True)
