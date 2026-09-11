# SkillBridge – Complete Corporate Training Management System

## Stack
Flask, SQLite, HTML5, CSS3, JavaScript, Bootstrap 5, Chart.js CDN, ReportLab.

## Features
- Role-based Admin, Trainer and Employee authentication
- Admin employee/trainer management
- Training program create/update/delete and trainer assignment
- Enrollment tracking
- Trainer assessment and MCQ question management
- Employee assessment with automatic scoring and pass/fail
- Progress and skills tracking
- Admin certificate issuing after a passed assessment
- PDF certificate download
- Responsive corporate UI and registration validation

## Run on Windows PowerShell
```powershell
cd SkillBridge_Complete
python -m venv venv
venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```
Open http://127.0.0.1:5000

## Development seed accounts
The application creates local development accounts only when the database is empty. Credentials are intentionally not displayed on the Login page.
- admin@skillbridge.com / admin123
- employee@skillbridge.com / employee123
- trainer@skillbridge.com / trainer123

For a fresh reset, stop Flask and delete `skillbridge.db`, then run `python app.py` again.
