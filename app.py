from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from models import db, User, Student, Company, PlacementDrive, Application
from datetime import datetime, date

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        db.create_all()

        # Admin
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                name='Admin',
                email='admin@college.com',
                password=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Admin created: admin@college.com / admin123")
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            selected_role = request.form['role'].lower()  # 👈 IMPORTANT

            user = User.query.filter_by(email=email).first()

            if not user:
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))

            # 🔐 ROLE MISMATCH CHECK
            if user.role != selected_role:
                flash('Incorrect role selected for this account', 'danger')
                return redirect(url_for('login'))

            if user.is_blacklisted:
                flash('Your account has been blacklisted. Contact admin.', 'danger')
                return redirect(url_for('login'))

            if not check_password_hash(user.password, password):
                flash('Invalid email or password', 'danger')
                return redirect(url_for('login'))

            if user.role == 'company' and user.company.approval_status != 'Approved':
                flash('Company not approved by admin yet.', 'warning')
                return redirect(url_for('login'))

            login_user(user)

            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'company':
                return redirect(url_for('company_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))

        return render_template('auth/login.html')

    @app.route('/logout', methods=['GET', 'POST'])
    @login_required
    def logout():
        logout_user()
        session.clear()
        flash('Logged out successfully', 'success')
        return redirect(url_for('login'))


    @app.route('/register/student', methods=['GET', 'POST'])
    def student_register():
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            roll_no = request.form['roll_no']
            branch_select = request.form.get('branch_select')
            branch_manual = request.form.get('branch_manual')

            branch = branch_manual.strip() if branch_manual else branch_select

            if not branch:
                flash('Please select or enter a department', 'danger')
                return redirect(url_for('student_register'))

            cgpa = request.form['cgpa']
            phone = request.form['phone']

            # Check existing user
            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return redirect(url_for('student_register'))

            # Check duplicate roll number
            if Student.query.filter_by(roll_no=roll_no).first():
                flash('Roll number already exists', 'danger')
                return redirect(url_for('student_register'))
            
            if request.form['password'] != request.form['confirm_password']:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('student_register'))


            # Create User
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role='student'
            )
            db.session.add(user)
            db.session.commit()

            # Create Student profile
            student = Student(
                user_id=user.id,
                roll_no=roll_no,
                branch=branch,
                cgpa=cgpa,
                phone=phone
            )
            db.session.add(student)
            db.session.commit()

            flash('Student registered successfully. Please login.', 'success')
            return redirect(url_for('login'))

        return render_template('auth/student_register.html')

    @app.route('/register/company', methods=['GET', 'POST'])
    def company_register():
        if request.method == 'POST':
            name = request.form['name']
            email = request.form['email']
            password = request.form['password']
            company_name = request.form['company_name']
            hr_contact = request.form['hr_contact']
            website = request.form['website']

            if User.query.filter_by(email=email).first():
                flash('Email already registered', 'danger')
                return redirect(url_for('company_register'))
  
            if request.form['password'] != request.form['confirm_password']:
                flash('Passwords do not match', 'danger')
                return redirect(url_for('company_register'))

            # Create user
            user = User(
                name=name,
                email=email,
                password=generate_password_hash(password),
                role='company'
            )
            db.session.add(user)
            db.session.commit()

            # Create company profile
            company = Company(
                user_id=user.id,
                company_name=company_name,
                hr_contact=hr_contact,
                website=website,
                approval_status='Pending'
            )
            db.session.add(company)
            db.session.commit()

            flash('Company registered. Wait for admin approval.', 'success')
            return redirect(url_for('login'))

        return render_template('auth/company_register.html')


# <------------Admin Routes----------->


    @app.route('/admin/dashboard')
    @login_required
    def admin_dashboard():
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        # COUNTS (for cards & charts)
        total_students = Student.query.count()
        total_companies = Company.query.count()
        total_drives = PlacementDrive.query.count()
        total_applications = Application.query.count()

        approved_companies_count = Company.query.filter_by(
            approval_status='Approved'
        ).count()

        pending_companies_count = Company.query.filter_by(
            approval_status='Pending'
        ).count()

        active_students_count = User.query.filter_by(
            role='student',
            is_blacklisted=False
        ).count()

        blacklisted_students_count = User.query.filter_by(
            role='student',
            is_blacklisted=True
        ).count()

        # LISTS (for tables)
        pending_companies = Company.query.filter_by(
            approval_status='Pending'
        ).all()

        pending_drives = PlacementDrive.query.filter_by(
            status='Pending'
        ).all()

        return render_template(
            'admin/dashboard.html',
            total_students=total_students,
            total_companies=total_companies,
            total_drives=total_drives,
            total_applications=total_applications,

            approved_companies_count=approved_companies_count,
            pending_companies_count=pending_companies_count,
            active_students_count=active_students_count,
            blacklisted_students_count=blacklisted_students_count,

            pending_companies=pending_companies,
            pending_drives=pending_drives
        )


    @app.route('/admin/companies')
    @login_required
    def manage_companies():
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        companies = Company.query.all()
        return render_template('admin/manage_companies.html', companies=companies)

    @app.route('/admin/company/<int:company_id>/<action>')
    @login_required
    def update_company_status(company_id, action):
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        company = Company.query.get_or_404(company_id)

        if action == 'approve':
            company.approval_status = 'Approved'
        elif action == 'reject':
            company.approval_status = 'Rejected'

        db.session.commit()
        flash('Company status updated', 'success')
        return redirect(url_for('manage_companies'))

    @app.route('/admin/students')
    @login_required
    def manage_students():
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        query = request.args.get('q')

        students_query = Student.query.join(User)

        if query:
            students_query = students_query.filter(
                (User.name.ilike(f'%{query}%')) |
                (Student.roll_no.ilike(f'%{query}%')) |
                (Student.phone.ilike(f'%{query}%'))
            )

        students = students_query.all()

        return render_template(
            'admin/manage_students.html',
            students=students,
            query=query
        )

    @app.route('/admin/student/<int:student_id>/applications')
    @login_required
    def admin_student_applications(student_id):
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        student = Student.query.get_or_404(student_id)

        applications = Application.query.filter_by(
            student_id=student.id
        ).order_by(Application.applied_date.desc()).all()

        return render_template(
            'admin/applications.html',
            student=student,
            applications=applications
        )

    @app.route('/admin/user/<int:user_id>/blacklist')
    @login_required
    def toggle_blacklist(user_id):
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        user = User.query.get_or_404(user_id)
        user.is_blacklisted = not user.is_blacklisted
        db.session.commit()

        status = "Blacklisted" if user.is_blacklisted else "Unblocked"
        flash(f'User {status} successfully', 'success')

        return redirect(request.referrer)

    @app.route('/admin/user/<int:user_id>/delete')
    @login_required
    def delete_user(user_id):
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        user = User.query.get_or_404(user_id)

        if user.role == 'admin':
            flash('Cannot delete admin', 'danger')
            return redirect(request.referrer)

        db.session.delete(user)
        db.session.commit()

        flash('User deleted successfully', 'success')
        return redirect(request.referrer)

    @app.route('/admin/drives')
    @login_required
    def manage_drives():
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        drives = PlacementDrive.query.all()
        return render_template('admin/manage_drives.html', drives=drives)

    @app.route('/admin/drives/<int:drive_id>/<action>')
    @login_required
    def update_drive_status(drive_id, action):
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        drive = PlacementDrive.query.get_or_404(drive_id)

        if action == 'approve':
            drive.status = 'Approved'
        elif action == 'reject':
            drive.status = 'Rejected'

        db.session.commit()
        flash('Placement drive status updated', 'success')
        return redirect(url_for('manage_drives'))


    @app.route('/admin/drives/<int:drive_id>/delete')
    @login_required
    def delete_drive(drive_id):
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        drive = PlacementDrive.query.get_or_404(drive_id)
        db.session.delete(drive)
        db.session.commit()

        flash('Placement drive deleted successfully', 'success')
        return redirect(url_for('manage_drives'))


    @app.route('/admin/applications')
    @login_required
    def admin_applications():
        if current_user.role != 'admin':
            return redirect(url_for('login'))

        status = request.args.get('status')
        search = request.args.get('q')

        query = Application.query.join(Student).join(User).join(PlacementDrive).join(Company)

        if status:
            query = query.filter(Application.status == status)

        if search:
            query = query.filter(
                (User.name.ilike(f'%{search}%')) |
                (Company.company_name.ilike(f'%{search}%')) |
                (PlacementDrive.job_title.ilike(f'%{search}%'))
            )

        applications = query.order_by(Application.applied_date.desc()).all()

        return render_template(
            'admin/applications.html',
            applications=applications,
            status=status,
            search=search
        )


# <------------Company Routes----------->


    @app.route('/company/dashboard')
    @login_required
    def company_dashboard():
        if current_user.role != 'company':
            return redirect(url_for('login'))

        company = Company.query.filter_by(user_id=current_user.id).first()

        # TOTAL DRIVES
        total_drives = PlacementDrive.query.filter_by(company_id=company.id).count()

        # TOTAL APPLICATIONS
        total_applications = db.session.query(Application) \
            .join(PlacementDrive) \
            .filter(PlacementDrive.company_id == company.id) \
            .count()

        # SHORTLISTED
        shortlisted_count = Application.query \
            .join(PlacementDrive) \
            .filter(
                PlacementDrive.company_id == company.id,
                Application.status == 'Shortlisted'
            ).count()

        # SELECTED
        selected_count = Application.query \
            .join(PlacementDrive) \
            .filter(
                PlacementDrive.company_id == company.id,
                Application.status == 'Selected'
            ).count()

        # RECENT DRIVES (for right-side section)
        recent_drives = PlacementDrive.query \
            .filter_by(company_id=company.id) \
            .order_by(PlacementDrive.id.desc()) \
            .limit(4) \
            .all()

        return render_template(
            'company/dashboard.html',
            company=company,
            total_drives=total_drives,
            total_applications=total_applications,
            shortlisted_count=shortlisted_count,
            selected_count=selected_count,
            recent_drives=recent_drives
        )

    @app.route('/company/drives/create', methods=['GET', 'POST'])
    @login_required
    def create_drive():
        if current_user.role != 'company':
            return redirect(url_for('login'))

        company = current_user.company

        if company.approval_status != 'Approved':
            flash('Company not approved by admin.', 'danger')
            return redirect(url_for('company_dashboard'))

        if request.method == 'POST':
            job_title = request.form['job_title']
            description = request.form['description']
            eligibility = request.form['eligibility']
            deadline = request.form['deadline']

            drive = PlacementDrive(
                company_id=company.id,
                job_title=job_title,
                job_description=description,
                eligibility=eligibility,
                application_deadline=datetime.strptime(deadline, '%Y-%m-%d'),
                status='Pending'
            )

            db.session.add(drive)
            db.session.commit()

            flash('Placement drive created. Await admin approval.', 'success')
            return redirect(url_for('company_drives'))

        return render_template('company/create_drive.html')

    @app.route('/company/drives')
    @login_required
    def company_drives():
        if current_user.role != 'company':
            return redirect(url_for('login'))

        drives = PlacementDrive.query.filter_by(
            company_id=current_user.company.id
        ).all()

        return render_template('company/drives.html', drives=drives)

    @app.route('/company/drives/<int:drive_id>/close')
    @login_required
    def close_drive(drive_id):
        if current_user.role != 'company':
            return redirect(url_for('login'))

        drive = PlacementDrive.query.get_or_404(drive_id)

        if drive.company_id != current_user.company.id:
            return redirect(url_for('company_drives'))

        drive.status = 'Closed'
        db.session.commit()

        flash('Drive closed successfully', 'success')
        return redirect(url_for('company_drives'))

    @app.route('/company/drives/<int:drive_id>/edit', methods=['GET', 'POST'])
    @login_required
    def edit_drive(drive_id):
        if current_user.role != 'company':
            return redirect(url_for('login'))

        drive = PlacementDrive.query.get_or_404(drive_id)

        if drive.company_id != current_user.company.id:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('company_drives'))

        if request.method == 'POST':
            drive.job_title = request.form['job_title']
            drive.job_description = request.form['description']
            drive.eligibility = request.form['eligibility']
            drive.application_deadline = datetime.strptime(
                request.form['deadline'], '%Y-%m-%d'
            )

            # editing requires re-approval
            drive.status = 'Pending'
            db.session.commit()

            flash('Drive updated. Await admin approval.', 'success')
            return redirect(url_for('company_drives'))

        return render_template('company/edit_drive.html', drive=drive)


    @app.route('/company/drives/<int:drive_id>/view')
    @login_required
    def view_drive(drive_id):
        if current_user.role != 'company':
            return redirect(url_for('login'))

        drive = PlacementDrive.query.get_or_404(drive_id)

        if drive.company_id != current_user.company.id:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('company_drives'))

        return render_template('company/view_drive.html', drive=drive)


    @app.route('/company/applications')
    @login_required
    def company_applications():
        if current_user.role != 'company':
            return redirect(url_for('login'))

        company = current_user.company

        drives = PlacementDrive.query.filter_by(
            company_id=company.id
        ).all()

        return render_template(
            'company/applications.html',
            drives=drives
        )

    @app.route('/company/drive/<int:drive_id>/applications')
    @login_required
    def drive_applications(drive_id):
        if current_user.role != 'company':
            return redirect(url_for('login'))

        drive = PlacementDrive.query.get_or_404(drive_id)

        if drive.company_id != current_user.company.id:
            return redirect(url_for('company_applications'))

        applications = Application.query.filter_by(
            drive_id=drive.id
        ).all()

        return render_template(
            'company/drive_applications.html',
            drive=drive,
            applications=applications
        )

    @app.route('/company/application/<int:app_id>/update/<status>')
    @login_required
    def update_application_status(app_id, status):
        if current_user.role != 'company':
            return redirect(url_for('login'))

        application = Application.query.get_or_404(app_id)

        if application.drive.company_id != current_user.company.id:
            return redirect(url_for('company_applications'))

        if status not in ['Shortlisted', 'Selected', 'Rejected']:
            return redirect(url_for('company_applications'))

        application.status = status
        db.session.commit()

        flash('Application status updated', 'success')
        return redirect(url_for('drive_applications', drive_id=application.drive_id))



# <------------Student Routes----------->

    @app.route('/student/dashboard')
    @login_required
    def student_dashboard():
        if current_user.role != 'student':
            return redirect(url_for('login'))

        student = current_user.student

        total_applied = Application.query.filter_by(student_id=student.id).count()
        shortlisted = Application.query.filter_by(
            student_id=student.id, status='Shortlisted'
        ).count()
        selected = Application.query.filter_by(
            student_id=student.id, status='Selected'
        ).count()
        rejected = Application.query.filter_by(
            student_id=student.id, status='Rejected'
        ).count()

        recent_apps = Application.query.filter_by(
            student_id=student.id
        ).order_by(Application.applied_date.desc()).limit(4).all()

        upcoming_drives = PlacementDrive.query.filter(
            PlacementDrive.status == 'Approved',
            PlacementDrive.application_deadline >= date.today()
        ).order_by(PlacementDrive.application_deadline).limit(3).all()

        return render_template(
            'student/dashboard.html',
            student=student,
            total_applied=total_applied,
            shortlisted=shortlisted,
            selected=selected,
            rejected=rejected,
            recent_apps=recent_apps,
            upcoming_drives=upcoming_drives
        )

    @app.route('/student/drives')
    @login_required
    def student_drives():
        if current_user.role != 'student':
            return redirect(url_for('login'))

        student = current_user.student

        # All approved & open drives
        drives = PlacementDrive.query.filter(
            PlacementDrive.status == 'Approved',
            PlacementDrive.application_deadline >= date.today()
        ).all()

        # Get drive IDs already applied by this student
        applied_drive_ids = {
            app.drive_id
            for app in Application.query.filter_by(student_id=student.id).all()
        }

        return render_template(
            'student/drives.html',
            drives=drives,
            applied_drive_ids=applied_drive_ids
        )


    @app.route('/student/drives/<int:drive_id>/apply')
    @login_required
    def apply_drive(drive_id):
        if current_user.role != 'student':
            return redirect(url_for('login'))

        student = current_user.student
        drive = PlacementDrive.query.get_or_404(drive_id)

        # Only approved & open drives
        if drive.status != 'Approved':
            flash('This drive is not open for applications.', 'danger')
            return redirect(url_for('student_drives'))

        # Prevent duplicate application
        existing = Application.query.filter_by(
            student_id=student.id,
            drive_id=drive.id
        ).first()

        if existing:
            flash('You have already applied for this drive.', 'warning')
            return redirect(url_for('student_drives'))

        application = Application(
            student_id=student.id,
            drive_id=drive.id
        )

        db.session.add(application)
        db.session.commit()

        flash('Applied successfully!', 'success')
        return redirect(url_for('student_applications'))

    @app.route('/student/applications')
    @login_required
    def student_applications():
        if current_user.role != 'student':
            return redirect(url_for('login'))

        student = current_user.student
        applications = Application.query.filter_by(student_id=student.id).all()

        total_applied = len(applications)
        shortlisted = sum(1 for a in applications if a.status == 'Shortlisted')
        selected = sum(1 for a in applications if a.status == 'Selected')
        rejected = sum(1 for a in applications if a.status == 'Rejected')

        return render_template(
            'student/applications.html',
            applications=applications,
            total_applied=total_applied,
            shortlisted=shortlisted,
            selected=selected,
            rejected=rejected
        )

    @app.route('/student/profile', methods=['GET', 'POST'])
    @login_required
    def student_profile():
        if current_user.role != 'student':
            return redirect(url_for('login'))

        student = current_user.student

        if request.method == 'POST':
            branch = request.form['branch'].strip()
            cgpa = request.form['cgpa']
            phone = request.form['phone'].strip()

            if not branch or not phone:
                flash('All fields are required', 'danger')
                return redirect(url_for('student_profile'))

            try:
                cgpa = float(cgpa)
                if cgpa < 0 or cgpa > 10:
                    raise ValueError
            except ValueError:
                flash('Invalid CGPA value', 'danger')
                return redirect(url_for('student_profile'))

            student.branch = branch
            student.cgpa = cgpa
            student.phone = phone

            db.session.commit()
            flash('Profile updated successfully', 'success')

            return redirect(url_for('student_profile'))

        return render_template(
            'student/profile.html',
            student=student
        )


    @app.route('/student/history')
    @login_required
    def placement_history():
        if current_user.role != 'student':
            return redirect(url_for('login'))

        student = current_user.student

        applications = Application.query.filter_by(
            student_id=student.id
        ).order_by(Application.applied_date.desc()).all()


        return render_template(
            'student/history.html',
            applications=applications
        )



    @app.route('/')
    def home():
        return render_template('landing.html')

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
