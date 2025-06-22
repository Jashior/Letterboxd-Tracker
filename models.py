      
# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Film(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    letterboxd_slug = db.Column(db.String(200), unique=True, nullable=False) # e.g., "28-years-later"
    display_name = db.Column(db.String(255), nullable=False) # e.g., "28 Years Later"
    year = db.Column(db.Integer, nullable=True)
    director = db.Column(db.String(255), nullable=True)
    poster_url = db.Column(db.String(500), nullable=True)
    is_tracked = db.Column(db.Boolean, default=True, nullable=False) # To control polling
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_scraped_at = db.Column(db.DateTime, nullable=True)
    last_known_average_rating = db.Column(db.Float, nullable=True) # For quick display
    last_known_rating_count = db.Column(db.Integer, nullable=True) # For quick display
    display_order = db.Column(db.Integer, nullable=False, server_default='0') # For custom sorting

    ratings = db.relationship('RatingSnapshot', backref='film', lazy=True, cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Film {self.display_name}>'

class RatingSnapshot(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    film_id = db.Column(db.Integer, db.ForeignKey('film.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    average_rating = db.Column(db.Float, nullable=False) # e.g., 3.66
    rating_count = db.Column(db.Integer, nullable=False) # e.g., 49285

    def __repr__(self):
        return f'<RatingSnapshot {self.film_id} @ {self.timestamp}: {self.average_rating}>'

    