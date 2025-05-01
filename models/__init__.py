from extensions import db
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func

from extensions import db
from .models import User, Subject, Chapter, Quiz, Question, Score, enrollment, UserAnswer  

db = SQLAlchemy()
