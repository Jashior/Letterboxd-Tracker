# app.py
import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_migrate import Migrate
from werkzeug.security import check_password_hash, generate_password_hash # For password hashing
from functools import wraps
import re
import sys
from datetime import datetime
from collections import defaultdict
import logging

from config import Config
from models import db, Film, RatingSnapshot  # Remove FilmRatingHistory
from sqlalchemy import or_
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
    films = Film.query.order_by(Film.display_order.asc()).all()
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

    # Determine the display order for the new film
    max_order = db.session.query(db.func.max(Film.display_order)).scalar() or 0

    new_film = Film(
        letterboxd_slug=slug,
        display_name=scraped_data.get('display_name', slug),
        year=scraped_data.get('year'),
        director=scraped_data.get('director'),
        poster_url=scraped_data.get('poster_url'),
        is_tracked=True, # Default to tracked
        display_order=max_order + 1
    )
    db.session.add(new_film)

    try:
        # Add initial rating snapshot if available
        if 'average_rating' in scraped_data and 'rating_count' in scraped_data:
            new_film.last_known_average_rating = scraped_data['average_rating']
            new_film.last_known_rating_count = scraped_data['rating_count']
            new_film.last_scraped_at = datetime.utcnow()
            
            # The 'film' back-reference on the RatingSnapshot model can be used
            # to associate the two objects before committing. SQLAlchemy handles the foreign key.
            snapshot = RatingSnapshot(
                average_rating=scraped_data['average_rating'],
                rating_count=scraped_data['rating_count'],
                film=new_film # Associate directly with the film object
            )
            db.session.add(snapshot)
            flash(f'Film "{new_film.display_name}" added and initial rating snapshot saved.', 'success')
        else:
            flash(f'Film "{new_film.display_name}" added. No rating data found yet (e.g., unreleased).', 'success')
        
        db.session.commit() # A single commit for the entire transaction
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding film {slug}: {e}")
        flash(f'An error occurred while adding the film "{slug}".', 'danger')

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

@app.route('/admin/film/move/<int:film_id>/<string:direction>', methods=['POST'])
@login_required
def move_film(film_id, direction):
    film_to_move = Film.query.get_or_404(film_id)
    
    if direction == 'up':
        # Find the film with the next lower display_order to swap with
        film_to_swap = Film.query.filter(Film.display_order < film_to_move.display_order).order_by(Film.display_order.desc()).first()
    elif direction == 'down':
        # Find the film with the next higher display_order to swap with
        film_to_swap = Film.query.filter(Film.display_order > film_to_move.display_order).order_by(Film.display_order.asc()).first()
    else:
        flash('Invalid move direction.', 'danger')
        return redirect(url_for('admin_dashboard'))

    if film_to_swap:
        # Swap display order values
        original_order = film_to_move.display_order
        film_to_move.display_order = film_to_swap.display_order
        film_to_swap.display_order = original_order
        db.session.commit()
        flash(f'Adjusted order for "{film_to_move.display_name}".', 'success')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/film/move_to_top/<int:film_id>', methods=['POST'])
@login_required
def move_film_to_top(film_id):
    film = Film.query.get_or_404(film_id)
    # Only consider films in the same group (tracked/archived)
    group_filter = Film.is_tracked == film.is_tracked
    films_in_group = Film.query.filter(group_filter).order_by(Film.display_order.asc()).all()
    if films_in_group and films_in_group[0].id != film.id:
        # Move this film to the top
        for idx, f in enumerate(films_in_group):
            if f.id == film.id:
                continue
            f.display_order = idx + 2  # Shift down
        film.display_order = 1
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/film/move_to_bottom/<int:film_id>', methods=['POST'])
@login_required
def move_film_to_bottom(film_id):
    film = Film.query.get_or_404(film_id)
    group_filter = Film.is_tracked == film.is_tracked
    films_in_group = Film.query.filter(group_filter).order_by(Film.display_order.asc()).all()
    if films_in_group and films_in_group[-1].id != film.id:
        # Move this film to the bottom
        for idx, f in enumerate(films_in_group):
            if f.id == film.id:
                continue
            f.display_order = idx + 1
        film.display_order = len(films_in_group)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))

# Only register the scheduler status route if NOT running in the scheduler process
import os

if not os.environ.get("RUNNING_SCHEDULER_PROCESS"):
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


# --- CLI Commands for data maintenance ---
@app.cli.command("reorder-films")
def reorder_films_command():
    """Resets the display_order for all films based on their addition date."""
    with app.app_context():
        # Order by existing display_order first, then by when they were added.
        # This preserves any manual ordering that might already exist for some films.
        films = Film.query.order_by(Film.display_order.asc(), Film.added_at.asc()).all()
        if not films:
            print("No films found in the database.")
            return

        print(f"Re-ordering {len(films)} films...")
        for index, film in enumerate(films):
            film.display_order = index + 1
        
        try:
            db.session.commit()
            print("Successfully updated display order for all films.")
        except Exception as e:
            db.session.rollback()
            print(f"An error occurred during re-ordering: {e}")

# --- Public Routes ---
@app.route('/')
def index():
    all_films = Film.query.order_by(Film.display_order.asc()).all()
    films_with_data = [f for f in all_films if f.is_tracked and f.last_known_average_rating is not None]
    films_without_data = [f for f in all_films if f.is_tracked and f.last_known_average_rating is None]
    films_archived = [f for f in all_films if not f.is_tracked]
    return render_template(
        'public/index.html',
        films_with_data=films_with_data,
        films_without_data=films_without_data,
        films_archived=films_archived
    )

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


# --- Compare Page and APIs ---
@app.route('/compare')
def compare():
    # Optional prefill of a film via query param
    prefill = request.args.get('prefill', '').strip()
    return render_template('public/compare.html', prefill=prefill)


@app.route('/api/films/search')
def api_films_search():
    query = request.args.get('q', '').strip()
    q = Film.query
    if query:
        like = f"%{query}%"
        q = q.filter(or_(Film.display_name.ilike(like), Film.letterboxd_slug.ilike(like)))
    # Show both tracked and archived, tracked first
    films = (
        q.order_by(Film.is_tracked.desc(), Film.display_order.asc(), Film.display_name.asc())
         .limit(50)
         .all()
    )
    return jsonify([
        {
            "id": f.id,
            "slug": f.letterboxd_slug,
            "name": f.display_name,
            "year": f.year,
            "poster_url": f.poster_url,
            "is_tracked": f.is_tracked,
        }
        for f in films
    ])


@app.route('/api/film_meta')
def api_film_meta():
    slug = request.args.get('slug', '').strip()
    if not slug:
        return jsonify({"error": "slug required"}), 400
    film = Film.query.filter_by(letterboxd_slug=slug).first()
    if not film:
        return jsonify({"error": "not found"}), 404
    return jsonify({
        "id": film.id,
        "slug": film.letterboxd_slug,
        "name": film.display_name,
        "year": film.year,
        "poster_url": film.poster_url,
        "is_tracked": film.is_tracked,
    })


@app.route('/api/compare')
def api_compare():
    # Support multiple films: ?slugs=slug1,slug2,slug3
    slugs_csv = request.args.get('slugs')
    slugs = []
    if slugs_csv:
        slugs = [s.strip() for s in slugs_csv.split(',') if s.strip()]
    else:
        # Backward compatibility: a & b
        a = request.args.get('a')
        b = request.args.get('b')
        if a: slugs.append(a)
        if b: slugs.append(b)

    if not slugs:
        return jsonify({"error": "Provide film slugs via 'slugs' (comma-separated) or 'a'/'b'."}), 400

    films = Film.query.filter(Film.letterboxd_slug.in_(slugs)).all()
    by_slug = {f.letterboxd_slug: f for f in films}
    missing = [s for s in slugs if s not in by_slug]
    if missing:
        return jsonify({"error": f"Films not found: {', '.join(missing)}"}), 404

    film_meta = {}
    datasets = {}
    for s in slugs:
        f = by_slug[s]
        film_meta[s] = {"slug": f.letterboxd_slug, "name": f.display_name, "year": f.year}
        snaps = (
            RatingSnapshot.query
            .filter_by(film_id=f.id)
            .order_by(RatingSnapshot.timestamp.asc())
            .all()
        )
        data_map = {}
        for snap in snaps:
            data_map[snap.rating_count] = snap.average_rating
        datasets[s] = [{"x": x, "y": y} for x, y in sorted(data_map.items())]

    return jsonify({
        "films": film_meta,
        "datasets": datasets,
        "order": slugs,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))  # Default to 5000 if not set
    app.run(host="0.0.0.0", port=port, debug=True)