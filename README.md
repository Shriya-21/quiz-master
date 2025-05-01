<<<<<<< HEAD
# Quiz Master - V1

**Quiz Master - V1** is a web-based quiz preparation platform developed using Flask. It is designed to facilitate structured learning and assessment for students while providing comprehensive administrative control and analytics for instructors.

---

## 🔍 Overview

This application supports two types of users:  
- **Students**, who can enroll in subjects, attempt quizzes, and track their academic performance.
- **Administrators**, who manage the academic content, monitor student progress, and analyze participation and performance trends.

---


### Prerequisites

- Python 3.8 or higher
- Virtual environment (recommended)
- Required packages are enclosed in requirements.txt

## 🎯 Key Features

### Student Functionality
- Secure registration and authentication
- Enroll in available subjects
- View and attempt quizzes with time constraints
- Receive feedback and scores immediately upon submission
- Download quiz transcripts in PDF format
- Personalized dashboard with progress tracking

### Administrator Functionality
- Predefined administrator account with elevated privileges
- Create and manage subjects, quizzes, and multiple-choice questions (MCQs)
- Monitor student enrollments and quiz attempts
- Access detailed performance reports and top performer insights
- Download individual and aggregate score reports

### Analytics and Visualizations
- Dashboard includes:
  - Total number of students, subjects, and quizzes
  - Enrollment distribution per subject
  - Average score per subject
  - Top-performing students
  - Quiz attempt and completion metrics
- Visualizations are rendered using Matplotlib and embedded via Base64 encoding

---

## 🧰 Technology Stack

- **Backend Framework**: Flask (Python)
- **Templating Engine**: Jinja2
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: HTML, CSS, Bootstrap, Material Design Bootstrap (MDB)
- **Charting**: Matplotlib

---

## 📁 Project Structure

quiz-master-v1/ 
├── app.py 
├── models
│ ├── models.py 
│ ├── __init__.py 
├── templates/ 
│ ├── base.html 
│ ├── admin_dashboard.html 
│ ├── user_profile.html 
│ └── ... 
├── static/ 
│ ├── css/ 
│ └── charts/ 
├── instance/ 
│ └── quizmaster.sqlite 
├── config.py
├── extensions.py
├── .gitignore 
└── README.md

---
=======
# quiz-master
>>>>>>> origin/main
