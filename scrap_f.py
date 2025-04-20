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
from typing import Dict, Optional, Any

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
        'retailer': 'amazon',
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

def scrape_flipkart(driver, url):
    """Specialized Flipkart scraper"""
    result = {
        'price': None,
        'name': None,
        'retailer': 'flipkart',
        'error': None
    }
    
    try:
        logger.info("Scraping Flipkart")
        driver.get(url)
        
        # Product name
        name_selectors = [
            (By.CLASS_NAME, "B_NuCI"),
            (By.CSS_SELECTOR, "h1 span")
        ]
        
        for by, value in name_selectors:
            try:
                element = driver.find_element(by, value)
                result['name'] = element.text.strip()
                if result['name']:
                    break
            except NoSuchElementException:
                continue
        
        # Product price
        price_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//div[contains(@class, '_30jeq3') or contains(text(),'₹')]"))
        )
        result['price'] = extract_price(price_element.text)
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error scraping Flipkart: {str(e)}")
    
    return result

def scrape_croma(driver, url):
    """Specialized Croma scraper"""
    result = {
        'price': None,
        'name': None,
        'retailer': 'croma',
        'error': None
    }
    
    try:
        logger.info("Scraping Croma")
        driver.get(url)
        
        # Product name
        name_selectors = [
            (By.CLASS_NAME, "pdp-product-title"),
            (By.TAG_NAME, "h1")
        ]
        
        for by, value in name_selectors:
            try:
                element = driver.find_element(by, value)
                result['name'] = element.text.strip()
                if result['name']:
                    break
            except NoSuchElementException:
                continue
        
        # Product price
        price_element = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(@class, 'amount') or contains(@class, 'price')]"))
        )
        result['price'] = extract_price(price_element.text)
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error scraping Croma: {str(e)}")
    
    return result

def scrape_product_data(
    driver,
    amazon_url: Optional[str] = None,
    flipkart_url: Optional[str] = None,
    croma_url: Optional[str] = None
) -> Dict[str, Any]:
    """Scrape product data from available retailer URLs"""
    result = {
        'price': None,
        'name': None,
        'retailer': None,
        'error': None
    }
    
    try:
        if amazon_url:
            amazon_result = scrape_amazon(driver, amazon_url)
            if amazon_result['price']:
                return amazon_result
        
        if flipkart_url:
            flipkart_result = scrape_flipkart(driver, flipkart_url)
            if flipkart_result['price']:
                return flipkart_result
                
        if croma_url:
            croma_result = scrape_croma(driver, croma_url)
            if croma_result['price']:
                return croma_result
                
        raise Exception("No valid retailer URL provided or failed to scrape all")
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Error in scrape_product_data: {str(e)}")
    
    return result