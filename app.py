from flask import Flask, flash, redirect, render_template, request, session
from extension import db
from models import *
from datetime import date, datetime, time, timedelta

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hospital_management_data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SECRET_KEY"] = "22f2001271"

db.init_app(app)

with app.app_context():
    db.create_all()
    create_default_admin()
    create_default_departments()

# ============================= (INDEX / LOGIN / REGISTER / LOGOUT) =============================


@app.route("/")
def index():
    return redirect("/login")


# -----------------------------------------REGISTRATION FOR PATIENT-----------------------------------------


@app.route("/register_patient", methods=["GET", "POST"])
def register_patient():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip()
        username = (request.form.get("username") or "").strip()
        name = (request.form.get("name") or "").strip()
        password = request.form.get("password") or ""
        age = request.form.get("age") or ""
        gender = request.form.get("gender") or ""


        if Patient.query.filter_by(email=email).first():
            flash("A patient with this email already exists. Please login.", "warning")
            return redirect("/login")

        if Patient.query.filter_by(username=username).first():
            flash("This username is already taken. Please choose another.", "warning")
            return redirect("/register_patient")

        patient = Patient(
            email=email,
            username=username,
            name=name,
            password=password,
            age=int(age) if age else None,
            gender=gender,
        )
        db.session.add(patient)
        db.session.commit()

        flash("Registration successful! Please login.", "success")
        return redirect("/login")

    return render_template("register_patient.html")



# -----------------------------------------LOGIN-----------------------------------------


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        role = request.form.get("role") or ""

        if role == "patient":
            patient = Patient.query.filter_by(username=username).first()
            if patient and patient.password == password:
                if patient.is_blacklisted:  
                    flash("Your patient account has been disabled. Please contact admin.", "danger")
                    return render_template("login.html")
                session["patient_id"] = patient.id
                return redirect(f"/patient/{patient.id}/dashboard")

        elif role == "doctor":
            doctor = Doctor.query.filter_by(username=username).first()
            if doctor and doctor.password == password:
                if doctor.is_blacklisted:  
                    flash("Your doctor account has been disabled. Please contact admin.", "danger")
                    return render_template("login.html")
                return redirect(f"/doctor/{doctor.id}/dashboard")

        elif role == "admin":
            admin = Admin.query.filter_by(username=username).first()
            if admin and admin.password == password:
                return redirect("/admin/dashboard")

        flash("Invalid username or password", "danger")
        return render_template("login.html")

    # GET
    return render_template("login.html")



# --------------------------------------------LOGOUT-----------------------


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")





# ============================= ADMIN ROUTES =============================


# -----------------------------------------ADMIN DASHBOARD-----------------------------------------
@app.route("/admin/dashboard", methods=["GET", "POST"])
def admin_dashboard():
    doctors = Doctor.query.order_by(Doctor.id).all()
    patients = Patient.query.order_by(Patient.id).all()
    return render_template(
        "admin_dashboard.html",
        Doctors=doctors,
        Patients=patients,
    )


# -----------------------------------------CREATE DEPARTMENT-----------------------------------------
@app.route("/admin/departments/create", methods=["GET", "POST"])
def create_department():
    if request.method == "POST":
        name = request.form.get("name")
        overview = request.form.get("overview")

        if Department.query.filter_by(name=name).first():
            flash("A department with this name already exists.", "warning")
            return redirect("/admin/departments/create")

        dept = Department(name=name, overview=overview)
        db.session.add(dept)
        db.session.commit()

        flash("Department created successfully.", "success")
        return redirect("/admin/dashboard")

    return render_template("create_department.html")


# -----------------------------------------ADD DOCTOR-----------------------------------------

@app.route("/admin/doctors/create", methods=["GET", "POST"])
def add_doctor():
    if request.method == "POST":
        username      = (request.form.get("username") or "").strip()
        name          = (request.form.get("name") or "").strip()
        email         = (request.form.get("email") or "").strip()
        password      = request.form.get("password") or ""
        description   = request.form.get("description") or ""
        experience    = request.form.get("experience", type=int)
        department_id = request.form.get("department_id", type=int)   

        if Doctor.query.filter_by(email=email).first():
            flash("A doctor with this email already exists.", "warning")
            return redirect("/admin/doctors/create")

        if Doctor.query.filter_by(username=username).first():
            flash("A doctor with this username already exists.", "warning")
            return redirect("/admin/doctors/create")

        dept = Department.query.get(department_id)
        if not dept:
            flash("Invalid department selected.", "danger")
            return redirect("/admin/doctors/create")

        doctor = Doctor(
            username=username,
            name=name,
            email=email,
            password=password,
            description=description,
            experience=experience,
            department=dept,        
        )

        db.session.add(doctor)
        db.session.commit()

        flash("Doctor added successfully.", "success")
        return redirect("/admin/dashboard")

    departments = Department.query.all()
    return render_template("add_doctor.html", departments=departments) 


#--------------------------------ADMIN APPOINTMENTS--------------------------------------

@app.route("/admin/appointments")
def admin_appointments():
    today = date.today()

    upcoming = (
        Appointment.query
        .filter(Appointment.date >= today)
        .order_by(Appointment.date.asc(), Appointment.start_time.asc())
        .all()
    )

    past = (
        Appointment.query
        .filter(Appointment.date < today)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    appointments = upcoming + past

    return render_template(
        "admin_appointments.html",
        Appointments=appointments
    )

#-------------------------------------admin_search--------------------------------------

@app.route("/admin/search", methods=["GET"])
def admin_search():
    doctor_query = (request.args.get("doctor_search") or "").strip()
    patient_query = (request.args.get("patient_search") or "").strip()

    doctors = []
    patients = []
    if doctor_query:
        doctors_by_name = Doctor.query.filter(
            Doctor.name.ilike(f"%{doctor_query}%")
        ).all()

        doctors_by_dept = Doctor.query.join(Department).filter(
            Department.name.ilike(f"%{doctor_query}%")
        ).all()

        doctors_by_id = []
        if doctor_query.isdigit():
            doctors_by_id = Doctor.query.filter_by(id=int(doctor_query)).all()

        d_tmp = {d.id: d for d in doctors_by_name}
        for d in doctors_by_dept:
            d_tmp[d.id] = d
        for d in doctors_by_id:
            d_tmp[d.id] = d

        doctors = list(d_tmp.values())


    if patient_query:
        patients_by_name = Patient.query.filter(
            Patient.name.ilike(f"%{patient_query}%")
        ).all()

        patients_by_age = []
        if patient_query.isdigit():
            patients_by_age = Patient.query.filter(
                Patient.age == int(patient_query)
            ).all()

 
        patients_by_gender = Patient.query.filter(
            Patient.gender.ilike(patient_query)
        ).all()


        p_tmp = {p.id: p for p in patients_by_name}
        for p in patients_by_age:
            p_tmp[p.id] = p
        for p in patients_by_gender:
            p_tmp[p.id] = p

        patients = list(p_tmp.values())

    return render_template(
        "admin_search.html",
        Doctors=doctors,
        Patients=patients,
        doctor_search=doctor_query,
        patient_search=patient_query,
    )

# -----------------------------------------EDIT DOCTOR-----------------------------------------
@app.route("/admin/doctors/<int:doctor_id>/edit", methods=["GET", "POST"])
def edit_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    departments = Department.query.all()

    if request.method == "POST":
        # store incoming values
        new_email = request.form.get("email") or doctor.email
        new_username = request.form.get("username") or doctor.username
        if new_username != doctor.username:
            if Doctor.query.filter_by(username=new_username).first():
                flash("Username already in use.", "warning")
                return redirect(f"/admin/doctors/{doctor_id}/edit")
        if new_email != doctor.email:
            if Doctor.query.filter_by(email=new_email).first():
                flash("Email already in use.", "warning")
                return redirect(f"/admin/doctors/{doctor_id}/edit")

        doctor.email = new_email
        doctor.username = new_username
        doctor.name = request.form.get("name") or doctor.name
        doctor.description = request.form.get("description") or doctor.description

        pwd = request.form.get("password")
        if pwd:
            doctor.password = pwd

        exp = request.form.get("experience")
        if exp:
            doctor.experience = int(exp)

        dept = request.form.get("department_id")
        if dept:
            doctor.department_id = int(dept)

        db.session.commit()
        flash("Doctor updated successfully.", "success")
        return redirect("/admin/dashboard")

    return render_template("edit_doctor.html", doctor=doctor, departments=departments)


#-----------------------------------------EDIT PATIENT----------------------------------------

@app.route("/admin/patients/<int:patient_id>/edit", methods=["GET", "POST"])
def admin_edit_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        age = request.form.get("age") or ""
        gender = request.form.get("gender") or ""

        if name:
            patient.name = name

        if age and age.isdigit():
            patient.age = int(age)

        if gender:
            patient.gender = gender

        db.session.commit()
        flash("Patient updated successfully.", "success")
        return redirect("/admin/dashboard")

    return render_template("admin_edit_patient.html", patient=patient)


# -----------------------------------------DELETE DOCTOR----------------------------------------
@app.route("/admin/doctors/<int:doctor_id>/delete", methods=["POST"])
def delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    if doctor.appointments:
        flash("Cannot delete doctor with appointments, Use Force Delete", "danger")
        return redirect("/admin/dashboard")
    availability = Availability.query.filter_by(doctor_id=doctor_id).all()
    for a in availability:
        db.session.delete(a)
    db.session.delete(doctor)
    db.session.commit()
    flash("Doctor deleted successfully.", "success")
    return redirect("/admin/dashboard")




#-----------------------------------------force delete-----------------------------------------


@app.route("/admin/doctors/<int:doctor_id>/force_delete", methods=["POST"])
def force_delete_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    appointments = Appointment.query.filter_by(doctor_id=doctor_id).all()
    for appt in appointments:
        db.session.delete(appt)

    availabilities = Availability.query.filter_by(doctor_id=doctor_id).all()
    for slot in availabilities:
        db.session.delete(slot)

    db.session.delete(doctor)
    db.session.commit()

    flash("Doctor and all related appointments & availability deleted successfully.", "success")
    return redirect("/admin/dashboard")




# -----------------------------------------DELETE PATIENT-----------------------------------------
@app.route("/admin/patients/<int:patient_id>/delete", methods=["POST"])
def delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.appointments:
        flash("Cannot delete patient with appointments. Use Force Delete", "danger")
        return redirect("/admin/dashboard")
    db.session.delete(patient)
    db.session.commit()
    flash("Patient deleted successfully.", "success")
    return redirect("/admin/dashboard")


#-----------------------------------------force delete-----------------------------------------


@app.route("/admin/patients/<int:patient_id>/force_delete", methods=["POST"])
def force_delete_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    appointments = Appointment.query.filter_by(patient_id=patient_id).all()
    for appt in appointments:
        db.session.delete(appt)

    # finally delete the patient
    db.session.delete(patient)
    db.session.commit()

    flash("Patient and all related appointments deleted successfully.", "success")
    return redirect("/admin/dashboard")



# -------------------------------- ADMIN: VIEW PATIENT HISTORY --------------------------------

@app.route("/admin/patients/<int:patient_id>/history")
def admin_patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status == "Completed",  
        )
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    return render_template(
        "admin_patient_history.html",
        patient=patient,
        appointments=appointments,
    )

#-------------------------admin past appointment view---------------------------------------


@app.route("/admin/appointments/<int:appointment_id>", methods=["GET"])
def admin_past_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    patient = appt.patient

    appointments = (
        Appointment.query
        .filter_by(patient_id=patient.id, status = "Completed")         
        .order_by(Appointment.date.desc())
        .all()
    )
    return render_template(
        "admin_past_appointment.html",
        appt=appt,                
        appointments=appointments 
    )

#----------------------------------------blacklist and unblacklist patient and doctor-------------------------------

@app.route("/admin/doctors/<int:doctor_id>/blacklist", methods=["POST"])
def admin_blacklist_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    doctor.is_blacklisted = True

    today = date.today()

    upcoming_appointments = Appointment.query.filter(
        Appointment.doctor_id == doctor_id,
        Appointment.date >= today,
        Appointment.status == "Booked"
    ).all()

    for appt in upcoming_appointments:
        slot = Availability.query.filter_by(
            doctor_id=doctor_id,
            date=appt.date,
            start_time=appt.start_time
        ).first()
        if slot:
            slot.is_booked = False

        appt.status = "Cancelled"

    db.session.commit()

    flash("Doctor blacklisted. All upcoming appointments cancelled.", "success")
    return redirect("/admin/dashboard")


@app.route("/admin/doctors/<int:doctor_id>/unblacklist", methods=["POST"])
def admin_unblacklist_doctor(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    doctor.is_blacklisted = False
    db.session.commit()
    flash("Doctor un-blacklisted successfully.", "success")
    return redirect("/admin/dashboard")


@app.route("/admin/patients/<int:patient_id>/blacklist", methods=["POST"])
def admin_blacklist_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_blacklisted = True

    today = date.today()

    upcoming_appointments = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.date >= today,
        Appointment.status == "Booked"
    ).all()

    for appt in upcoming_appointments:
        slot = Availability.query.filter_by(
            doctor_id=appt.doctor_id,
            date=appt.date,
            start_time=appt.start_time
        ).first()
        if slot:
            slot.is_booked = False

        db.session.delete(appt)

    db.session.commit()
    flash("Patient blacklisted. All upcoming appointments removed.", "success")
    return redirect("/admin/dashboard")



@app.route("/admin/patients/<int:patient_id>/unblacklist", methods=["POST"])
def admin_unblacklist_patient(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    patient.is_blacklisted = False
    db.session.commit()
    flash("Patient un-blacklisted successfully.", "success")
    return redirect("/admin/dashboard")




# ============================= DOCTOR ROUTES =============================


# -----------------------------------------DOCTOR DASHBOARD----------------------------------------

@app.route("/doctor/<int:doctor_id>/dashboard", methods=["GET", "POST"])
def doctor_dashboard(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    today = datetime.today().date()
    end = today + timedelta(days=7)

    if doctor.is_blacklisted:   
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")

    appointments = (
        Appointment.query
        .filter(
            Appointment.doctor_id == doctor_id,
            Appointment.date >= today,
            Appointment.date <= end,
            Appointment.status == "Booked",  
        )
        .order_by(Appointment.date.asc(), Appointment.start_time.asc())
        .all()
    )

    return render_template("doctor_dashboard.html", doctor=doctor, appointments=appointments)

# ----------------------------------PROVIDE AVAILABILITY----------------------------------

@app.route("/doctor/<int:doctor_id>/availability", methods=["GET", "POST"])
def provide_availability(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)

    if doctor.is_blacklisted:  
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")

    today = datetime.today().date()
    next_7_days = [today + timedelta(days=i) for i in range(7)]
    hours = [time(h, 0) for h in range(9, 19)] 
    if request.method == "POST":
        date_str = request.form["date"]
        start_str = request.form["time"]  

        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        t_start = datetime.strptime(start_str, "%H:%M").time()
        t_end = (datetime.combine(d, t_start) + timedelta(hours=1)).time()

        slot = Availability.query.filter_by(
            doctor_id=doctor_id, date=d, start_time=t_start
        ).first()

        if slot and not slot.is_booked:
            db.session.delete(slot)
        elif not slot:
            db.session.add(
                Availability(
                    doctor_id=doctor_id,
                    date=d,
                    start_time=t_start,
                    end_time=t_end,  # stored in DB
                    is_booked=False,
                )
            )

        db.session.commit()
        return redirect(f"/doctor/{doctor_id}/availability")

    all_slots = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        Availability.date >= next_7_days[0],
        Availability.date <= next_7_days[-1],
    ).all()

    selected = {(s.date, s.start_time) for s in all_slots}
    booked = {(s.date, s.start_time) for s in all_slots if s.is_booked}

    return render_template(
        "provide_availability.html",
        doctor=doctor,
        days=next_7_days,
        hours=hours,
        selected=selected,
        booked=booked,
    )

# -----------------------------------------UPDATE and COMPLETE PATIENT HISTORY-----------------------------------------

@app.route("/appointments/<int:appointment_id>/history/update", methods=["GET", "POST"])
def update_patient_history(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    if request.method == "POST":
        appt.notes = request.form.get("test_done")
        appt.diagnosis = request.form.get("diagnosis")
        appt.prescription = request.form.get("prescription")
        appt.medicine = request.form.get("medicine")

        action = request.form.get("action", "complete")

        if action == "complete":
            appt.status = "Completed"

        db.session.commit()

        flash("Patient history saved and appointment marked completed.", "success")
        return redirect(f"/doctor/{appt.doctor_id}/dashboard")

    return render_template("update_patient_history.html", appt=appt)

# -------------------------------------------doctor cancel----------------------------------------


@app.route("/doctor/appointments/<int:appointment_id>/cancel", methods=["POST"])
def doctor_cancel_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)

    
    if appt.status != "Booked":
        flash("Only booked appointments can be cancelled.", "warning")
        return redirect(f"/doctor/{appt.doctor_id}/dashboard")

    slot = Availability.query.filter_by(
        doctor_id=appt.doctor_id,
        date=appt.date,
        start_time=appt.start_time,
    ).first()
    if slot:
        slot.is_booked = False 

    appt.status = "Cancelled"

    db.session.commit()
    flash("Appointment cancelled. Other patients can now book this slot.", "success")
    return redirect(f"/doctor/{appt.doctor_id}/dashboard")


# ------------------------------------------ Doctor view patient history----------------------------------------

@app.route("/appointments/<int:appointment_id>/history/view")
def view_patient_history(appointment_id):
 
    appt = Appointment.query.get_or_404(appointment_id)

    patient = appt.patient
    current_doctor = appt.doctor

    history_appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient.id,
            Appointment.status == "Completed"
        )
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    return render_template(
        "doctor_view_history.html",
        patient=patient,
        history_appointments=history_appointments,
        current_doctor=current_doctor
    )
#---------------------------------------------Doctor past appointments---------------------------------------

@app.route("/doctor/<int:doctor_id>/appointments/past")
def doctor_past_appointments(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    if doctor.is_blacklisted:
        session.clear()
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")
    today = date.today()
    completed_and_cancelled = (
        Appointment.query
        .filter(Appointment.doctor_id == doctor_id)
        .filter(Appointment.status.in_(["Completed", "Cancelled"]))
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )
    past_booked = (
        Appointment.query
        .filter(Appointment.doctor_id == doctor_id)
        .filter(Appointment.status == "Booked")
        .filter(Appointment.date < today)
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )
    appointments = completed_and_cancelled + past_booked

    return render_template(
        "doctor_past_appointments.html",
        doctor=doctor,
        appointments=appointments,
        current_date=today
    )



# ============================= PATIENT ROUTES =============================


# -----------------------------------------PATIENT DASHBOARD-----------------------------------------

@app.route("/patient/<int:patient_id>/dashboard")
def patient_dashboard(patient_id):
    patient = Patient.query.get_or_404(patient_id)
    if patient.is_blacklisted:
        session.clear()
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")

    departments = Department.query.all()

    today = date.today()
    seven_days_later = today + timedelta(days=7)

    appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.date >= today,
            Appointment.date <= seven_days_later,
            Appointment.status.in_(["Booked", "Cancelled", "Completed"])
        )
        .order_by(Appointment.date, Appointment.start_time)
        .all()
    )

    return render_template(
        "patient_dashboard.html",
        patient=patient,
        departments=departments,
        appointments=appointments,
    )

#---------------------------------------------------Patient search----------------------------------------------

@app.route("/patient/<int:patient_id>/search", methods=["GET"])
def patient_search(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if patient.is_blacklisted:
        session.clear()
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")

    query = (request.args.get("search") or "").strip()
    departments = []
    doctors = []

    if query:
        departments = Department.query.filter(
            Department.name.ilike(f"%{query}%")
        ).all()

        doctors = Doctor.query.filter(
          Doctor.name.ilike(f"%{query}%"),
          Doctor.is_blacklisted == False
           ).all()

    return render_template(
        "patient_search.html",
        patient=patient,
        patient_id=patient_id,
        search=query,
        departments=departments,
        doctors=doctors,
    )


# ----------------------------------PATIENT DASHBOARD EDIT PROFILE----------------------------------

@app.route("/patient/<int:patient_id>/profile/edit", methods=["GET", "POST"])
def edit_profile(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    if patient.is_blacklisted:
        session.clear()
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")

    if request.method == "POST":
        new_username = (request.form.get("username") or "").strip()
        new_name = (request.form.get("name") or "").strip()
        age = request.form.get("age") or ""
        gender = request.form.get("gender") or ""
        email = (request.form.get("email") or "").strip()

        if new_username:
            if new_username != patient.username and Patient.query.filter_by(username=new_username).first():
                flash("This username is already taken.", "warning")
                return redirect(f"/patient/{patient.id}/profile/edit")
            patient.username = new_username

        if new_name:
            patient.name = new_name

        if age:
            patient.age = int(age)

        if gender:
            patient.gender = gender

        if email:
            if email != patient.email and Patient.query.filter_by(email=email).first():
                flash("This email is already in use.", "warning")
                return redirect(f"/patient/{patient.id}/profile/edit")
            patient.email = email

        password = request.form.get("password")
        if password:
            patient.password = password  # plain text for now

        db.session.commit()
        flash("Patient updated successfully.", "success")
        return redirect(f"/patient/{patient.id}/dashboard")

    return render_template("edit_profile.html", patient=patient)


# ------------------------------------VIEW DEPARTMENT DETAILS------------------------------------

@app.route("/patient/<int:patient_id>/departments/<int:dept_id>")
def view_department_details(patient_id, dept_id):
    department = Department.query.get_or_404(dept_id)
    doctors = Doctor.query.filter_by(department_id=dept_id, is_blacklisted=False).all() 
    return render_template(
        "view_department_details.html",
        department=department,
        doctors=doctors,
        patient_id=patient_id,
    )


# ------------------------------------VIEW DOCTOR DETAILS------------------------------------

@app.route("/patient/doctors/<int:doctor_id>")
def view_doctor_details(doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    patient_id = session.get("patient_id")
    dept_id = doctor.department_id

    return render_template(
        "view_doctors_details.html",
        doctor=doctor,
        patient_id=patient_id,
        dept_id=dept_id,
    )


# ----------------------------------PATIENT BOOK APPOINTMENT----------------------------------

@app.route("/patient/<int:patient_id>/doctors/<int:doctor_id>/availability", methods=["GET","POST"])
def book_availability(patient_id, doctor_id):
    doctor = Doctor.query.get_or_404(doctor_id)
    patient = Patient.query.get_or_404(patient_id)

    if patient.is_blacklisted:
        session.clear()
        flash("Your account has been disabled. Please contact admin.", "danger")
        return redirect("/login")
    
    if doctor.is_blacklisted:
        session.clear()
        flash("doctor is no longer available.", "danger")
        return redirect(f"/patient/{patient_id}/dashboard")

    today = date.today()
    days  = [today + timedelta(days=i) for i in range(7)]
    hours = [time(h, 0) for h in range(9, 19)]
    url   = f"/patient/{patient_id}/doctors/{doctor_id}/availability"

    if request.method == "POST":
        d     = datetime.strptime(request.form["date"], "%Y-%m-%d").date()
        start = datetime.strptime(request.form["time"], "%H:%M").time()
        end   = (datetime.combine(d, start) + timedelta(hours=1)).time()

        if Appointment.query.filter_by(
            patient_id=patient_id, doctor_id=doctor_id,
            date=d, start_time=start, status="Cancelled"
        ).first():
            flash(" Doctor have cancelled the appointment you can't book this doctor again")
            return redirect(url)


        if Appointment.query.filter(
            Appointment.patient_id == patient_id,
            Appointment.date == d,
            Appointment.start_time == start,
            Appointment.status.in_(["Booked", "Completed"])
        ).first():
            flash("You already have an appointment at this time.", "warning")
            return redirect(url)

        slot = Availability.query.filter_by(
            doctor_id=doctor_id, date=d, start_time=start
        ).first()
        if not slot or slot.is_booked:
            flash("That slot is no longer available.", "warning")
            return redirect(url)

        db.session.add(Appointment(
            patient_id=patient_id, doctor_id=doctor_id,
            date=d, start_time=start, end_time=end, status="Booked"
        ))
        slot.is_booked = True
        db.session.commit()
        flash("Appointment booked.", "success")
        return redirect(url)

    slots = Availability.query.filter(
        Availability.doctor_id == doctor_id,
        Availability.date.between(days[0], days[-1])
    ).all()

    provided_free   = {(s.date, s.start_time) for s in slots if not s.is_booked}
    provided_booked = {(s.date, s.start_time) for s in slots if s.is_booked}

    aps = Appointment.query.filter(
        Appointment.patient_id == patient_id,
        Appointment.date.between(days[0], days[-1])
    ).all()

    patient_booked     = {(a.date, a.start_time) for a in aps if a.doctor_id == doctor_id and a.status == "Booked"}
    patient_cancelled  = {(a.date, a.start_time) for a in aps if a.doctor_id == doctor_id and a.status == "Cancelled"}
    patient_completed  = {(a.date, a.start_time) for a in aps if a.doctor_id == doctor_id and a.status == "Completed"}
    patient_all_booked = {(a.date, a.start_time) for a in aps if a.status in ("Booked", "Completed")}

    return render_template(
        "book_availability.html",
        doctor=doctor, patient=patient,
        days=days, hours=hours,
        provided_free=provided_free, provided_booked=provided_booked,
        patient_booked=patient_booked, patient_cancelled=patient_cancelled,
        patient_completed=patient_completed, patient_all_booked=patient_all_booked,
    )

# ----------------------------------CANCEL APPOINTMENT----------------------------------
@app.route("/patient/appointments/<int:appointment_id>/cancel", methods=["POST"])
def cancel_appointment(appointment_id):
    appt = Appointment.query.get_or_404(appointment_id)


    pid = session.get("patient_id")
    pid_or = pid or appt.patient_id
    if pid and appt.patient_id != pid:
        flash("Not authorized to cancel this appointment.", "danger")
        return redirect(f"/patient/{pid_or}/dashboard")

    slot = Availability.query.filter_by(
        doctor_id=appt.doctor_id,
        date=appt.date,
        start_time=appt.start_time,
    ).first()
    if slot:
        slot.is_booked = False

    db.session.delete(appt) 
    db.session.commit()
    flash("Appointment cancelled.", "success")
    return redirect(f"/patient/{appt.patient_id}/dashboard")


#---------------------------------Patient history----------------------------------

@app.route("/patient/<int:patient_id>/history")
def patient_history(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.status == "Completed",
        )
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    return render_template(
        "patient_history.html",
        patient=patient,
        appointments=appointments,
    )


#---------------------------------Patient Past appointments----------------------------------

@app.route("/patient/<int:patient_id>/appointments/past")
def patient_past_appointments(patient_id):
    patient = Patient.query.get_or_404(patient_id)

    today = date.today()
    appointments = (
        Appointment.query
        .filter(
            Appointment.patient_id == patient_id,
            Appointment.date < today
        )
        .order_by(Appointment.date.desc(), Appointment.start_time.desc())
        .all()
    )

    return render_template(
        "patient_past_appointments.html",
        patient=patient,
        appointments=appointments
    )


if __name__ == "__main__":
    app.run(debug=True)



