from datetime import datetime
from . import db

class User(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email    = db.Column(db.String(120), unique=True, nullable=False)
    pw_hash  = db.Column(db.String(128), nullable=False)
    role     = db.Column(db.String(20), default="reader")   # reader | admin

class Book(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    title    = db.Column(db.String(150), index=True, nullable=False)
    author   = db.Column(db.String(150), index=True, nullable=False)
    year     = db.Column(db.Integer)
    genre    = db.Column(db.String(50), index=True)
    language = db.Column(db.String(30))
    overview = db.Column(db.Text)
    cover    = db.Column(db.String(200))    # path or URL
    file     = db.Column(db.String(200))    # pdf path

class Log(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    user_id   = db.Column(db.Integer, db.ForeignKey("user.id"))
    book_id   = db.Column(db.Integer, db.ForeignKey("book.id"))
    action    = db.Column(db.String(10))   # upload | download
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
