# scheduler.py
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
import logging
import time
from random import randint

from app import app # Import app for context
from models import db, Film, RatingSnapshot
from scraper import get_film_data

logger = logging.getLogger(__name__)
scheduler = APScheduler()

SCRAPE_JOB_ID = "scrape_letterboxd_ratings"

def run_scrape_job_for_film(film_id):
    """Scrapes a single film and updates the database. Returns True on success, False on failure."""
    with app.app_context(): # Need app context for db operations
        film = Film.query.get(film_id)
        if not film:
            logger.error(f"Film with ID {film_id} not found for scraping.")
            return False

        logger.info(f"Scraping data for: {film.display_name} ({film.letterboxd_slug})")
        scraped_data = get_film_data(film.letterboxd_slug)

        if scraped_data:
            # Update film metadata if it changed (e.g. director added later)
            film.display_name = scraped_data.get('display_name', film.display_name)
            film.year = scraped_data.get('year', film.year)
            film.director = scraped_data.get('director', film.director)
            film.poster_url = scraped_data.get('poster_url', film.poster_url)
            
            if 'average_rating' in scraped_data and 'rating_count' in scraped_data:
                avg_rating = scraped_data['average_rating']
                rating_count = scraped_data['rating_count']

                # Check if rating actually changed to avoid redundant snapshots
                # Or if it's the first scrape for this info
                if (film.last_known_average_rating != avg_rating or
                    film.last_known_rating_count != rating_count or
                    film.last_scraped_at is None): # Always save if first scrape or data changed

                    snapshot = RatingSnapshot(
                        film_id=film.id,
                        average_rating=avg_rating,
                        rating_count=rating_count,
                        timestamp=datetime.utcnow()
                    )
                    db.session.add(snapshot)
                    logger.info(f"New rating snapshot for {film.display_name}: {avg_rating} ({rating_count} ratings)")
                else:
                    logger.info(f"Rating for {film.display_name} unchanged: {avg_rating} ({rating_count} ratings). Skipping snapshot.")

                film.last_known_average_rating = avg_rating
                film.last_known_rating_count = rating_count
                film.last_scraped_at = datetime.utcnow()
                db.session.commit()
                return True
            else:
                # Film exists, but no rating data (e.g., unreleased)
                # We still update last_scraped_at to know we checked
                film.last_scraped_at = datetime.utcnow()
                db.session.commit()
                logger.info(f"No rating data found for {film.display_name} (possibly unreleased). Metadata updated if changed.")
                return True # Success in terms of processing, even if no rating
        else:
            logger.warning(f"Failed to scrape data for {film.display_name}")
            # Optionally update film.last_scraped_at here too, to indicate an attempt was made
            film.last_scraped_at = datetime.utcnow() # Mark as attempted
            db.session.commit()
            return False

def scheduled_scrape_task():
    logger.info("Scheduler starting scrape task...")
    with app.app_context(): # Crucial for database access within the scheduled job
        films_to_track = Film.query.filter_by(is_tracked=True).all()
        if not films_to_track:
            logger.info("No films are currently marked for tracking.")
            return

        for film in films_to_track:
            run_scrape_job_for_film(film.id)
            # Polite delay between requests to avoid overwhelming Letterboxd
            # Random delay to make it less predictable
            delay = randint(5, 15) # seconds
            logger.info(f"Waiting {delay} seconds before next film...")
            time.sleep(delay)
    logger.info("Scheduler finished scrape task.")

def init_scheduler(current_app):
    if not scheduler.running:
        scheduler.init_app(current_app)
        scheduler.start()
        logger.info("APScheduler initialized and started.")

        # Check if job already exists to prevent duplicates on app restart
        if not scheduler.get_job(SCRAPE_JOB_ID):
            interval_minutes = current_app.config.get('SCHEDULER_INTERVAL_MINUTES', 60)
            scheduler.add_job(
                id=SCRAPE_JOB_ID,
                func=scheduled_scrape_task,
                trigger='interval',
                minutes=interval_minutes,
                next_run_time=datetime.now() + timedelta(seconds=10) # Start 10s after app start
            )
            logger.info(f"Scheduled scrape job to run every {interval_minutes} minutes.")
        else:
            logger.info("Scrape job already exists.")
    else:
        logger.info("APScheduler already running.")