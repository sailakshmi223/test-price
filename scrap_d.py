from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from urllib.parse import urlparse, parse_qs, urlunparse
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_driver(headless=True):
    """Initialize and configure Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Set realistic user agent
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    options.add_argument(f'user-agent={user_agent}')
    
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--window-size=1920,1080')
    else:
        options.add_argument('--start-maximized')
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver

def clean_url(url):
    """Remove tracking parameters from URLs"""
    if not url:
        return url
    
    try:
        parsed = urlparse(url)
        
        # Domain-specific parameter preservation
        if 'amazon.' in parsed.netloc:
            keep_params = {'dp', 'product'}
        elif 'flipkart.' in parsed.netloc:
            keep_params = {'pid', 'lid'}
        elif 'croma.' in parsed.netloc:
            keep_params = {'p'}
        else:
            keep_params = set()
        
        # Filter query parameters
        query = parse_qs(parsed.query)
        clean_query = {k: v for k, v in query.items() if k in keep_params}
        
        # Rebuild URL
        return urlunparse(
            parsed._replace(
                query='&'.join(f"{k}={v[0]}" for k, v in clean_query.items()),
                fragment=''
            )
        )
    except Exception as e:
        logger.warning(f"URL cleaning failed: {str(e)}")
        return url

def extract_price(price_str):
    """Extract numeric price from string"""
    if not price_str:
        return None
    
    try:
        # Remove all non-numeric characters except decimal point
        cleaned = re.sub(r'[^\d.]', '', price_str)
        
        # Handle different decimal formats
        if ',' in cleaned and '.' in cleaned:
            if cleaned.find(',') < cleaned.find('.'):
                cleaned = cleaned.replace(',', '')  # "1.234,56" -> "1234.56"
            else:
                cleaned = cleaned.replace('.', '').replace(',', '.')  # "1,234.56" -> "1234.56"
        elif ',' in cleaned:
            cleaned = cleaned.replace(',', '')  # "1,234" -> "1234"
        
        return int(float(cleaned)) if cleaned else None
    except (ValueError, AttributeError) as e:
        logger.warning(f"Price extraction failed: {str(e)}")
        return None

def scrape_amazon(driver, url):
    """Specialized Amazon scraper"""
    result = {
        'price': None,
        'name': None,
        'error': None
    }
    
    try:
        logger.info("Scraping Amazon")
        driver.get(url)
        
        # Product name
        try:
            name_element = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "productTitle"))
            )
            result['name'] = name_element.text.strip()
        except TimeoutException:
            pass
        
        # Price - try multiple selectors
        price_selectors = [
            "//span[@class='a-price-whole']",
            "//span[contains(@class, 'priceToPay')]//span[@class='a-offscreen']",
            "//span[contains(@class, 'a-price')]//span[contains(@class, 'a-offscreen')]",
            "//span[contains(@class, 'apexPriceToPay')]//span[contains(@class, 'a-offscreen')]"
        ]
        
        for selector in price_selectors:
            try:
                price_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, selector))
                )
                price_text = price_element.get_attribute("textContent") or price_element.text
                result['price'] = extract_price(price_text)
                if result['price']:
                    break
            except (TimeoutException, NoSuchElementException):
                continue
        
        if not result['price']:
            raise Exception("Could not find price element on Amazon page")
            
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error scraping Amazon: {str(e)}")
    
    return result

def scrape_retailer(driver, url, retailer):
    """Scrape data from a single retailer (Flipkart or Croma)"""
    if retailer == 'amazon':
        return scrape_amazon(driver, url)
        
    result = {
        'price': None,
        'name': None,
        'error': None
    }
    
    try:
        logger.info(f"Scraping {retailer}")
        driver.get(url)
        
        # Product name selectors
        name_selectors = {
            'flipkart': [
                (By.CLASS_NAME, "B_NuCI"),
                (By.CSS_SELECTOR, "h1 span")
            ],
            'croma': [
                (By.CLASS_NAME, "pdp-product-title"),
                (By.TAG_NAME, "h1")
            ]
        }
        
        # Price selectors
        price_selectors = {
            'flipkart': "//div[contains(@class, '_30jeq3') or contains(text(),'₹')]",
            'croma': "//span[contains(@class, 'amount') or contains(@class, 'price')]"
        }
        
        # Get product name
        for by, value in name_selectors[retailer]:
            try:
                element = driver.find_element(by, value)
                result['name'] = element.text.strip()
                if result['name']:
                    break
            except NoSuchElementException:
                continue
        
        # Get product price
        price_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, price_selectors[retailer]))
        )
        result['price'] = extract_price(price_element.text)
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error scraping {retailer}: {str(e)}")
    
    return result

def scrape_product_data(driver, amazon_url, flipkart_url, croma_url):
    """Scrape product data from all retailers"""
    results = {
        'amazon': scrape_retailer(driver, amazon_url, 'amazon'),
        'flipkart': scrape_retailer(driver, flipkart_url, 'flipkart'),
        'croma': scrape_retailer(driver, croma_url, 'croma')
    }
    
    # Determine the most reliable product name
    product_name = (
        results['flipkart']['name'] or 
        results['amazon']['name'] or 
        results['croma']['name'] or 
        "Unknown Product"
    )[:500]  # Truncate to DB column length
    
    # Extract prices
    prices = {
        'amazon': results['amazon']['price'],
        'flipkart': results['flipkart']['price'],
        'croma': results['croma']['price']
    }
    
    # Prepare history entry
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    history = {
        'timestamp': timestamp,
        'prices': prices,
        'product_name': product_name
    }
    
    return product_name, prices, history