import sqlite3
from pathlib import Path


# =========================================================
# SkillBridge Database Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE = BASE_DIR / "skillbridge.db"


# =========================================================
# Get Database Connection
# =========================================================

def get_db():
    """
    Create and return SQLite database connection.
    """

    conn = sqlite3.connect(DATABASE)

    # Return rows like dictionaries
    conn.row_factory = sqlite3.Row

    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# =========================================================
# Initialize Database
# =========================================================

def init_db():
    """
    Create all required SkillBridge database tables
    and insert default demo users.
    """

    conn = get_db()
    cursor = conn.cursor()

    # =====================================================
    # USERS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
                CHECK(role IN ('admin', 'trainer', 'employee')),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # =====================================================
    # PROGRAMS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            duration TEXT,
            skills TEXT,
            trainer_id INTEGER,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (trainer_id)
                REFERENCES users(id)
                ON DELETE SET NULL
        )
    """)

    # =====================================================
    # ENROLLMENTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_id INTEGER NOT NULL,
            program_id INTEGER NOT NULL,

            progress INTEGER DEFAULT 0,
            status TEXT DEFAULT 'In Progress',

            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (employee_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (program_id)
                REFERENCES programs(id)
                ON DELETE CASCADE,

            UNIQUE(employee_id, program_id)
        )
    """)

    # =====================================================
    # ASSESSMENTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            program_id INTEGER NOT NULL,
            trainer_id INTEGER NOT NULL,

            title TEXT NOT NULL,
            description TEXT,

            passing_percentage INTEGER DEFAULT 40,

            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (program_id)
                REFERENCES programs(id)
                ON DELETE CASCADE,

            FOREIGN KEY (trainer_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        )
    """)

    # =====================================================
    # QUESTIONS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            assessment_id INTEGER NOT NULL,

            question_text TEXT NOT NULL,

            option_a TEXT NOT NULL,
            option_b TEXT NOT NULL,
            option_c TEXT NOT NULL,
            option_d TEXT NOT NULL,

            correct_answer TEXT NOT NULL
                CHECK(correct_answer IN ('A', 'B', 'C', 'D')),

            marks INTEGER DEFAULT 1,

            FOREIGN KEY (assessment_id)
                REFERENCES assessments(id)
                ON DELETE CASCADE
        )
    """)

    # =====================================================
    # RESULTS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            assessment_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,

            score INTEGER DEFAULT 0,
            total_marks INTEGER DEFAULT 0,

            percentage REAL DEFAULT 0,

            status TEXT DEFAULT 'Fail',

            attempt_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (assessment_id)
                REFERENCES assessments(id)
                ON DELETE CASCADE,

            FOREIGN KEY (employee_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            UNIQUE(assessment_id, employee_id)
        )
    """)

    # =====================================================
    # SKILLS TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_id INTEGER NOT NULL,

            skill_name TEXT NOT NULL,

            program_id INTEGER,

            level TEXT DEFAULT 'Beginner',

            score REAL,

            acquired_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (employee_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (program_id)
                REFERENCES programs(id)
                ON DELETE SET NULL
        )
    """)

    # =====================================================
    # CERTIFICATES TABLE
    # =====================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS certificates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            employee_id INTEGER NOT NULL,
            program_id INTEGER NOT NULL,

            result_id INTEGER,

            certificate_number TEXT UNIQUE NOT NULL,

            issued_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (employee_id)
                REFERENCES users(id)
                ON DELETE CASCADE,

            FOREIGN KEY (program_id)
                REFERENCES programs(id)
                ON DELETE CASCADE,

            FOREIGN KEY (result_id)
                REFERENCES results(id)
                ON DELETE SET NULL
        )
    """)

    # =====================================================
    # DEFAULT ADMIN
    # =====================================================

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (
        "System Admin",
        "admin@skillbridge.com",
        "admin123",
        "admin"
    ))

    # =====================================================
    # DEFAULT TRAINER
    # =====================================================

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Demo Trainer",
        "trainer@skillbridge.com",
        "trainer123",
        "trainer"
    ))

    # =====================================================
    # DEFAULT EMPLOYEE
    # =====================================================

    cursor.execute("""
        INSERT OR IGNORE INTO users
        (name, email, password, role)
        VALUES (?, ?, ?, ?)
    """, (
        "Demo Employee",
        "employee@skillbridge.com",
        "employee123",
        "employee"
    ))

    # =====================================================
    # SAVE DATABASE
    # =====================================================

    conn.commit()
    conn.close()


# =========================================================
# Run Database Directly
# =========================================================

if __name__ == "__main__":

    init_db()

    print("========================================")
    print("SkillBridge Database Initialized")
    print("========================================")
    print(f"Database Location: {DATABASE}")