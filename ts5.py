from scrap_d import init_driver, scrape_product_data
from db_d import get_db, add_product_to_db
import logging
import time
from urllib.parse import urlparse, parse_qs, urlunparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)
logger = logging.getLogger(__name__)

def clean_url(url):
    """Remove tracking parameters from URLs"""
    if not url:
        return url
    
    try:
        parsed = urlparse(url)
        
        if 'amazon.' in parsed.netloc:
            keep_params = {'dp', 'product'}
        elif 'flipkart.' in parsed.netloc:
            keep_params = {'pid', 'lid'}
        else:
            keep_params = set()
        
        query = parse_qs(parsed.query)
        clean_query = {k: v for k, v in query.items() if k in keep_params}
        
        return urlunparse(
            parsed._replace(
                query='&'.join(f"{k}={v[0]}" for k, v in clean_query.items()),
                fragment=''
            )
        )
    except Exception as e:
        logger.warning(f"URL cleaning failed: {str(e)}")
        return url

# Product URLs
urls = {
    'amazon': clean_url("https://www.amazon.in/iPhone-16-128-GB-Control/dp/B0DGJHBX5Y"),
    'flipkart': clean_url("https://www.flipkart.com/apple-iphone-14-pro-deep-purple-128-gb/p/itm75f73f63239fa"),
    'croma': clean_url("https://www.croma.com/apple-iphone-16-pro-max-256gb-black-titanium-/p/309742")
}

def main():
    driver = None
    try:
        logger.info("Initializing Chrome driver")
        driver = init_driver(headless=True)
        
        logger.info("Connecting to database")
        db = next(get_db())

        logger.info("Starting scraping process")
        
        # Scrape data from all retailers
        name, prices, history = scrape_product_data(driver, 
                                                  urls['amazon'], 
                                                  urls['flipkart'], 
                                                  urls['croma'])
        
        logger.info(f"Scraped product: {name}")
        logger.info(f"Prices: {prices}")

        # Save each retailer's data separately
        for retailer in ['amazon', 'flipkart', 'croma']:
            if prices.get(retailer) is not None:
                logger.info(f"Processing {retailer} data")
                
                # Prepare retailer-specific data
                price_data = {
                    "value": prices[retailer],
                    "currency": "INR",
                    "timestamp": time.strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Add to database
                product = add_product_to_db(
                    db,
                    url=urls[retailer],
                    retailer=retailer,
                    latest_prices=price_data,
                    price_history=[price_data]  # Initial history entry
                )
                
                if product:
                    logger.info(f"Added {retailer} product (ID: {product.product_id})")
                else:
                    logger.error(f"Failed to add {retailer} product")
            
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
    finally:
        if driver:
            logger.info("Closing browser driver")
            driver.quit()
        logger.info("Scraping process completed")

if __name__ == "__main__":
    main()