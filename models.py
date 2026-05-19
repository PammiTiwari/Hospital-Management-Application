from extension import db
from flask_login import UserMixin 
from datetime import datetime

#--------------------------------------------------ADMIN----------------------------------------------------------------------------
class Admin(db.Model):
    __tablename__ = "admin"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

#--------------------------------------------------PATIENT----------------------------------------------------------------------------
class Patient(db.Model):
    __tablename__ = "patient"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)
    appointments = db.relationship("Appointment", backref="patient", lazy=True)

#--------------------------------------------------DEPARTMENT---------------------------------------------------------------------------
class Department(db.Model):
    __tablename__ = "department"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    overview = db.Column(db.Text, nullable=False)
    doctors = db.relationship("Doctor", backref="department", lazy=True)

#--------------------------------------------------DOCTOR----------------------------------------------------------------------------------
class Doctor(db.Model):
    __tablename__ = "doctor"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    password = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    experience = db.Column(db.Integer, nullable=False)
    is_blacklisted = db.Column(db.Boolean, default=False, nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("department.id"), nullable=False)
    availabilities = db.relationship("Availability", backref="doctor", lazy=True)
    appointments = db.relationship("Appointment", backref="doctor", lazy=True)

# --------------------------------------------------AVAILABILITY----------------------------------------------------------------------------
class Availability(db.Model):
    __tablename__ = "availability"
    id         = db.Column(db.Integer, primary_key=True)
    doctor_id  = db.Column(db.Integer, db.ForeignKey("doctor.id"), nullable=False)
    date       = db.Column(db.Date,  nullable=False)
    start_time = db.Column(db.Time,  nullable=False)
    end_time   = db.Column(db.Time,  nullable=False)
    is_booked  = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("doctor_id", "date", "start_time", name="uq_availability_doc_date_hour"),
    )

# ------------------------------------------ APPOINTMENT AND TREATMENT ----------------------------------------------------------------------------------------
class Appointment(db.Model):
    __tablename__ = "appointment"
    id         = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey("patient.id"), nullable=False, index=True)
    doctor_id  = db.Column(db.Integer, db.ForeignKey("doctor.id"),  nullable=False, index=True)
    date       = db.Column(db.Date,  nullable=False, index=True)
    start_time = db.Column(db.Time,  nullable=False)
    end_time   = db.Column(db.Time,  nullable=False)
    status     = db.Column(db.String(20), default="Booked")  # Booked / Completed / Cancelled / Not Visited
    notes      = db.Column(db.Text)

    # simple treatment fields
    diagnosis    = db.Column(db.Text)
    prescription = db.Column(db.Text)
    medicine     = db.Column(db.Text)

#----------------------------------------------------CREATING DEFAULT ADMIN---------------------------------------------------------------
def create_default_admin():
    create_default_username = 'admin'
    create_default_password = 'admin'

    user = Admin(username=create_default_username, password=create_default_password)
    if not Admin.query.filter_by(username=create_default_username).first():
        db.session.add(user)
        db.session.commit()

#-------------------------------------DEFAULT 4 DEPARTMENT--------------------------------------------------------------
def create_default_departments():
    departments = [
        {'name': 'Cardiology', 'overview': 'Cardiology department'},
        {'name': 'Orthopedics', 'overview': 'Orthopedics department'},
        {'name': 'Gynecology', 'overview': 'Gynecology department'},
        {'name': 'Pediatrics', 'overview': 'Pediatrics department'}
    ]

    for department in departments:
        if not Department.query.filter_by(name=department['name']).first():
            dept = Department(name=department['name'], overview=department['overview'])
            db.session.add(dept)
            db.session.commit()
