# scraper.py
import requests
from bs4 import BeautifulSoup
import re
import logging
import json # For parsing JSON-LD

# The logger instance will be configured by Flask when app.py runs
# For standalone testing (if __name__ == '__main__'), basicConfig would be used.
logger = logging.getLogger(__name__)

def get_film_data(letterboxd_slug):
    target_url = f"https://letterboxd.com/film/{letterboxd_slug}/"
    # Reduced logging for normal operation, more can be added if debugging again
    logger.info(f"Attempting to scrape: {target_url}")

    headers = {
        'User-Agent': 'LetterboxdRatingTracker/1.0 (YourName; YourContactInfo; For personal project monitoring film ratings)'
    }
    
    try:
        response = requests.get(target_url, headers=headers, timeout=15) # Increased timeout slightly
        # logger.debug(f"Response status code for {target_url}: {response.status_code}") # Changed to DEBUG
        response.raise_for_status()
        
        html_content = response.text
        soup = BeautifulSoup(html_content, 'html.parser')
        data = {"letterboxd_slug": letterboxd_slug}

        # --- Metadata Parsing ---
        name_tag = soup.select_one("h1.headline-1.primaryname span.name")
        if name_tag:
            data['display_name'] = name_tag.text.strip()
        else: # Fallback
            title_tag = soup.find('meta', property='og:title')
            if title_tag and title_tag.get('content'):
                name_from_meta = title_tag['content']
                name_from_meta = re.sub(r'\s*\(\d{4}\)$', '', name_from_meta)
                name_from_meta = name_from_meta.replace(' - Letterboxd', '').strip()
                data['display_name'] = name_from_meta
            else:
                logger.warning(f"Could not find display name for {letterboxd_slug}")
                data['display_name'] = letterboxd_slug # Fallback to slug
        # logger.debug(f"Parsed display_name: {data.get('display_name')}") # DEBUG level

        year_tag = soup.select_one(".productioninfo .releasedate a")
        if year_tag and year_tag.text.isdigit():
            data['year'] = int(year_tag.text)
        else: # Fallback for year
            title_tag_content = soup.find('meta', property='og:title')['content'] if soup.find('meta', property='og:title') else ""
            year_match = re.search(r'\((\d{4})\)$', title_tag_content)
            if year_match:
                data['year'] = int(year_match.group(1))
        # logger.debug(f"Parsed year: {data.get('year')}") # DEBUG level

        director_tag = soup.select_one(".productioninfo .credits .creatorlist a.contributor span.prettify")
        if director_tag:
            data['director'] = director_tag.text.strip()
        # logger.debug(f"Parsed director: {data.get('director')}") # DEBUG level

        poster_meta_tag = soup.find('meta', property='og:image')
        if poster_meta_tag and poster_meta_tag.get('content'):
            data['poster_url'] = poster_meta_tag['content']
        # logger.debug(f"Parsed poster_url: {data.get('poster_url')}") # DEBUG level
        # --- End Metadata Parsing ---

        # --- Rating Parsing ---
        avg_rating_anchor = soup.select_one('span.average-rating a.display-rating')
        parsed_from_primary = False

        if avg_rating_anchor and avg_rating_anchor.has_attr('data-original-title'):
            # logger.debug(f"PRIMARY: RATING ANCHOR FOUND for {letterboxd_slug}") # DEBUG
            title_text = avg_rating_anchor['data-original-title']
            # logger.debug(f"PRIMARY: RATING TOOLTIP TEXT: '{title_text}'") # DEBUG
            
            avg_rating_match = re.search(r'Weighted average of ([\d\.]+)', title_text)
            rating_count_match = re.search(r'based on ([\d,]+) ratings', title_text)

            if avg_rating_match:
                data['average_rating'] = float(avg_rating_match.group(1))
                # logger.info(f"PRIMARY: Parsed average_rating: {data['average_rating']}") # INFO if you want to see it often
                parsed_from_primary = True
            else:
                logger.warning(f"PRIMARY: Could not parse average_rating from tooltip for {letterboxd_slug}: '{title_text}'")

            if rating_count_match:
                data['rating_count'] = int(rating_count_match.group(1).replace(',', ''))
                # logger.info(f"PRIMARY: Parsed rating_count: {data['rating_count']}") # INFO
            else:
                logger.warning(f"PRIMARY: Could not parse rating_count from tooltip for {letterboxd_slug}: '{title_text}'")
        else:
            logger.info(f"PRIMARY: Visual rating anchor not found for {letterboxd_slug}. Will attempt fallback.")

        if not parsed_from_primary or 'rating_count' not in data or 'average_rating' not in data:
            logger.info(f"FALLBACK: Attempting to parse rating from meta/JSON-LD for {letterboxd_slug}.")
            
            if 'average_rating' not in data:
                twitter_rating_meta = soup.find('meta', attrs={'name': 'twitter:data2'})
                if twitter_rating_meta and twitter_rating_meta.get('content'):
                    rating_match = re.search(r'([\d\.]+)\s+out\s+of\s+5', twitter_rating_meta['content'])
                    if rating_match:
                        data['average_rating'] = float(rating_match.group(1))
                        # logger.info(f"FALLBACK: Parsed average_rating: {data['average_rating']}")
                    else:
                        logger.warning(f"FALLBACK: Could not parse average_rating from twitter:data2 for {letterboxd_slug}: {twitter_rating_meta['content']}")
                else:
                    logger.warning(f"FALLBACK: twitter:data2 meta tag for rating not found for {letterboxd_slug}.")

            if 'rating_count' not in data:
                script_tag_ld_json = soup.find('script', type='application/ld+json')
                if script_tag_ld_json:
                    script_content = script_tag_ld_json.string
                    if script_content:
                        json_start_index = script_content.find('{')
                        json_end_index = script_content.rfind('}')
                        if json_start_index != -1 and json_end_index != -1 and json_end_index > json_start_index:
                            json_string_to_parse = script_content[json_start_index : json_end_index+1]
                            try:
                                json_ld_data = json.loads(json_string_to_parse)
                                if 'aggregateRating' in json_ld_data and 'ratingCount' in json_ld_data['aggregateRating']:
                                    data['rating_count'] = int(json_ld_data['aggregateRating']['ratingCount'])
                                    # logger.info(f"FALLBACK: Parsed rating_count: {data['rating_count']}")
                                else:
                                    logger.warning(f"FALLBACK: 'ratingCount' not found in JSON-LD for {letterboxd_slug}.")
                            except json.JSONDecodeError as e:
                                logger.warning(f"FALLBACK: Could not parse JSON-LD for {letterboxd_slug}. Error: {e}.")
                        else:
                            logger.warning(f"FALLBACK: Could not find valid JSON object in JSON-LD script for {letterboxd_slug}.")
                    else:
                        logger.warning(f"FALLBACK: JSON-LD script tag content empty for {letterboxd_slug}.")
                else:
                    logger.warning(f"FALLBACK: JSON-LD script tag not found for {letterboxd_slug}.")
        
        if 'average_rating' not in data:
             logger.warning(f"FINAL: average_rating could not be determined for {letterboxd_slug}.")
        if 'rating_count' not in data:
             logger.warning(f"FINAL: rating_count could not be determined for {letterboxd_slug}.")
        # --- End Rating Parsing ---
        
        if 'average_rating' in data and 'rating_count' in data:
            logger.info(f"Successfully scraped rating for {data.get('display_name', letterboxd_slug)}: {data['average_rating']} ({data['rating_count']} ratings)")
        elif 'average_rating' in data: # Has rating but not count (should be rare with current logic)
            logger.info(f"Successfully scraped average rating for {data.get('display_name', letterboxd_slug)}: {data['average_rating']} (rating count MISSING)")
        else: # No rating info at all
            logger.info(f"No rating data found for {data.get('display_name', letterboxd_slug)} after all attempts.")


        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"RequestException for URL '{target_url}': {e}")
        return None
    except Exception as e:
        logger.error(f"General Exception during parsing for URL '{target_url}': {e}", exc_info=True) # exc_info=True is good for full trace in logs
        return None

if __name__ == '__main__':
    # This block is for direct testing of scraper.py.
    # Flask app will configure its own root logger.
    logging.basicConfig(
        level=logging.DEBUG, # Set to DEBUG for standalone testing to see more detail
        format='%(asctime)s - %(levelname)s - %(name)s - %(module)s - %(funcName)s - %(lineno)d - %(message)s'
    )
    
    slug_to_test = "28-years-later"
    # slug_to_test = "dune-part-two" 
    # slug_to_test = "a-film-that-does-not-exist-for-sure" # Test a 404

    print(f"--- TESTING SCRAPER STANDALONE WITH SLUG: {slug_to_test} ---")
    scraped_data = get_film_data(slug_to_test)

    if scraped_data:
        print(f"--- SCRAPED DATA for {slug_to_test}: ---")
        for key, value in scraped_data.items():
            print(f"  {key}: {value}")
    else:
        print(f"--- FAILED to retrieve or parse data for {slug_to_test} ---")