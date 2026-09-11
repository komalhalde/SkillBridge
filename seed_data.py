import sqlite3

DB_NAME = "skillbridge.db"

db = sqlite3.connect(DB_NAME)
db.execute("PRAGMA foreign_keys = ON")

# Get demo trainer
trainer = db.execute(
    "SELECT id FROM users WHERE email = ?",
    ("trainer@skillbridge.com",)
).fetchone()

# Get demo employee
employee = db.execute(
    "SELECT id FROM users WHERE email = ?",
    ("employee@skillbridge.com",)
).fetchone()

if not trainer:
    print("Demo trainer not found.")
    db.close()
    exit()

if not employee:
    print("Demo employee not found.")
    db.close()
    exit()

trainer_id = trainer[0]
employee_id = employee[0]

# -------------------------------------------------
# SAMPLE TRAINING PROGRAMS
# -------------------------------------------------

programs = [
    (
        "Python Programming",
        "Learn Python fundamentals, functions, OOP, file handling and database connectivity.",
        "6 Weeks",
        "Python, Programming, OOP, SQLite"
    ),
    (
        "Web Development",
        "Learn HTML, CSS, JavaScript and Flask for developing modern web applications.",
        "8 Weeks",
        "HTML, CSS, JavaScript, Flask, Web Development"
    ),
    (
        "Data Analytics",
        "Learn data analysis using Python, Pandas, NumPy and data visualization.",
        "6 Weeks",
        "Python, Pandas, NumPy, Data Analytics"
    )
]

program_ids = []

for title, description, duration, skills in programs:

    existing = db.execute(
        "SELECT id FROM programs WHERE title = ?",
        (title,)
    ).fetchone()

    if existing:
        program_id = existing[0]
        print(f"Already exists: {title}")
    else:
        cursor = db.execute(
            """
            INSERT INTO programs
            (title, description, duration, skills, trainer_id)
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

        program_id = cursor.lastrowid
        print(f"Added program: {title}")

    program_ids.append(program_id)


# -------------------------------------------------
# SAMPLE ENROLLMENT
# -------------------------------------------------

python_program_id = program_ids[0]

existing_enrollment = db.execute(
    """
    SELECT id
    FROM enrollments
    WHERE employee_id = ? AND program_id = ?
    """,
    (employee_id, python_program_id)
).fetchone()

if not existing_enrollment:

    db.execute(
        """
        INSERT INTO enrollments
        (employee_id, program_id, progress, status)
        VALUES (?, ?, ?, ?)
        """,
        (
            employee_id,
            python_program_id,
            60,
            "in_progress"
        )
    )

    print("Demo Employee enrolled in Python Programming.")


# -------------------------------------------------
# SAMPLE ASSESSMENT
# -------------------------------------------------

assessment = db.execute(
    """
    SELECT id
    FROM assessments
    WHERE program_id = ?
    AND title = ?
    """,
    (
        python_program_id,
        "Python Programming Assessment"
    )
).fetchone()

if assessment:
    assessment_id = assessment[0]
else:

    cursor = db.execute(
        """
        INSERT INTO assessments
        (program_id, trainer_id, title, description, passing_percentage)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            python_program_id,
            trainer_id,
            "Python Programming Assessment",
            "Basic Python programming assessment.",
            50
        )
    )

    assessment_id = cursor.lastrowid

    print("Added Python assessment.")


# -------------------------------------------------
# SAMPLE MCQ QUESTIONS
# -------------------------------------------------

questions = [
    (
        "Which keyword is used to define a function in Python?",
        "function",
        "def",
        "func",
        "define",
        "B",
        1
    ),
    (
        "Which data type is used to store multiple items in an ordered collection?",
        "List",
        "Integer",
        "Boolean",
        "Float",
        "A",
        1
    ),
    (
        "Which symbol is used for a comment in Python?",
        "//",
        "/*",
        "#",
        "--",
        "C",
        1
    ),
    (
        "Which function is used to display output in Python?",
        "display()",
        "echo()",
        "print()",
        "show()",
        "C",
        1
    ),
    (
        "Which keyword is used to create a class in Python?",
        "object",
        "class",
        "struct",
        "create",
        "B",
        1
    )
]

for question in questions:

    existing_question = db.execute(
        """
        SELECT id
        FROM questions
        WHERE assessment_id = ?
        AND question_text = ?
        """,
        (
            assessment_id,
            question[0]
        )
    ).fetchone()

    if not existing_question:

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
                question[0],
                question[1],
                question[2],
                question[3],
                question[4],
                question[5],
                question[6]
            )
        )

print("Sample MCQ questions added.")

db.commit()
db.close()

print("")
print("====================================")
print(" SAMPLE DATA ADDED SUCCESSFULLY ")
print("====================================")
print("")
print("Programs:")
print("1. Python Programming")
print("2. Web Development")
print("3. Data Analytics")
print("")
print("Python assessment with 5 MCQs created.")
print("Demo Employee enrolled in Python Programming.")