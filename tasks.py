# tasks.py
import logging
from datetime import datetime
from random import randint
import time

from models import db, Film, RatingSnapshot
from scraper import get_film_data

logger = logging.getLogger(__name__)

def run_scrape_job_for_film(film_id):
    """Scrapes a single film and updates the database. Returns True on success, False on failure."""
    # This function is executed within an application context provided by
    # Flask-APScheduler (for scheduled jobs) or a Flask view (for manual triggers).
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
            if (film.last_known_average_rating != avg_rating or
                film.last_known_rating_count != rating_count or
                film.last_scraped_at is None):

                snapshot = RatingSnapshot(
                    film_id=film.id,
                    average_rating=avg_rating,
                    rating_count=rating_count,
                    timestamp=datetime.utcnow()
                )
                db.session.add(snapshot)
                logger.info(f"New rating snapshot for {film.display_name}: {avg_rating} ({rating_count} ratings)")
            else:
                logger.info(f"Rating for {film.display_name} unchanged. Skipping snapshot.")

            film.last_known_average_rating = avg_rating
            film.last_known_rating_count = rating_count
        
        film.last_scraped_at = datetime.utcnow()
        db.session.commit()
        return True
    else:
        logger.warning(f"Failed to scrape data for {film.display_name}")
        film.last_scraped_at = datetime.utcnow() # Mark as attempted
        db.session.commit()
        return False

def scheduled_scrape_task():
    logger.info("Scheduled task triggered")
    logger.info("Scheduler starting scrape task...")
    # This function is run by APScheduler and will have an app context automatically.
    # Structured log for timing
    logger.info(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    films_to_track = Film.query.filter_by(is_tracked=True).all()
    if not films_to_track:
        logger.info("No films are currently marked for tracking.")
        return

    logger.info(f"Found {len(films_to_track)} films to scrape")
    for film in films_to_track:
        logger.debug(f"Queued: {film.display_name}")
    
    for film in films_to_track:
        logger.info(f"Scraping: {film.display_name}")
        run_scrape_job_for_film(film.id)
        delay = randint(5, 15) # Polite delay between requests
        logger.info(f"Waiting {delay} seconds before next film...")
        time.sleep(delay)
    logger.info("Scheduler finished scrape task.")
    logger.info(">>> SCHEDULED TASK COMPLETED <<<")