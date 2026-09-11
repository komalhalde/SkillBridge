from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_file,
    abort
)

from functools import wraps
from io import BytesIO
from datetime import datetime
import uuid

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from models.database import get_db, init_db


# ============================================================
# APP CONFIGURATION
# ============================================================

app = Flask(__name__)
app.secret_key = "skillbridge-secret-key-2026"

init_db()


# ============================================================
# REPAIR OLD RESULT STATUS
# ============================================================

def repair_result_statuses():
    """
    Fix old result records where the stored status does not
    match the saved percentage and assessment passing percentage.
    """

    db = get_db()

    try:

        results = db.execute(
            """
            SELECT
                r.id,
                r.percentage,
                a.passing_percentage
            FROM results r
            JOIN assessments a
                ON r.assessment_id = a.id
            """
        ).fetchall()

        for result in results:

            try:
                percentage = float(
                    result["percentage"] or 0
                )
            except (
                TypeError,
                ValueError
            ):
                percentage = 0.0

            try:
                passing_percentage = float(
                    result["passing_percentage"]
                    if result["passing_percentage"] is not None
                    else 40
                )
            except (
                TypeError,
                ValueError
            ):
                passing_percentage = 40.0

            # Keep passing percentage between 0 and 100
            passing_percentage = max(
                0.0,
                min(100.0, passing_percentage)
            )

            if percentage >= passing_percentage:
                status = "passed"
            else:
                status = "failed"

            db.execute(
                """
                UPDATE results
                SET status = ?
                WHERE id = ?
                """,
                (
                    status,
                    result["id"]
                )
            )

        db.commit()

    except Exception:
        db.rollback()


# Repair old records when application starts
repair_result_statuses()


# ============================================================
# AUTHENTICATION
# ============================================================

def login_required(view):

    @wraps(view)
    def wrapped_view(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please login first.",
                "warning"
            )

            return redirect(
                url_for("login")
            )

        return view(*args, **kwargs)

    return wrapped_view


def role_required(role):

    def decorator(view):

        @wraps(view)
        def wrapped_view(*args, **kwargs):

            if "user_id" not in session:

                flash(
                    "Please login first.",
                    "warning"
                )

                return redirect(
                    url_for("login")
                )

            if session.get("role") != role:

                flash(
                    "You are not authorized to access this page.",
                    "danger"
                )

                return redirect(
                    url_for("dashboard")
                )

            return view(*args, **kwargs)

        return wrapped_view

    return decorator


# ============================================================
# HOME
# ============================================================

@app.route("/")
def home():

    return render_template(
        "home.html"
    )


# ============================================================
# LOGIN
# ============================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        if not email or not password:

            flash(
                "Email and password are required.",
                "danger"
            )

            return render_template(
                "login.html"
            )

        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        if user and user["password"] == password:

            session.clear()

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["email"] = user["email"]
            session["role"] = user["role"]

            flash(
                "Login successful!",
                "success"
            )

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid email or password.",
            "danger"
        )

    return render_template(
        "login.html"
    )


# ============================================================
# REGISTER EMPLOYEE
# ============================================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not name or not email or not password:

            flash(
                "All fields are required.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if len(password) < 6:

            flash(
                "Password must contain at least 6 characters.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        db = get_db()

        existing = db.execute(
            """
            SELECT id
            FROM users
            WHERE LOWER(email) = ?
            """,
            (email,)
        ).fetchone()

        if existing:

            flash(
                "Email already registered.",
                "danger"
            )

            return render_template(
                "register.html"
            )

        db.execute(
            """
            INSERT INTO users
            (
                name,
                email,
                password,
                role
            )
            VALUES (?, ?, ?, 'employee')
            """,
            (
                name,
                email,
                password
            )
        )

        db.commit()

        flash(
            "Registration successful. Please login.",
            "success"
        )

        return redirect(
            url_for("login")
        )

    return render_template(
        "register.html"
    )


# ============================================================
# LOGOUT
# ============================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "info"
    )

    return redirect(
        url_for("home")
    )


# ============================================================
# COMMON DASHBOARD
# ============================================================

@app.route("/dashboard")
@login_required
def dashboard():

    role = session.get("role")

    if role == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if role == "trainer":

        return redirect(
            url_for("trainer_dashboard")
        )

    if role == "employee":

        return redirect(
            url_for("employee_dashboard")
        )

    session.clear()

    return redirect(
        url_for("login")
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@app.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():

    db = get_db()

    employee_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'employee'
        """
    ).fetchone()["count"]

    trainer_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM users
        WHERE role = 'trainer'
        """
    ).fetchone()["count"]

    program_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM programs
        """
    ).fetchone()["count"]

    enrollment_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM enrollments
        """
    ).fetchone()["count"]

    result_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM results
        """
    ).fetchone()["count"]

    certificate_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM certificates
        """
    ).fetchone()["count"]

    return render_template(
        "admin/dashboard.html",
        employee_count=employee_count,
        trainer_count=trainer_count,
        program_count=program_count,
        enrollment_count=enrollment_count,
        result_count=result_count,
        certificate_count=certificate_count
    )


# ============================================================
# ADMIN - EMPLOYEES
# ============================================================

@app.route("/admin/employees")
@role_required("admin")
def admin_employees():

    db = get_db()

    employees = db.execute(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.role,
            u.created_at,
            COUNT(e.id) AS enrollment_count
        FROM users u
        LEFT JOIN enrollments e
            ON u.id = e.employee_id
        WHERE u.role = 'employee'
        GROUP BY u.id
        ORDER BY u.id DESC
        """
    ).fetchall()

    return render_template(
        "admin/employees.html",
        employees=employees
    )


# ============================================================
# ADMIN - EMPLOYEE VIEW
# ============================================================

@app.route(
    "/admin/employees/<int:employee_id>"
)
@role_required("admin")
def admin_employee_view(employee_id):

    db = get_db()

    employee = db.execute(
        """
        SELECT
            id,
            name,
            email,
            role,
            created_at
        FROM users
        WHERE id = ?
        AND role = 'employee'
        """,
        (employee_id,)
    ).fetchone()

    if not employee:

        flash(
            "Employee not found.",
            "danger"
        )

        return redirect(
            url_for("admin_employees")
        )

    enrollments = db.execute(
        """
        SELECT
            e.*,
            p.title AS program_title
        FROM enrollments e
        JOIN programs p
            ON e.program_id = p.id
        WHERE e.employee_id = ?
        ORDER BY e.enrolled_at DESC
        """,
        (employee_id,)
    ).fetchall()

    results = db.execute(
        """
        SELECT
            r.*,
            a.title AS assessment_title,
            p.title AS program_title
        FROM results r
        JOIN assessments a
            ON r.assessment_id = a.id
        JOIN programs p
            ON a.program_id = p.id
        WHERE r.employee_id = ?
        ORDER BY r.attempt_date DESC
        """,
        (employee_id,)
    ).fetchall()

    skills = db.execute(
        """
        SELECT
            s.*,
            p.title AS program_title
        FROM skills s
        LEFT JOIN programs p
            ON s.program_id = p.id
        WHERE s.employee_id = ?
        ORDER BY s.acquired_at DESC
        """,
        (employee_id,)
    ).fetchall()

    certificates = db.execute(
        """
        SELECT
            c.*,
            p.title AS program_title
        FROM certificates c
        JOIN programs p
            ON c.program_id = p.id
        WHERE c.employee_id = ?
        ORDER BY c.issued_at DESC
        """,
        (employee_id,)
    ).fetchall()

    return render_template(
        "admin/employee_view.html",
        employee=employee,
        enrollments=enrollments,
        results=results,
        skills=skills,
        certificates=certificates
    )


# ============================================================
# ADMIN - ADD EMPLOYEE
# ============================================================

@app.route(
    "/admin/employees/add",
    methods=["POST"]
)
@role_required("admin")
def admin_employee_add():

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not name or not email or not password:

        flash(
            "All employee fields are required.",
            "danger"
        )

        return redirect(
            url_for("admin_employees")
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
        """,
        (email,)
    ).fetchone()

    if existing:

        flash(
            "Email already exists.",
            "danger"
        )

        return redirect(
            url_for("admin_employees")
        )

    db.execute(
        """
        INSERT INTO users
        (
            name,
            email,
            password,
            role
        )
        VALUES (?, ?, ?, 'employee')
        """,
        (
            name,
            email,
            password
        )
    )

    db.commit()

    flash(
        "Employee added successfully.",
        "success"
    )

    return redirect(
        url_for("admin_employees")
    )


# ============================================================
# ADMIN - DELETE EMPLOYEE
# ============================================================

@app.route(
    "/admin/employees/delete/<int:employee_id>",
    methods=["POST", "GET"]
)
@role_required("admin")
def admin_employee_delete(employee_id):

    db = get_db()

    try:

        db.execute(
            """
            DELETE FROM certificates
            WHERE employee_id = ?
            """,
            (employee_id,)
        )

        db.execute(
            """
            DELETE FROM skills
            WHERE employee_id = ?
            """,
            (employee_id,)
        )

        db.execute(
            """
            DELETE FROM results
            WHERE employee_id = ?
            """,
            (employee_id,)
        )

        db.execute(
            """
            DELETE FROM enrollments
            WHERE employee_id = ?
            """,
            (employee_id,)
        )

        db.execute(
            """
            DELETE FROM users
            WHERE id = ?
            AND role = 'employee'
            """,
            (employee_id,)
        )

        db.commit()

        flash(
            "Employee deleted successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        flash(
            f"Unable to delete employee: {e}",
            "danger"
        )

    return redirect(
        url_for("admin_employees")
    )


# ============================================================
# ADMIN - TRAINERS
# ============================================================

@app.route("/admin/trainers")
@role_required("admin")
def admin_trainers():

    db = get_db()

    trainers = db.execute(
        """
        SELECT
            u.id,
            u.name,
            u.email,
            u.role,
            u.created_at,
            COUNT(p.id) AS program_count
        FROM users u
        LEFT JOIN programs p
            ON u.id = p.trainer_id
        WHERE u.role = 'trainer'
        GROUP BY u.id
        ORDER BY u.id DESC
        """
    ).fetchall()

    return render_template(
        "admin/trainers.html",
        trainers=trainers
    )


# ============================================================
# ADMIN - TRAINER VIEW
# ============================================================

@app.route(
    "/admin/trainers/<int:trainer_id>"
)
@role_required("admin")
def admin_trainer_view(trainer_id):

    db = get_db()

    trainer = db.execute(
        """
        SELECT
            id,
            name,
            email,
            role,
            created_at
        FROM users
        WHERE id = ?
        AND role = 'trainer'
        """,
        (trainer_id,)
    ).fetchone()

    if not trainer:

        flash(
            "Trainer not found.",
            "danger"
        )

        return redirect(
            url_for("admin_trainers")
        )

    programs = db.execute(
        """
        SELECT
            id,
            title,
            description,
            duration,
            skills,
            created_at
        FROM programs
        WHERE trainer_id = ?
        ORDER BY created_at DESC
        """,
        (trainer_id,)
    ).fetchall()

    assessments = db.execute(
        """
        SELECT
            a.*,
            p.title AS program_title
        FROM assessments a
        JOIN programs p
            ON a.program_id = p.id
        WHERE a.trainer_id = ?
        ORDER BY a.created_at DESC
        """,
        (trainer_id,)
    ).fetchall()

    return render_template(
        "admin/trainer_view.html",
        trainer=trainer,
        programs=programs,
        assessments=assessments
    )


# ============================================================
# ADMIN - ADD TRAINER
# ============================================================

@app.route(
    "/admin/trainers/add",
    methods=["POST"]
)
@role_required("admin")
def admin_trainer_add():

    name = request.form.get(
        "name",
        ""
    ).strip()

    email = request.form.get(
        "email",
        ""
    ).strip().lower()

    password = request.form.get(
        "password",
        ""
    )

    if not name or not email or not password:

        flash(
            "All trainer fields are required.",
            "danger"
        )

        return redirect(
            url_for("admin_trainers")
        )

    db = get_db()

    existing = db.execute(
        """
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
        """,
        (email,)
    ).fetchone()

    if existing:

        flash(
            "Email already exists.",
            "danger"
        )

        return redirect(
            url_for("admin_trainers")
        )

    db.execute(
        """
        INSERT INTO users
        (
            name,
            email,
            password,
            role
        )
        VALUES (?, ?, ?, 'trainer')
        """,
        (
            name,
            email,
            password
        )
    )

    db.commit()

    flash(
        "Trainer added successfully.",
        "success"
    )

    return redirect(
        url_for("admin_trainers")
    )


# ============================================================
# ADMIN - DELETE TRAINER
# ============================================================

@app.route(
    "/admin/trainers/delete/<int:trainer_id>",
    methods=["POST", "GET"]
)
@role_required("admin")
def admin_trainer_delete(trainer_id):

    db = get_db()

    try:

        db.execute(
            """
            UPDATE programs
            SET trainer_id = NULL
            WHERE trainer_id = ?
            """,
            (trainer_id,)
        )

        db.execute(
            """
            DELETE FROM users
            WHERE id = ?
            AND role = 'trainer'
            """,
            (trainer_id,)
        )

        db.commit()

        flash(
            "Trainer deleted successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        flash(
            f"Unable to delete trainer: {e}",
            "danger"
        )

    return redirect(
        url_for("admin_trainers")
    )


# ============================================================
# ADMIN - PROGRAMS
# ============================================================

@app.route("/admin/programs")
@role_required("admin")
def admin_programs():

    db = get_db()

    programs = db.execute(
        """
        SELECT
            p.*,
            u.name AS trainer_name,
            COUNT(e.id) AS enrollment_count
        FROM programs p
        LEFT JOIN users u
            ON p.trainer_id = u.id
        LEFT JOIN enrollments e
            ON p.id = e.program_id
        GROUP BY p.id
        ORDER BY p.id DESC
        """
    ).fetchall()

    trainers = db.execute(
        """
        SELECT
            id,
            name
        FROM users
        WHERE role = 'trainer'
        ORDER BY name
        """
    ).fetchall()

    return render_template(
        "admin/programs.html",
        programs=programs,
        trainers=trainers
    )


# ============================================================
# ADMIN - CREATE PROGRAM
# ============================================================

@app.route(
    "/admin/programs/create",
    methods=["GET", "POST"]
)
@role_required("admin")
def admin_program_create():

    db = get_db()

    trainers = db.execute(
        """
        SELECT
            id,
            name
        FROM users
        WHERE role = 'trainer'
        ORDER BY name
        """
    ).fetchall()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        skills = request.form.get(
            "skills",
            ""
        ).strip()

        trainer_id = request.form.get(
            "trainer_id"
        )

        if trainer_id == "":
            trainer_id = None

        if not title:

            flash(
                "Program title is required.",
                "danger"
            )

            return render_template(
                "admin/program_form.html",
                program=None,
                trainers=trainers
            )

        db.execute(
            """
            INSERT INTO programs
            (
                title,
                description,
                duration,
                skills,
                trainer_id
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                title,
                description,
                duration,
                skills,
                trainer_id
            )
        )

        db.commit()

        flash(
            "Training program created successfully.",
            "success"
        )

        return redirect(
            url_for("admin_programs")
        )

    return render_template(
        "admin/program_form.html",
        program=None,
        trainers=trainers
    )


# ============================================================
# ADMIN - EDIT PROGRAM
# ============================================================

@app.route(
    "/admin/programs/edit/<int:program_id>",
    methods=["GET", "POST"]
)
@role_required("admin")
def admin_program_edit(program_id):

    db = get_db()

    program = db.execute(
        """
        SELECT *
        FROM programs
        WHERE id = ?
        """,
        (program_id,)
    ).fetchone()

    if not program:
        abort(404)

    trainers = db.execute(
        """
        SELECT
            id,
            name
        FROM users
        WHERE role = 'trainer'
        ORDER BY name
        """
    ).fetchall()

    if request.method == "POST":

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        duration = request.form.get(
            "duration",
            ""
        ).strip()

        skills = request.form.get(
            "skills",
            ""
        ).strip()

        trainer_id = request.form.get(
            "trainer_id"
        )

        if trainer_id == "":
            trainer_id = None

        if not title:

            flash(
                "Program title is required.",
                "danger"
            )

            return render_template(
                "admin/program_form.html",
                program=program,
                trainers=trainers
            )

        db.execute(
            """
            UPDATE programs
            SET
                title = ?,
                description = ?,
                duration = ?,
                skills = ?,
                trainer_id = ?
            WHERE id = ?
            """,
            (
                title,
                description,
                duration,
                skills,
                trainer_id,
                program_id
            )
        )

        db.commit()

        flash(
            "Training program updated successfully.",
            "success"
        )

        return redirect(
            url_for("admin_programs")
        )

    return render_template(
        "admin/program_form.html",
        program=program,
        trainers=trainers
    )


# ============================================================
# ADMIN - DELETE PROGRAM
# ============================================================

@app.route(
    "/admin/programs/delete/<int:program_id>",
    methods=["POST", "GET"]
)
@role_required("admin")
def admin_program_delete(program_id):

    db = get_db()

    try:

        assessments = db.execute(
            """
            SELECT id
            FROM assessments
            WHERE program_id = ?
            """,
            (program_id,)
        ).fetchall()

        for assessment in assessments:

            db.execute(
                """
                DELETE FROM questions
                WHERE assessment_id = ?
                """,
                (assessment["id"],)
            )

            db.execute(
                """
                DELETE FROM results
                WHERE assessment_id = ?
                """,
                (assessment["id"],)
            )

        db.execute(
            """
            DELETE FROM assessments
            WHERE program_id = ?
            """,
            (program_id,)
        )

        db.execute(
            """
            DELETE FROM certificates
            WHERE program_id = ?
            """,
            (program_id,)
        )

        db.execute(
            """
            DELETE FROM skills
            WHERE program_id = ?
            """,
            (program_id,)
        )

        db.execute(
            """
            DELETE FROM enrollments
            WHERE program_id = ?
            """,
            (program_id,)
        )

        db.execute(
            """
            DELETE FROM programs
            WHERE id = ?
            """,
            (program_id,)
        )

        db.commit()

        flash(
            "Training program deleted successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        flash(
            f"Unable to delete program: {e}",
            "danger"
        )

    return redirect(
        url_for("admin_programs")
    )


# ============================================================
# ADMIN - PROGRAM VIEW
# ============================================================

@app.route(
    "/admin/programs/<int:program_id>"
)
@role_required("admin")
def admin_program_view(program_id):

    db = get_db()

    program = db.execute(
        """
        SELECT
            p.*,
            u.name AS trainer_name
        FROM programs p
        LEFT JOIN users u
            ON p.trainer_id = u.id
        WHERE p.id = ?
        """,
        (program_id,)
    ).fetchone()

    if not program:
        abort(404)

    enrollments = db.execute(
        """
        SELECT
            e.*,
            u.name AS employee_name,
            u.email AS employee_email
        FROM enrollments e
        JOIN users u
            ON e.employee_id = u.id
        WHERE e.program_id = ?
        ORDER BY e.enrolled_at DESC
        """,
        (program_id,)
    ).fetchall()

    return render_template(
        "admin/program_view.html",
        program=program,
        enrollments=enrollments
    )


# ============================================================
# ADMIN - ENROLLMENTS
# ============================================================

@app.route("/admin/enrollments")
@role_required("admin")
def admin_enrollments():

    db = get_db()

    enrollments = db.execute(
        """
        SELECT
            e.*,
            u.name AS employee_name,
            u.email AS employee_email,
            p.title AS program_title,
            t.name AS trainer_name
        FROM enrollments e
        JOIN users u
            ON e.employee_id = u.id
        JOIN programs p
            ON e.program_id = p.id
        LEFT JOIN users t
            ON p.trainer_id = t.id
        ORDER BY e.enrolled_at DESC
        """
    ).fetchall()

    return render_template(
        "admin/enrollments.html",
        enrollments=enrollments
    )


# ============================================================
# ADMIN - ENROLLMENT VIEW
# ============================================================

@app.route(
    "/admin/enrollments/<int:enrollment_id>"
)
@role_required("admin")
def admin_enrollment_view(enrollment_id):

    db = get_db()

    enrollment = db.execute(
        """
        SELECT
            e.id,
            e.employee_id,
            e.program_id,
            e.progress,
            e.status,
            e.enrolled_at,

            u.name AS employee_name,
            u.email AS employee_email,

            p.title AS program_title,
            p.description AS program_description,
            p.duration,
            p.skills,

            t.name AS trainer_name

        FROM enrollments e

        JOIN users u
            ON e.employee_id = u.id

        JOIN programs p
            ON e.program_id = p.id

        LEFT JOIN users t
            ON p.trainer_id = t.id

        WHERE e.id = ?
        """,
        (enrollment_id,)
    ).fetchone()

    if not enrollment:

        flash(
            "Enrollment not found.",
            "danger"
        )

        return redirect(
            url_for("admin_enrollments")
        )

    results = db.execute(
        """
        SELECT
            r.id,
            r.score,
            r.total_marks,
            r.percentage,
            r.status,
            r.attempt_date,

            a.id AS assessment_id,
            a.title AS assessment_title

        FROM results r

        JOIN assessments a
            ON r.assessment_id = a.id

        WHERE r.employee_id = ?
        AND a.program_id = ?

        ORDER BY r.attempt_date DESC
        """,
        (
            enrollment["employee_id"],
            enrollment["program_id"]
        )
    ).fetchall()

    certificates = db.execute(
        """
        SELECT
            c.id,
            c.certificate_number,
            c.issued_at
        FROM certificates c
        WHERE c.employee_id = ?
        AND c.program_id = ?
        ORDER BY c.issued_at DESC
        """,
        (
            enrollment["employee_id"],
            enrollment["program_id"]
        )
    ).fetchall()

    return render_template(
        "admin/enrollment_view.html",
        enrollment=enrollment,
        results=results,
        certificates=certificates
    )


# ============================================================
# ADMIN - RESULTS
# ============================================================

@app.route("/admin/results")
@role_required("admin")
def admin_results():

    db = get_db()

    results = db.execute(
        """
        SELECT
            r.*,
            u.name AS employee_name,
            u.email AS employee_email,
            a.title AS assessment_title,
            p.title AS program_title
        FROM results r
        JOIN users u
            ON r.employee_id = u.id
        JOIN assessments a
            ON r.assessment_id = a.id
        JOIN programs p
            ON a.program_id = p.id
        ORDER BY r.attempt_date DESC
        """
    ).fetchall()

    return render_template(
        "admin/results.html",
        results=results
    )


# ============================================================
# ADMIN - CERTIFICATES
# ============================================================

@app.route("/admin/certificates")
@role_required("admin")
def admin_certificates():

    db = get_db()

    certificates = db.execute(
        """
        SELECT
            c.*,
            u.name AS employee_name,
            u.email AS employee_email,
            p.title AS program_title
        FROM certificates c
        JOIN users u
            ON c.employee_id = u.id
        JOIN programs p
            ON c.program_id = p.id
        ORDER BY c.issued_at DESC
        """
    ).fetchall()

    return render_template(
        "admin/certificates.html",
        certificates=certificates
    )


# ============================================================
# TRAINER - DASHBOARD
# ============================================================

@app.route("/trainer/dashboard")
@role_required("trainer")
def trainer_dashboard():

    db = get_db()

    trainer_id = session["user_id"]

    programs = db.execute(
        """
        SELECT
            id,
            title,
            description,
            duration,
            skills
        FROM programs
        WHERE trainer_id = ?
        ORDER BY id DESC
        """,
        (trainer_id,)
    ).fetchall()

    program_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM programs
        WHERE trainer_id = ?
        """,
        (trainer_id,)
    ).fetchone()["count"]

    assessment_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM assessments
        WHERE trainer_id = ?
        """,
        (trainer_id,)
    ).fetchone()["count"]

    result_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM results r
        JOIN assessments a
            ON r.assessment_id = a.id
        WHERE a.trainer_id = ?
        """,
        (trainer_id,)
    ).fetchone()["count"]

    return render_template(
        "trainer/dashboard.html",
        programs=programs,
        program_count=program_count,
        assessment_count=assessment_count,
        result_count=result_count
    )


# ============================================================
# TRAINER - ASSESSMENTS
# ============================================================
# ============================================================
# TRAINER - ASSESSMENTS
# ============================================================

@app.route("/trainer/assessments")
@role_required("trainer")
def trainer_assessments():

    db = get_db()

    trainer_id = session["user_id"]

    # Get trainer's assessments
    assessments = db.execute(
        """
        SELECT
            a.*,
            p.title AS program_title,
            COUNT(q.id) AS question_count
        FROM assessments a
        JOIN programs p
            ON a.program_id = p.id
        LEFT JOIN questions q
            ON a.id = q.assessment_id
        WHERE a.trainer_id = ?
        GROUP BY a.id
        ORDER BY a.id DESC
        """,
        (trainer_id,)
    ).fetchall()

    # Get trainer's programs
    programs = db.execute(
        """
        SELECT
            id,
            title
        FROM programs
        WHERE trainer_id = ?
        ORDER BY title
        """,
        (trainer_id,)
    ).fetchall()

    return render_template(
        "trainer/assessments.html",
        assessments=assessments,
        programs=programs
    )
# ============================================================
# TRAINER - CREATE ASSESSMENT
# ============================================================

@app.route(
    "/trainer/assessments/create",
    methods=["GET", "POST"]
)
@role_required("trainer")
def trainer_assessment_create():

    db = get_db()

    trainer_id = session["user_id"]

    programs = db.execute(
        """
        SELECT
            id,
            title
        FROM programs
        WHERE trainer_id = ?
        ORDER BY title
        """,
        (trainer_id,)
    ).fetchall()

    if request.method == "POST":

        program_id = request.form.get(
            "program_id"
        )

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        passing_percentage = request.form.get(
            "passing_percentage",
            "40"
        )

        try:

            program_id = int(program_id)

            passing_percentage = float(
                passing_percentage
            )

        except (
            TypeError,
            ValueError
        ):

            flash(
                "Invalid assessment data.",
                "danger"
            )

            return render_template(
                "trainer/assessment_form.html",
                assessment=None,
                programs=programs
            )

        passing_percentage = max(
            0.0,
            min(
                100.0,
                passing_percentage
            )
        )

        if not title:

            flash(
                "Assessment title is required.",
                "danger"
            )

            return render_template(
                "trainer/assessment_form.html",
                assessment=None,
                programs=programs
            )

        program = db.execute(
            """
            SELECT id
            FROM programs
            WHERE id = ?
            AND trainer_id = ?
            """,
            (
                program_id,
                trainer_id
            )
        ).fetchone()

        if not program:

            flash(
                "Invalid training program.",
                "danger"
            )

            return redirect(
                url_for("trainer_assessments")
            )

        db.execute(
            """
            INSERT INTO assessments
            (
                program_id,
                trainer_id,
                title,
                description,
                passing_percentage
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                program_id,
                trainer_id,
                title,
                description,
                passing_percentage
            )
        )

        db.commit()

        flash(
            "Assessment created successfully.",
            "success"
        )

        return redirect(
            url_for("trainer_assessments")
        )

    return render_template(
        "trainer/assessment_form.html",
        assessment=None,
        programs=programs
    )


# ============================================================
# TRAINER - EDIT ASSESSMENT
# ============================================================

@app.route(
    "/trainer/assessments/edit/<int:assessment_id>",
    methods=["GET", "POST"]
)
@role_required("trainer")
def trainer_assessment_edit(assessment_id):

    db = get_db()

    trainer_id = session["user_id"]

    assessment = db.execute(
        """
        SELECT *
        FROM assessments
        WHERE id = ?
        AND trainer_id = ?
        """,
        (
            assessment_id,
            trainer_id
        )
    ).fetchone()

    if not assessment:
        abort(404)

    programs = db.execute(
        """
        SELECT
            id,
            title
        FROM programs
        WHERE trainer_id = ?
        ORDER BY title
        """,
        (trainer_id,)
    ).fetchall()

    if request.method == "POST":

        program_id = request.form.get(
            "program_id"
        )

        title = request.form.get(
            "title",
            ""
        ).strip()

        description = request.form.get(
            "description",
            ""
        ).strip()

        passing_percentage = request.form.get(
            "passing_percentage",
            "40"
        )

        try:

            program_id = int(program_id)

            passing_percentage = float(
                passing_percentage
            )

        except (
            TypeError,
            ValueError
        ):

            flash(
                "Invalid assessment data.",
                "danger"
            )

            return redirect(
                url_for("trainer_assessments")
            )

        passing_percentage = max(
            0.0,
            min(
                100.0,
                passing_percentage
            )
        )

        if not title:

            flash(
                "Assessment title is required.",
                "danger"
            )

            return render_template(
                "trainer/assessment_form.html",
                assessment=assessment,
                programs=programs
            )

        program = db.execute(
            """
            SELECT id
            FROM programs
            WHERE id = ?
            AND trainer_id = ?
            """,
            (
                program_id,
                trainer_id
            )
        ).fetchone()

        if not program:

            flash(
                "Invalid training program.",
                "danger"
            )

            return redirect(
                url_for("trainer_assessments")
            )

        db.execute(
            """
            UPDATE assessments
            SET
                program_id = ?,
                title = ?,
                description = ?,
                passing_percentage = ?
            WHERE id = ?
            AND trainer_id = ?
            """,
            (
                program_id,
                title,
                description,
                passing_percentage,
                assessment_id,
                trainer_id
            )
        )

        db.commit()

        # Recalculate old results for this assessment
        repair_result_statuses()

        flash(
            "Assessment updated successfully.",
            "success"
        )

        return redirect(
            url_for("trainer_assessments")
        )

    return render_template(
        "trainer/assessment_form.html",
        assessment=assessment,
        programs=programs
    )


# ============================================================
# TRAINER - DELETE ASSESSMENT
# ============================================================

@app.route(
    "/trainer/assessments/delete/<int:assessment_id>",
    methods=["POST", "GET"]
)
@role_required("trainer")
def trainer_assessment_delete(assessment_id):

    db = get_db()

    trainer_id = session["user_id"]

    assessment = db.execute(
        """
        SELECT id
        FROM assessments
        WHERE id = ?
        AND trainer_id = ?
        """,
        (
            assessment_id,
            trainer_id
        )
    ).fetchone()

    if not assessment:

        flash(
            "Assessment not found.",
            "danger"
        )

        return redirect(
            url_for("trainer_assessments")
        )

    try:

        db.execute(
            """
            DELETE FROM questions
            WHERE assessment_id = ?
            """,
            (assessment_id,)
        )

        db.execute(
            """
            DELETE FROM results
            WHERE assessment_id = ?
            """,
            (assessment_id,)
        )

        db.execute(
            """
            DELETE FROM assessments
            WHERE id = ?
            AND trainer_id = ?
            """,
            (
                assessment_id,
                trainer_id
            )
        )

        db.commit()

        flash(
            "Assessment deleted successfully.",
            "success"
        )

    except Exception as e:

        db.rollback()

        flash(
            f"Unable to delete assessment: {e}",
            "danger"
        )

    return redirect(
        url_for("trainer_assessments")
    )


# ============================================================
# TRAINER - QUESTIONS
# ============================================================

@app.route(
    "/trainer/assessments/<int:assessment_id>/questions"
)
@role_required("trainer")
def trainer_questions(assessment_id):

    db = get_db()

    trainer_id = session["user_id"]

    assessment = db.execute(
        """
        SELECT
            a.*,
            p.title AS program_title
        FROM assessments a
        JOIN programs p
            ON a.program_id = p.id
        WHERE a.id = ?
        AND a.trainer_id = ?
        """,
        (
            assessment_id,
            trainer_id
        )
    ).fetchone()

    if not assessment:
        abort(404)

    questions = db.execute(
        """
        SELECT *
        FROM questions
        WHERE assessment_id = ?
        ORDER BY id
        """,
        (assessment_id,)
    ).fetchall()

    return render_template(
        "trainer/questions.html",
        assessment=assessment,
        questions=questions
    )


# ============================================================
# TRAINER - ADD QUESTION
# ============================================================

@app.route(
    "/trainer/assessments/<int:assessment_id>/questions/add",
    methods=["POST"]
)
@role_required("trainer")
def trainer_question_add(assessment_id):

    db = get_db()

    trainer_id = session["user_id"]

    assessment = db.execute(
        """
        SELECT id
        FROM assessments
        WHERE id = ?
        AND trainer_id = ?
        """,
        (
            assessment_id,
            trainer_id
        )
    ).fetchone()

    if not assessment:
        abort(404)

    question_text = request.form.get(
        "question_text",
        ""
    ).strip()

    option_a = request.form.get(
        "option_a",
        ""
    ).strip()

    option_b = request.form.get(
        "option_b",
        ""
    ).strip()

    option_c = request.form.get(
        "option_c",
        ""
    ).strip()

    option_d = request.form.get(
        "option_d",
        ""
    ).strip()

    correct_answer = request.form.get(
        "correct_answer",
        ""
    ).strip().upper()

    marks = request.form.get(
        "marks",
        "1"
    )

    try:

        marks = float(marks)

    except (
        TypeError,
        ValueError
    ):

        marks = 1.0

    if marks <= 0:
        marks = 1.0

    if not question_text:

        flash(
            "Question text is required.",
            "danger"
        )

        return redirect(
            url_for(
                "trainer_questions",
                assessment_id=assessment_id
            )
        )

    if correct_answer not in [
        "A",
        "B",
        "C",
        "D"
    ]:

        flash(
            "Correct answer must be A, B, C or D.",
            "danger"
        )

        return redirect(
            url_for(
                "trainer_questions",
                assessment_id=assessment_id
            )
        )

    db.execute(
        """
        INSERT INTO questions
        (
            assessment_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            marks
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            assessment_id,
            question_text,
            option_a,
            option_b,
            option_c,
            option_d,
            correct_answer,
            marks
        )
    )

    db.commit()

    flash(
        "Question added successfully.",
        "success"
    )

    return redirect(
        url_for(
            "trainer_questions",
            assessment_id=assessment_id
        )
    )


# ============================================================
# TRAINER - EDIT QUESTION
# ============================================================

@app.route(
    "/trainer/questions/<int:question_id>/edit",
    methods=["GET", "POST"]
)
@role_required("trainer")
def trainer_question_edit(question_id):

    db = get_db()

    trainer_id = session["user_id"]

    question = db.execute(
        """
        SELECT
            q.*,
            a.title AS assessment_title,
            a.id AS assessment_id
        FROM questions q
        JOIN assessments a
            ON q.assessment_id = a.id
        WHERE q.id = ?
        AND a.trainer_id = ?
        """,
        (
            question_id,
            trainer_id
        )
    ).fetchone()

    if not question:
        abort(404)

    assessment_id = question["assessment_id"]

    if request.method == "POST":

        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        option_a = request.form.get(
            "option_a",
            ""
        ).strip()

        option_b = request.form.get(
            "option_b",
            ""
        ).strip()

        option_c = request.form.get(
            "option_c",
            ""
        ).strip()

        option_d = request.form.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.form.get(
            "correct_answer",
            ""
        ).strip().upper()

        marks = request.form.get(
            "marks",
            "1"
        )

        try:

            marks = float(marks)

        except (
            TypeError,
            ValueError
        ):

            marks = 1.0

        if marks <= 0:
            marks = 1.0

        if not question_text:

            flash(
                "Question text is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "trainer_questions",
                    assessment_id=assessment_id
                )
            )

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:

            flash(
                "Correct answer must be A, B, C or D.",
                "danger"
            )

            return redirect(
                url_for(
                    "trainer_questions",
                    assessment_id=assessment_id
                )
            )

        db.execute(
            """
            UPDATE questions
            SET
                question_text = ?,
                option_a = ?,
                option_b = ?,
                option_c = ?,
                option_d = ?,
                correct_answer = ?,
                marks = ?
            WHERE id = ?
            """,
            (
                question_text,
                option_a,
                option_b,
                option_c,
                option_d,
                correct_answer,
                marks,
                question_id
            )
        )

        db.commit()

        flash(
            "Question updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "trainer_questions",
                assessment_id=assessment_id
            )
        )

    return render_template(
        "trainer/questions.html",
        assessment=question,
        questions=[question],
        edit_question=question
    )


# ============================================================
# TRAINER - DELETE QUESTION
# ============================================================

@app.route(
    "/trainer/questions/<int:question_id>/delete",
    methods=["POST", "GET"]
)
@role_required("trainer")
def trainer_question_delete(question_id):

    db = get_db()

    trainer_id = session["user_id"]

    question = db.execute(
        """
        SELECT
            q.id,
            q.assessment_id
        FROM questions q
        JOIN assessments a
            ON q.assessment_id = a.id
        WHERE q.id = ?
        AND a.trainer_id = ?
        """,
        (
            question_id,
            trainer_id
        )
    ).fetchone()

    if not question:
        abort(404)

    assessment_id = question["assessment_id"]

    db.execute(
        """
        DELETE FROM questions
        WHERE id = ?
        """,
        (question_id,)
    )

    db.commit()

    flash(
        "Question deleted successfully.",
        "success"
    )

    return redirect(
        url_for(
            "trainer_questions",
            assessment_id=assessment_id
        )
    )


# ============================================================
# TRAINER - RESULTS
# ============================================================

@app.route("/trainer/results")
@role_required("trainer")
def trainer_results():

    # Repair any old incorrect results before displaying
    repair_result_statuses()

    db = get_db()

    trainer_id = session["user_id"]

    results = db.execute(
        """
        SELECT
            r.*,
            u.name AS employee_name,
            u.email AS employee_email,
            a.title AS assessment_title,
            p.title AS program_title
        FROM results r
        JOIN users u
            ON r.employee_id = u.id
        JOIN assessments a
            ON r.assessment_id = a.id
        JOIN programs p
            ON a.program_id = p.id
        WHERE a.trainer_id = ?
        ORDER BY r.attempt_date DESC
        """,
        (trainer_id,)
    ).fetchall()

    return render_template(
        "trainer/results.html",
        results=results
    )


# ============================================================
# EMPLOYEE DASHBOARD
# ============================================================

@app.route("/employee/dashboard")
@role_required("employee")
def employee_dashboard():

    db = get_db()

    employee_id = session["user_id"]

    available_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM programs
        """
    ).fetchone()["count"]

    enrolled_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM enrollments
        WHERE employee_id = ?
        """,
        (employee_id,)
    ).fetchone()["count"]

    skill_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM skills
        WHERE employee_id = ?
        """,
        (employee_id,)
    ).fetchone()["count"]

    certificate_count = db.execute(
        """
        SELECT COUNT(*) AS count
        FROM certificates
        WHERE employee_id = ?
        """,
        (employee_id,)
    ).fetchone()["count"]

    assessment_count = db.execute(
        """
        SELECT COUNT(DISTINCT a.id) AS count
        FROM assessments a
        JOIN enrollments e
            ON a.program_id = e.program_id
        WHERE e.employee_id = ?
        """,
        (employee_id,)
    ).fetchone()["count"]

    enrollments = db.execute(
        """
        SELECT
            e.id,
            e.progress,
            e.status,
            p.id AS program_id,
            p.title
        FROM enrollments e
        JOIN programs p
            ON e.program_id = p.id
        WHERE e.employee_id = ?
        ORDER BY e.id DESC
        """,
        (employee_id,)
    ).fetchall()

    return render_template(
        "employee/dashboard.html",
        available_count=available_count,
        enrolled_count=enrolled_count,
        skill_count=skill_count,
        certificate_count=certificate_count,
        assessment_count=assessment_count,
        enrollments=enrollments
    )


# ============================================================
# EMPLOYEE - ALL COURSES
# ============================================================

@app.route("/employee/courses")
@role_required("employee")
def employee_courses():

    db = get_db()

    employee_id = session["user_id"]

    programs = db.execute(
        """
        SELECT
            p.*,
            u.name AS trainer_name,
            e.id AS enrollment_id,
            e.progress,
            e.status
        FROM programs p
        LEFT JOIN users u
            ON p.trainer_id = u.id
        LEFT JOIN enrollments e
            ON p.id = e.program_id
            AND e.employee_id = ?
        ORDER BY p.id DESC
        """,
        (employee_id,)
    ).fetchall()

    return render_template(
        "employee/courses.html",
        programs=programs
    )


# ============================================================
# EMPLOYEE - ENROLL
# ============================================================

@app.route(
    "/employee/enroll/<int:program_id>",
    methods=["POST"]
)
@role_required("employee")
def employee_enroll(program_id):

    db = get_db()

    employee_id = session["user_id"]

    program = db.execute(
        """
        SELECT
            id,
            title
        FROM programs
        WHERE id = ?
        """,
        (program_id,)
    ).fetchone()

    if not program:

        flash(
            "Training program not found.",
            "danger"
        )

        return redirect(
            url_for("employee_courses")
        )

    existing = db.execute(
        """
        SELECT id
        FROM enrollments
        WHERE employee_id = ?
        AND program_id = ?
        """,
        (
            employee_id,
            program_id
        )
    ).fetchone()

    if existing:

        flash(
            "You are already enrolled in this program.",
            "info"
        )

        return redirect(
            url_for("employee_my_courses")
        )

    try:

        db.execute(
            """
            INSERT INTO enrollments
            (
                employee_id,
                program_id,
                progress,
                status
            )
            VALUES (?, ?, 0, 'enrolled')
            """,
            (
                employee_id,
                program_id
            )
        )

        db.commit()

    except Exception as e:

        db.rollback()

        flash(
            f"Unable to enroll: {e}",
            "danger"
        )

        return redirect(
            url_for("employee_courses")
        )

    flash(
        f"Successfully enrolled in {program['title']}.",
        "success"
    )

    return redirect(
        url_for("employee_my_courses")
    )


# ============================================================
# EMPLOYEE - MY COURSES
# ============================================================

@app.route("/employee/my-courses")
@role_required("employee")
def employee_my_courses():

    db = get_db()

    employee_id = session["user_id"]

    courses = db.execute(
        """
        SELECT
            e.*,
            p.id AS program_id,
            p.title,
            p.description,
            p.duration,
            p.skills,
            u.name AS trainer_name
        FROM enrollments e
        JOIN programs p
            ON e.program_id = p.id
        LEFT JOIN users u
            ON p.trainer_id = u.id
        WHERE e.employee_id = ?
        ORDER BY e.enrolled_at DESC
        """,
        (employee_id,)
    ).fetchall()

    assessments = db.execute(
        """
        SELECT
            a.id,
            a.program_id,
            a.title,
            a.description,
            a.passing_percentage,

            p.title AS program_title,

            e.id AS enrollment_id,
            e.progress,
            e.status AS enrollment_status,

            (
                SELECT COUNT(*)
                FROM questions q
                WHERE q.assessment_id = a.id
            ) AS question_count,

            (
                SELECT r.id
                FROM results r
                WHERE r.assessment_id = a.id
                AND r.employee_id = ?
                LIMIT 1
            ) AS result_id,

            (
                SELECT r.status
                FROM results r
                WHERE r.assessment_id = a.id
                AND r.employee_id = ?
                LIMIT 1
            ) AS result_status,

            (
                SELECT r.percentage
                FROM results r
                WHERE r.assessment_id = a.id
                AND r.employee_id = ?
                LIMIT 1
            ) AS result_percentage

        FROM assessments a

        JOIN programs p
            ON a.program_id = p.id

        JOIN enrollments e
            ON e.program_id = p.id

        WHERE e.employee_id = ?

        ORDER BY a.id DESC
        """,
        (
            employee_id,
            employee_id,
            employee_id,
            employee_id
        )
    ).fetchall()

    certificates = db.execute(
        """
        SELECT
            c.*,
            p.title AS program_title,
            r.percentage
        FROM certificates c
        JOIN programs p
            ON c.program_id = p.id
        LEFT JOIN results r
            ON c.result_id = r.id
        WHERE c.employee_id = ?
        ORDER BY c.issued_at DESC
        """,
        (employee_id,)
    ).fetchall()

    return render_template(
        "employee/my_courses.html",
        courses=courses,
        enrollments=courses,
        assessments=assessments,
        certificates=certificates
    )


# ============================================================
# EMPLOYEE - UPDATE PROGRESS
# ============================================================

@app.route(
    "/employee/progress/<int:enrollment_id>",
    methods=["GET", "POST"]
)
@role_required("employee")
def employee_update_progress(enrollment_id):

    db = get_db()

    employee_id = session["user_id"]

    enrollment = db.execute(
        """
        SELECT
            e.*,
            p.title AS program_title
        FROM enrollments e
        JOIN programs p
            ON e.program_id = p.id
        WHERE e.id = ?
        AND e.employee_id = ?
        """,
        (
            enrollment_id,
            employee_id
        )
    ).fetchone()

    if not enrollment:
        abort(404)

    if request.method == "POST":

        progress = request.form.get(
            "progress",
            "0"
        )

        try:

            progress = int(progress)

        except (
            TypeError,
            ValueError
        ):

            progress = 0

        progress = max(
            0,
            min(100, progress)
        )

        status = (
            "completed"
            if progress == 100
            else "in_progress"
        )

        db.execute(
            """
            UPDATE enrollments
            SET
                progress = ?,
                status = ?
            WHERE id = ?
            AND employee_id = ?
            """,
            (
                progress,
                status,
                enrollment_id,
                employee_id
            )
        )

        db.commit()

        flash(
            "Course progress updated successfully.",
            "success"
        )

        return redirect(
            url_for("employee_my_courses")
        )

    return render_template(
        "employee/update_progress.html",
        enrollment=enrollment
    )


# ============================================================
# EMPLOYEE - TAKE ASSESSMENT
# ============================================================

@app.route(
    "/employee/assessment/<int:assessment_id>",
    methods=["GET", "POST"]
)
@role_required("employee")
def employee_assessment(assessment_id):

    db = get_db()

    employee_id = session["user_id"]

    assessment = db.execute(
        """
        SELECT
            a.*,
            p.title AS program_title
        FROM assessments a
        JOIN programs p
            ON a.program_id = p.id
        WHERE a.id = ?
        """,
        (assessment_id,)
    ).fetchone()

    if not assessment:
        abort(404)

    enrollment = db.execute(
        """
        SELECT *
        FROM enrollments
        WHERE employee_id = ?
        AND program_id = ?
        """,
        (
            employee_id,
            assessment["program_id"]
        )
    ).fetchone()

    if not enrollment:

        flash(
            "Please enroll in this program first.",
            "warning"
        )

        return redirect(
            url_for("employee_courses")
        )

    questions = db.execute(
        """
        SELECT *
        FROM questions
        WHERE assessment_id = ?
        ORDER BY id
        """,
        (assessment_id,)
    ).fetchall()

    if not questions:

        flash(
            "This assessment has no questions yet.",
            "info"
        )

        return redirect(
            url_for("employee_my_courses")
        )

    # --------------------------------------------------------
    # SUBMIT ASSESSMENT
    # --------------------------------------------------------

    if request.method == "POST":

        score = 0.0
        total_marks = 0.0

        # Calculate score
        for question in questions:

            try:

                marks = float(
                    question["marks"] or 1
                )

            except (
                TypeError,
                ValueError
            ):

                marks = 1.0

            if marks <= 0:
                marks = 1.0

            total_marks += marks

            answer = (
                request.form.get(
                    f"question_{question['id']}",
                    ""
                )
                or ""
            ).strip().upper()

            correct_answer = (
                question["correct_answer"]
                or ""
            ).strip().upper()

            if answer == correct_answer:

                score += marks

        # Calculate percentage
        if total_marks > 0:

            percentage = (
                score /
                total_marks
            ) * 100

        else:

            percentage = 0.0

        percentage = round(
            percentage,
            2
        )

        # ----------------------------------------------------
        # PASSING PERCENTAGE
        # ----------------------------------------------------

        try:

            passing_percentage = float(
                assessment["passing_percentage"]
                if assessment["passing_percentage"] is not None
                else 40
            )

        except (
            TypeError,
            ValueError
        ):

            passing_percentage = 40.0

        # Keep passing score in valid range
        passing_percentage = max(
            0.0,
            min(
                100.0,
                passing_percentage
            )
        )

        # ----------------------------------------------------
        # PASS / FAIL
        # ----------------------------------------------------

        if percentage >= passing_percentage:

            status = "passed"

        else:

            status = "failed"

        # ----------------------------------------------------
        # SAVE / UPDATE RESULT
        # ----------------------------------------------------

        existing_result = db.execute(
            """
            SELECT id
            FROM results
            WHERE assessment_id = ?
            AND employee_id = ?
            """,
            (
                assessment_id,
                employee_id
            )
        ).fetchone()

        if existing_result:

            db.execute(
                """
                UPDATE results
                SET
                    score = ?,
                    total_marks = ?,
                    percentage = ?,
                    status = ?,
                    attempt_date = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    score,
                    total_marks,
                    percentage,
                    status,
                    existing_result["id"]
                )
            )

            result_id = existing_result["id"]

        else:

            cursor = db.execute(
                """
                INSERT INTO results
                (
                    assessment_id,
                    employee_id,
                    score,
                    total_marks,
                    percentage,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    employee_id,
                    score,
                    total_marks,
                    percentage,
                    status
                )
            )

            result_id = cursor.lastrowid

        # ====================================================
        # PASSED
        # ====================================================

        if status == "passed":

            # ------------------------------------------------
            # COMPLETE ENROLLMENT
            # ------------------------------------------------

            db.execute(
                """
                UPDATE enrollments
                SET
                    progress = 100,
                    status = 'completed'
                WHERE employee_id = ?
                AND program_id = ?
                """,
                (
                    employee_id,
                    assessment["program_id"]
                )
            )

            # ------------------------------------------------
            # ADD SKILLS
            # ------------------------------------------------

            program = db.execute(
                """
                SELECT skills
                FROM programs
                WHERE id = ?
                """,
                (
                    assessment["program_id"],
                )
            ).fetchone()

            if program and program["skills"]:

                skill_names = [
                    skill.strip()
                    for skill in program["skills"].split(",")
                    if skill.strip()
                ]

                if percentage >= 80:

                    level = "Advanced"

                elif percentage >= 60:

                    level = "Intermediate"

                else:

                    level = "Beginner"

                for skill_name in skill_names:

                    existing_skill = db.execute(
                        """
                        SELECT id
                        FROM skills
                        WHERE employee_id = ?
                        AND program_id = ?
                        AND LOWER(skill_name) = LOWER(?)
                        """,
                        (
                            employee_id,
                            assessment["program_id"],
                            skill_name
                        )
                    ).fetchone()

                    if existing_skill:

                        db.execute(
                            """
                            UPDATE skills
                            SET
                                level = ?,
                                score = ?,
                                acquired_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (
                                level,
                                percentage,
                                existing_skill["id"]
                            )
                        )

                    else:

                        db.execute(
                            """
                            INSERT INTO skills
                            (
                                employee_id,
                                skill_name,
                                program_id,
                                level,
                                score
                            )
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                employee_id,
                                skill_name,
                                assessment["program_id"],
                                level,
                                percentage
                            )
                        )

            # ------------------------------------------------
            # CREATE CERTIFICATE
            # ------------------------------------------------

            certificate = db.execute(
                """
                SELECT id
                FROM certificates
                WHERE employee_id = ?
                AND program_id = ?
                """,
                (
                    employee_id,
                    assessment["program_id"]
                )
            ).fetchone()

            if not certificate:

                certificate_number = (
                    "SB-"
                    + datetime.now().strftime("%Y%m%d")
                    + "-"
                    + uuid.uuid4().hex[:8].upper()
                )

                db.execute(
                    """
                    INSERT INTO certificates
                    (
                        employee_id,
                        program_id,
                        result_id,
                        certificate_number
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        employee_id,
                        assessment["program_id"],
                        result_id,
                        certificate_number
                    )
                )

        # Save everything
        db.commit()

        flash(
            f"Assessment submitted successfully. "
            f"Score: {score:g}/{total_marks:g} "
            f"({percentage:.2f}%). "
            f"Result: {status.upper()} "
            f"(Passing: {passing_percentage:.2f}%).",
            "success"
        )

        return redirect(
            url_for(
                "employee_result",
                result_id=result_id
            )
        )

    return render_template(
        "employee/assessment.html",
        assessment=assessment,
        questions=questions
    )


# ============================================================
# EMPLOYEE - RESULT
# ============================================================

@app.route(
    "/employee/result/<int:result_id>"
)
@role_required("employee")
def employee_result(result_id):

    # Repair status before showing result
    repair_result_statuses()

    db = get_db()

    employee_id = session["user_id"]

    result = db.execute(
        """
        SELECT
            r.*,
            a.title AS assessment_title,
            a.passing_percentage,
            p.title AS program_title
        FROM results r
        JOIN assessments a
            ON r.assessment_id = a.id
        JOIN programs p
            ON a.program_id = p.id
        WHERE r.id = ?
        AND r.employee_id = ?
        """,
        (
            result_id,
            employee_id
        )
    ).fetchone()

    if not result:
        abort(404)

    return render_template(
        "employee/result.html",
        result=result
    )


# ============================================================
# EMPLOYEE - SKILLS
# ============================================================

@app.route("/employee/skills")
@role_required("employee")
def employee_skills():

    db = get_db()

    employee_id = session["user_id"]

    skills = db.execute(
        """
        SELECT
            s.*,
            p.title AS program_title
        FROM skills s
        LEFT JOIN programs p
            ON s.program_id = p.id
        WHERE s.employee_id = ?
        ORDER BY s.acquired_at DESC
        """,
        (employee_id,)
    ).fetchall()

    return render_template(
        "employee/skills.html",
        skills=skills
    )


# ============================================================
# EMPLOYEE - CERTIFICATES
# ============================================================

@app.route("/employee/certificates")
@role_required("employee")
def employee_certificates():

    db = get_db()

    employee_id = session["user_id"]

    certificates = db.execute(
        """
        SELECT
            c.*,
            p.title AS program_title,
            r.percentage
        FROM certificates c
        JOIN programs p
            ON c.program_id = p.id
        LEFT JOIN results r
            ON c.result_id = r.id
        WHERE c.employee_id = ?
        ORDER BY c.issued_at DESC
        """,
        (employee_id,)
    ).fetchall()

    return render_template(
        "employee/certificates.html",
        certificates=certificates
    )


# ============================================================
# CERTIFICATE - DOWNLOAD
# ============================================================

@app.route(
    "/certificate/download/<int:certificate_id>"
)
@login_required
def download_certificate(certificate_id):

    db = get_db()

    certificate = db.execute(
        """
        SELECT
            c.*,
            u.name AS employee_name,
            p.title AS program_title,
            r.percentage
        FROM certificates c
        JOIN users u
            ON c.employee_id = u.id
        JOIN programs p
            ON c.program_id = p.id
        LEFT JOIN results r
            ON c.result_id = r.id
        WHERE c.id = ?
        """,
        (certificate_id,)
    ).fetchone()

    if not certificate:
        abort(404)

    if (
        session.get("role") == "employee"
        and certificate["employee_id"]
        != session.get("user_id")
    ):

        abort(403)

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4
    )

    width, height = A4

    # Outer border
    pdf.setLineWidth(3)

    pdf.rect(
        35,
        35,
        width - 70,
        height - 70
    )

    # Inner border
    pdf.setLineWidth(1)

    pdf.rect(
        45,
        45,
        width - 90,
        height - 90
    )

    # SkillBridge
    pdf.setFont(
        "Helvetica-Bold",
        28
    )

    pdf.drawCentredString(
        width / 2,
        height - 130,
        "SKILLBRIDGE"
    )

    # Certificate title
    pdf.setFont(
        "Helvetica-Bold",
        22
    )

    pdf.drawCentredString(
        width / 2,
        height - 180,
        "CERTIFICATE OF COMPLETION"
    )

    pdf.setFont(
        "Helvetica",
        13
    )

    pdf.drawCentredString(
        width / 2,
        height - 225,
        "This certificate is proudly presented to"
    )

    # Employee
    pdf.setFont(
        "Helvetica-Bold",
        25
    )

    pdf.drawCentredString(
        width / 2,
        height - 280,
        certificate["employee_name"]
    )

    pdf.setFont(
        "Helvetica",
        13
    )

    pdf.drawCentredString(
        width / 2,
        height - 325,
        "for successfully completing the training program"
    )

    # Program
    pdf.setFont(
        "Helvetica-Bold",
        19
    )

    pdf.drawCentredString(
        width / 2,
        height - 365,
        certificate["program_title"]
    )

    # Score
    if certificate["percentage"] is not None:

        pdf.setFont(
            "Helvetica",
            13
        )

        pdf.drawCentredString(
            width / 2,
            height - 410,
            (
                "Assessment Score: "
                f"{certificate['percentage']:.2f}%"
            )
        )

    # Certificate number
    pdf.setFont(
        "Helvetica",
        11
    )

    pdf.drawString(
        80,
        120,
        (
            "Certificate No: "
            f"{certificate['certificate_number']}"
        )
    )

    # Issued date
    pdf.drawRightString(
        width - 80,
        120,
        (
            "Issued: "
            f"{certificate['issued_at']}"
        )
    )

    pdf.setFont(
        "Helvetica-Bold",
        12
    )

    pdf.drawCentredString(
        width / 2,
        80,
        "SkillBridge Training Management System"
    )

    pdf.save()

    buffer.seek(0)

    filename = (
        "SkillBridge_Certificate_"
        f"{certificate['certificate_number']}.pdf"
    )

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# ============================================================
# CERTIFICATE - VERIFY
# ============================================================

@app.route(
    "/certificate/verify/<int:certificate_id>"
)
def verify_certificate(certificate_id):

    db = get_db()

    certificate = db.execute(
        """
        SELECT
            c.*,
            u.name AS employee_name,
            p.title AS program_title,
            r.percentage
        FROM certificates c
        JOIN users u
            ON c.employee_id = u.id
        JOIN programs p
            ON c.program_id = p.id
        LEFT JOIN results r
            ON c.result_id = r.id
        WHERE c.id = ?
        """,
        (certificate_id,)
    ).fetchone()

    if not certificate:
        abort(404)

    return render_template(
        "certificate_verify.html",
        certificate=certificate
    )


# ============================================================
# BACKWARD COMPATIBILITY ENDPOINT ALIASES
# ============================================================

app.add_url_rule(
    "/trainer/assessments/create",
    endpoint="create_assessment",
    view_func=trainer_assessment_create,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/trainer/assessments/create",
    endpoint="trainer_create_assessment",
    view_func=trainer_assessment_create,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/trainer/assessments/edit/<int:assessment_id>",
    endpoint="edit_assessment",
    view_func=trainer_assessment_edit,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/trainer/assessments/delete/<int:assessment_id>",
    endpoint="delete_assessment",
    view_func=trainer_assessment_delete,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/trainer/assessments/<int:assessment_id>/questions",
    endpoint="assessment_questions",
    view_func=trainer_questions,
    methods=["GET"]
)

app.add_url_rule(
    "/trainer/assessments/<int:assessment_id>/questions/add",
    endpoint="add_question",
    view_func=trainer_question_add,
    methods=["POST"]
)

app.add_url_rule(
    "/trainer/questions/<int:question_id>/edit",
    endpoint="edit_question",
    view_func=trainer_question_edit,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/trainer/questions/<int:question_id>/delete",
    endpoint="delete_question",
    view_func=trainer_question_delete,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/employee/enroll/<int:program_id>",
    endpoint="enroll_program",
    view_func=employee_enroll,
    methods=["POST"]
)

app.add_url_rule(
    "/employee/progress/<int:enrollment_id>",
    endpoint="update_progress",
    view_func=employee_update_progress,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/employee/assessment/<int:assessment_id>",
    endpoint="take_assessment",
    view_func=employee_assessment,
    methods=["GET", "POST"]
)

app.add_url_rule(
    "/employee/result/<int:result_id>",
    endpoint="result",
    view_func=employee_result,
    methods=["GET"]
)


# ============================================================
# ERROR HANDLERS
# ============================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "404.html"
    ), 404


@app.errorhandler(500)
def internal_server_error(error):

    try:

        db = get_db()

        db.rollback()

    except Exception:
        pass

    return render_template(
        "500.html"
    ), 500


# ============================================================
# RUN APP
# ============================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )