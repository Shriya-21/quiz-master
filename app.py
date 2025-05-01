import os
import numpy as np
import base64
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func

from extensions import db, migrate, login_manager
from models import User, Subject, Chapter, Quiz, Question, Score, enrollment, UserAnswer
from datetime import datetime, timedelta

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///quiz_master.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'shriya21'

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)

login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

#COMMON FUNCTIONALITY
#-----------------------------------------------------------------------------------------------------

@app.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for("admin_home" if current_user.is_admin else "user_home"))
    return render_template("home.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        full_name = request.form.get("full_name")
        email = request.form.get("email")
        gender = request.form.get("gender")
        dob = request.form.get("dob")
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        min_dob = datetime.now() - timedelta(days=5*365)
        
        if dob:
            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').date() 
            except ValueError:
                flash("Invalid Date of Birth format!", "danger")
                return redirect(url_for('register'))

        if dob > min_dob.date():
            flash("Invalid Date of Birth", "error")
            return redirect("/register")

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email is already registered!", "danger")
            return redirect(url_for('register'))

        import re
        email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_pattern, email):
            flash("Invalid email format.", "danger")
            return redirect(url_for('register'))

        if password != confirm_password:
            flash("Passwords do not match!", "danger")
            return redirect(url_for('register'))

        if not is_valid_password(password):
            flash("Password must be at least 8 characters, include an uppercase letter, a number, and a special character.", "error")
            return redirect("/register")

        new_user = User(full_name=full_name, email=email, gender = gender, dob=dob, password=password)
        db.session.add(new_user)
        db.session.commit()
        
        flash("Registration successful! You can now log in.", "success")
        return redirect(url_for('login'))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()
        if not user:  
            flash("Email not found in records. Please register!", "danger")
            return redirect(url_for('register'))

        if user.blocked:
            if user.failed_attempts >= 3:
                if user.last_failed_attempt and datetime.now() - user.last_failed_attempt > timedelta(hours=24):
                    user.blocked = False
                    user.failed_attempts = 0
                    user.last_failed_attempt = None
                    db.session.commit()
                    return redirect(url_for('login'))
                else:
                    return redirect(url_for('home'))
            else:
                flash("You are blocked by the admin. Please contact support.", "danger")
                return redirect(url_for('home'))

        if user.password == password:  
            user.failed_login = 0
            db.session.commit()

            login_user(user)
            if user.is_admin:
                return redirect(url_for("admin_home"))
            return redirect(url_for("user_home"))  

        user.failed_attempts += 1

        if user.failed_attempts >= 3:
            user.blocked = True
            user.last_failed_attempt = datetime.now()
            db.session.commit()
            flash("You have been blocked due to too many failed login attempts", "danger")
        else:
            db.session.commit()
            flash(f"Incorrect email or password. Attempt: {user.failed_attempts}/3", "danger")
 
        return redirect(url_for("login"))

    return render_template("login.html")

def is_valid_password(password):
    return (len(password) >= 8 and
            any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and
            any(c in "!@#$%^&*()-_=+[]{}|;:'\",.<>?/" for c in password))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully!", "success")
    return redirect(url_for("login"))


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        dob = request.form.get('dob')
        gender = request.form.get("gender")

        if dob:
            try:
                dob = datetime.strptime(dob, '%Y-%m-%d').date() 
            except ValueError:
                flash("Invalid Date of Birth format!", "danger")
                return redirect(url_for('edit_profile'))

        min_dob = datetime.now() - timedelta(days=5*365)
        if dob > min_dob.date():
            flash("Invalid Date of Birth!", "danger")
            return redirect(url_for('edit_profile'))

        current_user.full_name = full_name
        current_user.dob = dob
        current_user.gender = gender
        db.session.commit()
        flash("Profile updated successfully!", "success")

        return redirect(url_for('admin_profile' if current_user.is_admin else 'user_profile'))

    return render_template('edit_profile.html', user=current_user)

@app.route("/user/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if current_user.password != current_password:
            flash("Current password is incorrect.", "danger")
            return redirect(url_for("change_password"))

        if new_password != confirm_password:
            flash("New passwords do not match.", "danger")
            return redirect(url_for("change_password"))

        if not is_valid_password(new_password):
            flash("Password must be at least 8 characters long, contain an uppercase letter, a number, and a special character.", "danger")
            return redirect(url_for("change_password"))

        current_user.password = new_password
        db.session.commit()
        flash("Password changed successfully!", "success")
        return redirect(url_for("user_profile") if not current_user.is_admin else url_for("admin_profile"))

    return render_template("change_password.html")

#ADMIN FUNCTIONALITY
#-----------------------------------------------------------------------------------------------------

@app.route('/admin/home')
@login_required 
def admin_home():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    return render_template('admin_home.html')

@app.route("/admin/subjects")
@login_required
def admin_subjects():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    subjects = Subject.query.all() 
    return render_template("admin_subjects.html", subjects=subjects)

@app.route("/admin/add_subject", methods=["GET", "POST"])
@login_required
def add_subject():
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]

        if not name:
            flash("Subject name is required!", "danger")
            return redirect(url_for("add_subject")) 

        new_subject = Subject(name=name, description=description)
        db.session.add(new_subject)
        db.session.commit()
        flash("New subject added!", "success")
        return redirect(url_for("admin_subjects"))

    return render_template("admin_add_subject.html")

@app.route("/admin/delete_subject/<int:subject_id>", methods=["POST"])
@login_required
def delete_subject(subject_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    subject = Subject.query.get(subject_id)
    if subject:
        db.session.delete(subject)
        db.session.commit()
        flash("Subject deleted successfully!", "success")
    else:
        flash("Subject not found!", "danger")

    return redirect(url_for("admin_subjects"))

@app.route("/admin/edit_subject/<int:subject_id>", methods=["GET", "POST"])
@login_required
def edit_subject(subject_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    subject = Subject.query.get(subject_id)
    if not subject:
        flash("Subject not found!", "danger")
        return redirect(url_for("admin_home"))

    if request.method == "POST":
        subject.name = request.form["name"]
        subject.description = request.form["description"]
        db.session.commit()
        flash("Subject updated successfully!", "success")
        return redirect(url_for("admin_subjects"))

    return render_template("admin_edit_subject.html", subject=subject)

@app.route("/admin/add_chapter/<int:subject_id>", methods=["GET", "POST"])
@login_required
def add_chapter(subject_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home')) 

    subject = Subject.query.get_or_404(subject_id)

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]

        if not name:
            flash("Chapter name is required!", "danger")
            return redirect(url_for("add_chapter", subject_id=subject.id))

        new_chapter = Chapter(name=name, subject_id=subject.id, description=description)
        db.session.add(new_chapter)
        db.session.commit()
        flash("New chapter added!", "success")
        return redirect(url_for("admin_subjects"))

    return render_template("admin_add_chapter.html", subject=subject)

@app.route("/admin/edit_chapter/<int:chapter_id>", methods=["GET", "POST"])
@login_required
def edit_chapter(chapter_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == "POST":
        chapter.name = request.form["name"]
        chapter.description = request.form["description"]
        db.session.commit()
        flash("Chapter updated successfully!", "success")
        return redirect(url_for("admin_subjects"))

    return render_template("admin_edit_chapter.html", chapter=chapter)

@app.route("/admin/delete_chapter/<int:chapter_id>", methods=["GET", "POST"])
@login_required
def delete_chapter(chapter_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == "POST":
        db.session.delete(chapter)
        db.session.commit()
        flash("Chapter deleted successfully!", "success")
        return redirect(url_for("admin_home"))

    return render_template("delete_chapter.html", chapter=chapter)

@app.route('/admin/quizzes')
def admin_quizzes():
    subjects = Subject.query.options(db.joinedload(Subject.chapters).joinedload(Chapter.quizzes)).all()
    return render_template('admin_quizzes.html', subjects=subjects)


@app.route('/admin/add_quiz/<int:chapter_id>', methods=['GET', 'POST'])
def add_quiz(chapter_id):
        
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    chapter = Chapter.query.get_or_404(chapter_id)

    if request.method == 'POST':

        name = request.form.get('name')
        quiz_duration = request.form.get('quiz_duration')
        deadline = request.form.get('deadline')
        deadline_datetime = datetime.strptime(deadline, "%Y-%m-%dT%H:%M")

        time_now = datetime.now()

        chapter = Chapter.query.get(int(chapter_id))
    
        subject_id = chapter.subject_id

        if not name or not deadline:
            return "All fields are required", 400 

        if deadline_datetime < time_now:
            flash("Deadline must be in future!","error")
            return redirect(url_for('add_quiz', chapter_id=chapter_id))

        new_quiz = Quiz(name=name, quiz_duration = quiz_duration, deadline=deadline_datetime, subject_id=subject_id, chapter_id=chapter_id)
        db.session.add(new_quiz)
        db.session.commit()
        flash("Quiz added successfully!","success")
        return redirect(url_for('add_question', quiz_id=new_quiz.quiz_id))

    return render_template('admin_add_quiz.html', chapter=chapter)

@app.route('/admin/add_question/<int:quiz_id>', methods=['GET', 'POST'])
def add_question(quiz_id):

    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == 'POST':
        text = request.form.get('text')
        marks = request.form.get('marks')
        option_a = request.form.get('option_a')
        option_b = request.form.get('option_b')
        option_c = request.form.get('option_c')
        option_d = request.form.get('option_d')
        correct_option = request.form.get('correct_option')

        if not text or not option_a or not option_b or not option_c or not option_d or not correct_option:
            flash("All fields are required!", "danger")
            return redirect(url_for('add_question', quiz_id=quiz.id))

        new_question = Question(
            text=text,
            marks = marks,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_option=correct_option,
            quiz_id=quiz.quiz_id
        )
        
        db.session.add(new_question)
        db.session.commit()
        flash("Question Added!", "success")
        return redirect(url_for('add_question', quiz_id=quiz.quiz_id)) 

    return render_template('admin_add_question.html', quiz=quiz)

@app.route('/admin/edit_quiz/<int:quiz_id>', methods=["GET", "POST"])
@login_required
def edit_quiz(quiz_id):

    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    quiz = Quiz.query.get_or_404(quiz_id)

    if request.method == "POST":

        quiz.name = request.form.get("name")
        quiz.quiz_duration = int(request.form.get("quiz_duration"))
        quiz.deadline = request.form.get("deadline")
        deadline_str = request.form.get("deadline")
        if deadline_str:
            quiz.deadline = datetime.strptime(deadline_str, "%Y-%m-%dT%H:%M")

        if quiz.deadline < datetime.now():
            flash("Deadline must be in the future!", "error")
            return redirect(url_for("edit_quiz", quiz_id=quiz_id))

        for question in quiz.questions:
            question.text = request.form.get(f"question_text_{question.id}")
            question.option_a = request.form.get(f"option_a_{question.id}")
            question.option_b = request.form.get(f"option_b_{question.id}")
            question.option_c = request.form.get(f"option_c_{question.id}")
            question.option_d = request.form.get(f"option_d_{question.id}")
            question.correct_option = request.form.get(f"correct_option_{question.id}")
            question.marks = int(request.form.get(f"marks_{question.id}"))

        db.session.commit()
        flash("Quiz updated successfully!", "success")
        return redirect(url_for("admin_quizzes"))

    return render_template("admin_edit_quiz.html", quiz=quiz)

@app.route('/quiz/delete/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    quiz = Quiz.query.get_or_404(quiz_id)
    db.session.delete(quiz)
    db.session.commit()
    return redirect(url_for('admin_quizzes'))

@app.route('/admin/edit_question/<int:question_id>', methods=['GET', 'POST'])
def edit_question(question_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    question = Question.query.get_or_404(question_id)
    if request.method == 'POST':
        question.text = request.form.get('text')
        question.marks = request.form.get('marks')
        question.option_a = request.form.get('option_a')
        question.option_b = request.form.get('option_b')
        question.option_c = request.form.get('option_c')
        question.option_d = request.form.get('option_d')
        question.correct_option = request.form.get('correct_option')
        db.session.commit()
        return redirect(url_for('edit_quiz', quiz_id=question.quiz_id))  
    return render_template('admin_edit_question.html', question=question)

@app.route('/admin/delete_question/<int:question_id>', methods=['POST'])
def delete_question(question_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    question = Question.query.get_or_404(question_id)
    quiz_id = question.quiz_id  
    db.session.delete(question)
    db.session.commit()
    return redirect(url_for('edit_quiz', quiz_id=quiz_id))

@app.route("/admin/subject/<int:subject_id>/students")
@login_required
def view_enrolled_students(subject_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    subject = Subject.query.get_or_404(subject_id) 
    students = subject.students  

    return render_template("admin_view_students.html", subject=subject, students=students)

@app.route("/admin/submissions/<int:quiz_id>")
@login_required
def view_submissions(quiz_id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for('home'))

    quiz = Quiz.query.get_or_404(quiz_id)
    
    scores = Score.query.filter_by(quiz_id=quiz_id).join(User, Score.user_id == User.id).order_by(Score.time_stamp_of_attempt).all() 
    return render_template("admin_submissions.html", quiz=quiz, scores=scores)

@app.route('/admin/student/<int:student_id>')
@login_required
def view_student(student_id):
    if not current_user.is_admin:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('home'))

    student = User.query.get_or_404(student_id)
    quizzes = Score.query.filter_by(user_id=student_id)
    return render_template('admin_view_profile.html', user=student, quizzes = quizzes, admin_view=True)

@app.route("/admin/student/<int:id>")
@login_required
def admin_view_student(id):
    if not current_user.is_admin:
        flash("Unauthorized access!", "danger")
        return redirect(url_for("home"))

    student = User.query.get_or_404(id)
    scores = Score.query.filter_by(user_id=student.id).all()
    return render_template("admin_view_student.html", user=student, scores=scores)

@app.route("/admin/profile")
@login_required
def admin_profile():
    if not current_user.is_admin:
        flash("Access denied!", "danger")
        return redirect(url_for("home"))

    subjects_created = Subject.query.all()
    
    return render_template("admin_profile.html", admin=current_user, subjects_created=subjects_created)

@app.route('/admin/students')
@login_required
def student_list():
    if not current_user.is_admin:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('admin_home'))

    students = User.query.filter_by(is_admin=False).all() 
    return render_template('student_list.html', students=students)

@app.route('/admin/search', methods=['GET'])
@login_required
def admin_search():
    if not current_user.is_admin:
        flash("Unauthorized access.", "danger")
        return redirect(url_for('admin_home'))

    query = request.args.get('query', '').strip()

    if not query:
        return render_template("admin_search.html", query=query, subjects=[], quizzes=[], students=[])

    print(query)
    subjects = Subject.query.filter(Subject.name.ilike(f"%{query}%")).all()
    quizzes = db.session.query(Quiz.quiz_id, Quiz.name, Subject.name.label("subject_name")) \
        .join(Subject, Quiz.subject_id == Subject.id) \
        .filter((Quiz.name.ilike(f"%{query}%")) | (Subject.name.ilike(f"%{query}%"))).all()

    students = User.query.filter(
        User.full_name.ilike(f"%{query}%"), User.is_admin == False
    ).all()
    print(subjects)
    print(quizzes)
    print(students)

    return render_template(
        'admin_search.html',
        query=query,
        subjects=subjects,
        quizzes=quizzes,
        students=students
    )

@app.route('/admin/block_student/<int:user_id>', methods=['POST'])
@login_required
def block_student(user_id):
    if not current_user.is_admin:
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for('home'))
    
    student = User.query.get_or_404(user_id)
    
    student.blocked = True
    db.session.commit()
    
    flash(f"Student {student.full_name} has been blocked.", "success")
    return redirect(url_for('student_list'))

@app.route('/admin/unblock_student/<int:user_id>', methods=['POST'])
@login_required
def unblock_student(user_id):
    if not current_user.is_admin:
        flash("You are not authorized to perform this action.", "danger")
        return redirect(url_for('home'))
    
    student = User.query.get_or_404(user_id)
    
    student.blocked = False
    db.session.commit()
    
    flash(f"Student {student.full_name} has been unblocked.", "success")
    return redirect(url_for('student_list'))

def delete_score(score_id):
    if not current_user.is_admin:
        os.abort(403)

    score = Score.query.get_or_404(score_id)
    db.session.delete(score)
    db.session.commit()

    flash("Attempt deleted successfully!", "success")
    return redirect(url_for("admin_submissions"))

def generate_chart(data, labels, chart_type="bar"):
    fig, ax = plt.subplots(figsize=(6, 4))

    gradient_colors = ['#E1C16E', '#B5A27A', '#8C8073', '#5C5752']
    cmap = plt.get_cmap("cividis")

    if chart_type == "bar":
        colors = [cmap(i / len(data)) for i in range(len(data))]
        ax.bar(labels, data, color=colors, edgecolor="#5C5752")
        ax.set_ylabel("Count", fontsize=12, color="#7A6F5A")
        ax.spines['bottom'].set_color("#000000")
        ax.set_facecolor("#ECE6DA")

    elif chart_type == "pie":
        filtered_data = [d for d in data if d > 0]
        filtered_labels = [labels[i] for i in range(len(data)) if data[i] > 0]

        if filtered_data:
            ax.pie(filtered_data, labels=filtered_labels, autopct='%1.1f%%',
                   colors=gradient_colors[:len(filtered_data)], startangle=140,
                   wedgeprops={'edgecolor': 'white', 'linewidth': 1.5})
        else:
            ax.text(0.5, 0.5, "No Data Available", fontsize=12, ha='center', va='center', color="#7A6F5A")

    elif chart_type == "line":
        x = np.arange(len(labels))
        ax.plot(x, data, marker='o', linestyle='-', color='#E1C16E', linewidth=2, markersize=6)

        ax.fill_between(x, data, color='#B5A27A', alpha=0.3)
        ax.set_ylabel("Average Score", fontsize=12, color="#7A6F5A")
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=30, ha='right')

    img = io.BytesIO()
    plt.savefig(img, format='png', bbox_inches='tight', facecolor="#ECE6DA")
    img.seek(0)
    chart_url = base64.b64encode(img.getvalue()).decode()
    plt.close()
    return chart_url

@app.route('/admin_dashboard')
def admin_dashboard():
    total_students = User.query.filter_by(is_admin=False).count()
    total_subjects = Subject.query.count()
    total_quizzes = Quiz.query.count()
    
    subjects = Subject.query.all()
    subject_names = [subject.name for subject in subjects]
    
    enrollments = [len(subject.enrolled_users) for subject in subjects]    
    enrollments_pie_chart = generate_chart(enrollments, subject_names, "pie") if sum(enrollments) > 0 else None
    enrollments_bar_chart = generate_chart(enrollments, subject_names, "bar") if sum(enrollments) > 0 else None

    average_scores = []
    for subject in subjects:
        scores = [score.score_percentage for quiz in subject.quizzes for score in quiz.scores]
        avg_score = sum(scores) / len(scores) if scores else 0
        average_scores.append(avg_score)

    average_scores_chart = generate_chart(average_scores, subject_names, "line")

    students = User.query.filter_by(is_admin=False).all()
    leaderboard = []
    for student in students:
        scores = [score.score_percentage for score in student.scores]
        avg_score = sum(scores) / len(scores) if scores else 0
        leaderboard.append({"name": student.full_name, "attempts": len(scores), "avg_score": avg_score})

    leaderboard = sorted(leaderboard, key=lambda x: x["avg_score"], reverse=True)[:5]

    return render_template("admin_dashboard.html",
                           total_students=total_students,
                           total_subjects=total_subjects,
                           total_quizzes=total_quizzes,
                           enrollments_pie_chart=enrollments_pie_chart,
                           enrollments_bar_chart=enrollments_bar_chart,
                           average_scores_chart=average_scores_chart,
                           leaderboard=leaderboard)


#USER FUNCTIONALITY
#-----------------------------------------------------------------------------------------------------

@app.route("/user/home")
@login_required
def user_home():
    return render_template("user_home.html")


@app.route("/user/subjects")
@login_required
def user_subjects():
    enrolled_subjects = current_user.subjects 
    return render_template("user_subjects.html", subjects=enrolled_subjects)

@app.route("/user/quizzes")
@login_required
def user_quizzes():
    enrolled_subjects = current_user.subjects
    subject_ids = [subject.id for subject in enrolled_subjects]
    quizzes = Quiz.query.join(Chapter).filter(Chapter.subject_id.in_(subject_ids)).order_by(Quiz.deadline).all()
    scores = Score.query.filter_by(user_id=current_user.id).all()
    score_dict = {
        score.quiz_id: {
            "user_id": score.user_id,
            "total_scored": score.total_scored,
            "time_stamp_of_attempt": score.time_stamp_of_attempt
        }
        for score in scores
    }

    print(Quiz.deadline, datetime.utcnow())
    return render_template('user_quizzes.html', quizzes = quizzes, score_dict = score_dict, current_time=datetime.now())

@app.route("/user/quiz/<int:quiz_id>", methods=["GET"])
@login_required
def attempt_quiz(quiz_id):

    quiz = Quiz.query.get_or_404(quiz_id)

    if quiz.deadline < datetime.now():
        flash("The deadline for this quiz has passed. You cannot attempt it anymore.", "danger")
        return redirect(url_for("user_home")) 
    return render_template("user_attempt_quiz.html", quiz=quiz, datetime=datetime.now())


@app.route("/user/quiz/submit/<int:quiz_id>", methods=["POST"])
@login_required
def submit_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)
    total_score = 0

    # Create a new Score first
    new_score = Score(
        quiz_id=quiz.quiz_id,
        user_id=current_user.id,
        time_stamp_of_attempt=datetime.now(),
        total_scored=0  # Initial value, will update later
    )
    db.session.add(new_score)
    db.session.commit()  # Commit to get the `new_score.id`

    for question in quiz.questions:
        user_answer = request.form.get(f"question_{question.id}")  # Get the answer from the form
        
        # Check if the user provided an answer
        if user_answer is None:
            is_correct = False
            marks_awarded = 0
        else:
            is_correct = user_answer == question.correct_option
            marks_awarded = question.marks if is_correct else 0

        total_score += marks_awarded

        # Create the UserAnswer entry and link it to the new_score
        user_answer_entry = UserAnswer(
            user_id=current_user.id,
            quiz_id=quiz.quiz_id,
            score_id=new_score.id,  # Link the user_answer to the correct score
            question_id=question.id,
            selected_answer=user_answer,
            is_correct=is_correct,
            marks_awarded=marks_awarded
        )
        db.session.add(user_answer_entry)

    # After collecting all the answers, update the total score
    new_score.total_scored = total_score
    db.session.commit()  # Commit the total score to the Score table

    flash("Quiz submitted successfully!", "success")
    return redirect(url_for("user_quizzes"))


@app.route("/quiz/transcript/<int:quiz_id>/<int:user_id>")
@login_required
def view_transcript(quiz_id, user_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    # Get the latest attempt for the given user and quiz
    latest_score = db.session.query(Score).filter_by(user_id=user_id, quiz_id=quiz_id).order_by(Score.time_stamp_of_attempt.desc()).first()

    # If no score exists for the user, show an error message
    if not latest_score or latest_score.total_scored is None or quiz.total_marks is None or quiz.total_marks == 0:
        flash("Transcript not available. The student has not attempted the quiz yet.", "danger")
        return redirect(url_for("admin_submissions" if current_user.is_admin else "user_quizzes"))

    # Get user answers for the latest attempt
    user_answers = UserAnswer.query.filter_by(user_id=user_id, quiz_id=quiz_id).all()

    # Get the highest score for this user on this quiz
    highest_score = db.session.query(Score).filter_by(user_id=user_id, quiz_id=quiz_id).order_by(Score.total_scored.desc()).first()

    # Calculate the number of attempts
    number_of_attempts = db.session.query(Score).filter_by(user_id=user_id, quiz_id=quiz_id).count()

    # Count the number of skipped questions (those with None as the selected_answer)
    skipped_questions = db.session.query(UserAnswer).filter_by(user_id=user_id, quiz_id=quiz_id, selected_answer=None).count()

    # Calculate the score percentage for the latest attempt
    score_percentage = (latest_score.total_scored / quiz.total_marks) * 100 if quiz.total_marks else 0

    user = User.query.get_or_404(user_id)

    return render_template(
        "user_transcript.html",
        quiz=quiz,
        score=latest_score,  # Latest score
        score_percentage=score_percentage,
        user=user,
        user_answers=user_answers,
        number_of_attempts=number_of_attempts,
        highest_score=highest_score,
        skipped_questions=skipped_questions
    )


@app.route("/user/enrol")
@login_required
def enrol_subject():

    enrolled_subjects = {subject.id for subject in current_user.subjects} 
    available_subjects = Subject.query.filter(~Subject.id.in_(enrolled_subjects)).all()  

    return render_template("enrol_subject.html", subjects=available_subjects)

@app.route("/enroll/<int:subject_id>", methods=["POST"])
@login_required
def user_enrol(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    if subject not in current_user.subjects:
        current_user.subjects.append(subject)
        db.session.commit()
        flash(f"Enrolled in {subject.name}!", "success")
    else:
        flash("Already enrolled.", "info")

    return redirect(url_for("enrol_subject"))

@app.route("/subjects/enroll/<int:subject_id>", methods=["POST"])
@login_required
def enroll_in_subject(subject_id):
    subject = Subject.query.get_or_404(subject_id)

    if subject in current_user.subjects:
        flash("You are already enrolled in this subject!", "warning")
        return redirect(url_for("enrol_subject"))

    current_user.subjects.append(subject)
    db.session.commit()

    flash(f"Successfully enrolled in {subject.name}!", "success")
    return redirect(url_for("user_subjects"))

@app.route("/user/profile")
@login_required
def user_profile():
    scores = Score.query.filter_by(user_id=current_user.id).all()
    return render_template("user_profile.html", user=current_user, scores=scores)

@app.route('/user/search', methods=['GET'])
@login_required
def user_search():
    query = request.args.get('query', '').strip()

    if not query:
        return render_template("admin_search.html", query=query, subjects=[], quizzes=[], students=[])

    print(query)
    subjects = Subject.query.filter(Subject.name.ilike(f"%{query}%")).all()
    quizzes = db.session.query(Quiz.quiz_id, Quiz.name, Subject.name.label("subject_name")) \
        .join(Subject, Quiz.subject_id == Subject.id) \
        .filter((Quiz.name.ilike(f"%{query}%")) | (Subject.name.ilike(f"%{query}%"))).all()


    students = User.query.filter(
        User.full_name.ilike(f"%{query}%"), User.is_admin == False
    ).all()
    print(subjects)
    print(quizzes)
    print(students)

    return render_template(
        'user_search.html',
        query=query,
        subjects=subjects,
        quizzes=quizzes,
        students=students
    )

@app.route("/view_quiz/<int:quiz_id>")
@login_required
def view_quiz(quiz_id):
    quiz = Quiz.query.get_or_404(quiz_id)

    total_questions = len(quiz.questions)
    total_marks = sum(q.marks for q in quiz.questions)
    user_attempt = Score.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).first()

    return render_template(
        "view_quiz.html",
        quiz=quiz,
        total_questions=total_questions,
        total_marks=total_marks,
        user_attempt=user_attempt,
        datetime = datetime.now()
    )

@app.route('/unenroll/<int:subject_id>', methods=['POST'])
def unenroll(subject_id):
    subject = Subject.query.get_or_404(subject_id)
    current_user.subjects.remove(subject)

    db.session.commit()
        
    flash(f'You have successfully unenrolled from {subject.name}.', 'success')

    return redirect(url_for('user_subjects'))

def create_admin_user():
    if not User.query.filter_by(email="admin@quizmaster.com").first():
        admin_user = User(
            email="admin@quizmaster.com",
            full_name="Admin",
            gender="Admin",
            dob=datetime.strptime("1990-01-01", "%Y-%m-%d").date(),
            is_admin=True,
            password="Admin@123"
        )
        db.session.add(admin_user)
        db.session.commit()


with app.app_context():
    db.create_all() 
    create_admin_user()

if __name__ == "__main__":
    app.run(debug=True)
