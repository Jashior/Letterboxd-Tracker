# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash # For password hashing
from functools import wraps
import re
import sys
from datetime import datetime
import logging

from config import Config
from models import db, Film, RatingSnapshot  # Remove FilmRatingHistory
from scraper import get_film_data
from tasks import run_scrape_job_for_film  # Import from new tasks.py
from scheduler import init_scheduler, scheduler, SCRAPE_JOB_ID  # Import the initializer and scheduler instance


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

    
# Ensure the instance folder exists for SQLite
try:
    os.makedirs(app.instance_path)
except OSError:
    pass # Already exists
# Flask's convention for SQLite DB, etc. `app.instance_path` resolves to a folder named 'instance'
os.makedirs(app.instance_path, exist_ok=True)
 
db.init_app(app)
migrate = Migrate(app, db) # Initialize Flask-Migrate

# Initialize and start the scheduler if enabled in config.
# We add a check to prevent starting the scheduler during 'flask db' commands.
is_running_db_command = len(sys.argv) > 1 and sys.argv[1] == 'db'

if app.config.get('SCHEDULER_API_ENABLED') and not is_running_db_command:
    init_scheduler(app) # This function now handles the scheduler's lifecycle

# --- Admin Authentication ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # For simplicity, we are not storing hashed passwords for the admin user in DB
        # We are comparing with env variables. For more users, use a User model.
        if username == app.config['ADMIN_USERNAME'] and password == app.config['ADMIN_PASSWORD']:
            session['admin_logged_in'] = True
            flash('Logged in successfully!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('admin_dashboard'))
        else:
            flash('Invalid credentials. Please try again.', 'danger')
    return render_template('admin/login.html')

@app.route('/logout')
def logout():
    session.pop('admin_logged_in', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# --- Admin Routes ---
@app.route('/admin')
@login_required
def admin_dashboard():
    films = Film.query.order_by(Film.display_name).all()
    job = scheduler.get_job(SCRAPE_JOB_ID)
    next_run_time = job.next_run_time if job else None
    return render_template('admin/dashboard.html', films=films, next_run_time=next_run_time)

@app.route('/admin/add_film', methods=['POST'])
@login_required
def add_film():
    letterboxd_url = request.form['letterboxd_url']
    # Extract slug: https://letterboxd.com/film/slug-name/ -> slug-name
    match = re.search(r'letterboxd\.com/film/([^/]+)/?', letterboxd_url)
    if not match:
        flash('Invalid Letterboxd film URL format.', 'danger')
        return redirect(url_for('admin_dashboard'))

    slug = match.group(1)
    existing_film = Film.query.filter_by(letterboxd_slug=slug).first()
    if existing_film:
        flash(f'Film "{slug}" is already tracked.', 'warning')
        return redirect(url_for('admin_dashboard'))

    # Fetch initial data to populate display_name, year etc.
    scraped_data = get_film_data(slug)
    if not scraped_data or not scraped_data.get('display_name'):
        flash(f'Could not fetch initial data for "{slug}". Please check the slug or try again later.', 'danger')
        return redirect(url_for('admin_dashboard'))

    new_film = Film(
        letterboxd_slug=slug,
        display_name=scraped_data.get('display_name', slug),
        year=scraped_data.get('year'),
        director=scraped_data.get('director'),
        poster_url=scraped_data.get('poster_url'),
        is_tracked=True # Default to tracked
    )
    db.session.add(new_film)
    
    # Add initial rating snapshot if available
    if 'average_rating' in scraped_data and 'rating_count' in scraped_data:
        new_film.last_known_average_rating = scraped_data['average_rating']
        new_film.last_known_rating_count = scraped_data['rating_count']
        new_film.last_scraped_at = datetime.utcnow()
        snapshot = RatingSnapshot(
            film_id=new_film.id, # This will be set after commit if new_film is flushed
            average_rating=scraped_data['average_rating'],
            rating_count=scraped_data['rating_count']
        )
        # Need to commit film first to get its ID for the snapshot, or handle it carefully.
        # Let's commit film, then add snapshot related to it.
        try:
            db.session.commit() # Commit film to get ID
            
            # Re-fetch the film to ensure we have the ID for the snapshot if it was a new film.
            # Or, if using Flask-SQLAlchemy, the ID might be populated after flush.
            # For safety, fetch it again if it's a new entry, or associate directly
            # if the ORM handles it. Assuming new_film.id is populated after commit.

            snapshot.film_id = new_film.id # Ensure film_id is set
            db.session.add(snapshot)
            db.session.commit()
            flash(f'Film "{new_film.display_name}" added and initial rating snapshot saved.', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding film {slug} or its snapshot: {e}")
            flash(f'Error adding film "{slug}": {e}', 'danger')
    else:
        try:
            db.session.commit()
            flash(f'Film "{new_film.display_name}" added. No rating data found yet (e.g., unreleased).', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding film {slug} (no initial rating): {e}")
            flash(f'Error adding film "{slug}": {e}', 'danger')

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/toggle_tracking/<int:film_id>', methods=['POST'])
@login_required
def toggle_tracking(film_id):
    film = Film.query.get_or_404(film_id)
    film.is_tracked = not film.is_tracked
    db.session.commit()
    status = "now tracked" if film.is_tracked else "no longer tracked"
    flash(f'Film "{film.display_name}" is {status}.', 'info')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete_film/<int:film_id>', methods=['POST'])
@login_required
def delete_film(film_id):
    film = Film.query.get_or_404(film_id)
    # Related RatingSnapshots will be deleted due to cascade="all, delete-orphan"
    db.session.delete(film)
    db.session.commit()
    flash(f'Film "{film.display_name}" and all its data deleted.', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/scrape_now/<int:film_id>', methods=['POST'])
@login_required
def scrape_now_film(film_id):
    film = Film.query.get_or_404(film_id)
    logger.info(f"Manual scrape initiated for {film.display_name}")
    # Call the scraping logic from our tasks file
    success = run_scrape_job_for_film(film.id) # Pass film_id
    if success:
        flash(f'Successfully scraped new data for "{film.display_name}".', 'success')
    else:
        flash(f'Failed to scrape new data for "{film.display_name}". Check logs.', 'warning')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/scheduler_status')
@login_required
def scheduler_status():
    """An endpoint to check the status of the background scheduler job."""
    job = scheduler.get_job(SCRAPE_JOB_ID)
    status_data = {
        "scheduler_running": scheduler.running
    }
    if job:
        status_data["job_found"] = True
        status_data["job_id"] = job.id
        status_data["next_run"] = job.next_run_time.isoformat() if job.next_run_time else "N/A"
    else:
        status_data["job_found"] = False
        status_data["job_id"] = SCRAPE_JOB_ID
        status_data["error"] = "Job not found. It may not have been scheduled correctly."

    # Using jsonify will correctly set the Content-Type header to application/json
    return jsonify(status_data)


# --- Public Routes ---
@app.route('/')
def index():
    films = Film.query.order_by(Film.display_name).all()
    return render_template('public/index.html', films=films)

@app.route('/film/<letterboxd_slug>')
def film_detail(letterboxd_slug):
    film = Film.query.filter_by(letterboxd_slug=letterboxd_slug).first_or_404()
    ratings = RatingSnapshot.query.filter_by(film_id=film.id).order_by(RatingSnapshot.timestamp.asc()).all()
    return render_template('public/film_detail.html', film=film, ratings=ratings)

@app.route('/api/film/<letterboxd_slug>/ratings')
def api_film_ratings(letterboxd_slug):
    # Fetch rating history for the film
    film = Film.query.filter_by(letterboxd_slug=letterboxd_slug).first_or_404()
    # Use RatingSnapshot for history
    history = (
        RatingSnapshot.query
        .filter_by(film_id=film.id)
        .order_by(RatingSnapshot.timestamp)
        .all()
    )
    labels = [h.timestamp.isoformat() for h in history]
    avg_ratings = [h.average_rating for h in history]
    rating_counts = [h.rating_count for h in history]
    return jsonify({
        "labels": labels,
        "datasets": [
            {"label": "Average Rating", "data": avg_ratings},
            {"label": "Rating Count", "data": rating_counts}
        ]
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port, debug=True)