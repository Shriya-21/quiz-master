from extensions import db
from flask_login import UserMixin
from datetime import date

enrollment = db.Table(
    'enrollment',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('subject_id', db.Integer, db.ForeignKey('subject.id'), primary_key=True),
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date)
    gender = db.Column(db.String, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    blocked = db.Column(db.Boolean, default=False)

    failed_attempts = db.Column(db.Integer, default=0)
    last_failed_attempt = db.Column(db.DateTime)
    score_id = db.Column(db.Integer, db.ForeignKey('score.id')) 
    
    subjects = db.relationship('Subject', secondary=enrollment, backref=db.backref('enrolled_users', lazy=True))
    scores = db.relationship('Score', back_populates='user', foreign_keys='Score.user_id')

    def check_password(self, pwd):
        return self.password == pwd
    
    def calculate_age(self, today):
        if not self.dob:
            return None  
        today = date.today()
        age = today.year - self.dob.year - (
            (today.month, today.day) < (self.dob.month, self.dob.day)
        )
        return age

class Subject(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)

    chapters = db.relationship('Chapter', backref='subject', cascade="all, delete", lazy=True)
    quizzes = db.relationship('Quiz', backref='subject', cascade="all, delete", lazy=True)

    def __repr__(self):
        return f"<Subject {self.name}>"

class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    quizzes = db.relationship('Quiz', backref='chapter', cascade="all, delete-orphan", lazy=True)

    def __repr__(self):
        return f"<Chapter {self.name}>"

class Quiz(db.Model):
    quiz_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    deadline = db.Column(db.DateTime, nullable=False)
    quiz_duration = db.Column(db.Integer, nullable=False)
    subject_id = db.Column(db.Integer, db.ForeignKey('subject.id'), nullable=False)
    chapter_id = db.Column(db.Integer, db.ForeignKey('chapter.id'), nullable=False)
    
    questions = db.relationship('Question', backref='quiz', cascade="all, delete-orphan")
    scores = db.relationship("Score", back_populates="quiz", cascade="all, delete-orphan")

    @property
    def total_marks(self):
        return sum(question.marks for question in self.questions)

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    option_a = db.Column(db.String(200), nullable=False)
    option_b = db.Column(db.String(200), nullable=False)
    option_c = db.Column(db.String(200), nullable=False)
    option_d = db.Column(db.String(200), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.quiz_id'), nullable=False)
    marks = db.Column(db.Integer, nullable=False, default=1)

    answers = db.relationship('UserAnswer', back_populates="question", cascade="all, delete-orphan")


class Score(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.quiz_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    time_stamp_of_attempt = db.Column(db.DateTime, nullable=False)
    total_scored = db.Column(db.Integer, nullable=False)

    user_answers = db.relationship('UserAnswer', backref='score', cascade="all, delete-orphan", lazy=True)
    quiz = db.relationship("Quiz", back_populates="scores")
    user = db.relationship('User', back_populates='scores', foreign_keys=[user_id])

    @property
    def score_percentage(self):
        """Calculates the percentage score based on total marks of the quiz."""
        if self.quiz and self.quiz.total_marks:  
            return round((self.total_scored * 100) / self.quiz.total_marks, 2)
        return 0

class UserAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.quiz_id'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    selected_answer = db.Column(db.String(1), nullable=True)
    is_correct = db.Column(db.Boolean, nullable=False)
    marks_awarded = db.Column(db.Integer, nullable=False, default=0)

    user = db.relationship('User', backref='answers')
    quiz = db.relationship('Quiz', backref='answers')
    question = db.relationship('Question', back_populates="answers")
    score_id = db.Column(db.Integer, db.ForeignKey('score.id'), nullable=False)
