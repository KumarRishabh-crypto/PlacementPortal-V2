from datetime import datetime
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


# ---------------- USER MODEL ----------------
class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # admin / company / student
    is_active = db.Column(db.Boolean, default=True)
    is_blacklisted = db.Column(db.Boolean, default=False)

    # 🔥 CASCADE FIX
    student = db.relationship(
        'Student',
        backref='user',
        uselist=False,
        cascade='all, delete-orphan'
    )

    company = db.relationship(
        'Company',
        backref='user',
        uselist=False,
        cascade='all, delete-orphan'
    )


# ---------------- STUDENT MODEL ----------------
class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    roll_no = db.Column(db.String(50), unique=True, nullable=False)
    branch = db.Column(db.String(100))
    cgpa = db.Column(db.Float)
    phone = db.Column(db.String(15))

    # 🔥 CASCADE FIX
    applications = db.relationship(
        'Application',
        backref='student',
        cascade='all, delete-orphan',
        lazy=True
    )


# ---------------- COMPANY MODEL ----------------
class Company(db.Model):
    __tablename__ = 'companies'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    company_name = db.Column(db.String(150), nullable=False)
    hr_contact = db.Column(db.String(100))
    website = db.Column(db.String(150))
    approval_status = db.Column(
        db.String(20),
        default='Pending'
    )  # Pending / Approved / Rejected

    # 🔥 CASCADE FIX
    drives = db.relationship(
        'PlacementDrive',
        backref='company',
        cascade='all, delete-orphan',
        lazy=True
    )


# ---------------- PLACEMENT DRIVE MODEL ----------------
class PlacementDrive(db.Model):
    __tablename__ = 'placement_drives'

    id = db.Column(db.Integer, primary_key=True)
    company_id = db.Column(
        db.Integer,
        db.ForeignKey('companies.id', ondelete='CASCADE'),
        nullable=False
    )
    job_title = db.Column(db.String(150), nullable=False)
    job_description = db.Column(db.Text)
    eligibility = db.Column(db.String(200))
    application_deadline = db.Column(db.Date)
    status = db.Column(
        db.String(20),
        default='Pending'
    )  # Pending / Approved / Closed

    # 🔥 CASCADE FIX
    applications = db.relationship(
        'Application',
        backref='drive',
        cascade='all, delete-orphan',
        lazy=True
    )


# ---------------- APPLICATION MODEL ----------------
class Application(db.Model):
    __tablename__ = 'applications'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey('students.id', ondelete='CASCADE'),
        nullable=False
    )
    drive_id = db.Column(
        db.Integer,
        db.ForeignKey('placement_drives.id', ondelete='CASCADE'),
        nullable=False
    )
    applied_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(
        db.String(20),
        default='Applied'
    )  # Applied / Shortlisted / Selected / Rejected

    __table_args__ = (
        db.UniqueConstraint(
            'student_id',
            'drive_id',
            name='unique_student_drive'
        ),
    )
