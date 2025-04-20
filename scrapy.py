from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import re
from urllib.parse import urlparse, parse_qs, urlunparse

def init_driver(headless=False):
    """Initialize and configure the Chrome WebDriver"""
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--disable-extensions')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    # Set user agent to mimic a real browser
    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    options.add_argument(f'user-agent={user_agent}')
    
    if headless:
        options.add_argument('--headless=new')
    
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    driver.implicitly_wait(5)
    return driver

def clean_url(url):
    """Remove tracking parameters from URLs"""
    if not url:
        return url
    
    try:
        # Parse the URL
        parsed = urlparse(url)
        
        # Keep only essential query parameters
        if parsed.netloc.endswith('amazon.in'):
            keep_params = {'dp', 'product'}
            query = {k: v for k, v in parse_qs(parsed.query).items() if k in keep_params}
        elif parsed.netloc.endswith('flipkart.com'):
            keep_params = {'pid', 'lid'}
            query = {k: v for k, v in parse_qs(parsed.query).items() if k in keep_params}
        else:
            query = {}
        
        # Rebuild the URL
        cleaned = parsed._replace(query='&'.join(f"{k}={v[0]}" for k, v in query.items()))
        return urlunparse(cleaned)
    except Exception:
        return url  # Return original if cleaning fails

def extract_price(price_str):
    """Extract numeric price from string"""
    if not price_str:
        return None
    
    try:
        # Remove all non-numeric characters except commas and dots
        cleaned = re.sub(r'[^\d.,]', '', price_str)
        # Remove thousands separators
        cleaned = cleaned.replace(',', '')
        # Handle decimal prices (take integer part)
        if '.' in cleaned:
            cleaned = cleaned.split('.')[0]
        return int(cleaned) if cleaned else None
    except (ValueError, AttributeError):
        return None

def scrape_product_data(driver, amazon_url, flipkart_url, croma_url):
    """Scrape product data from e-commerce websites"""
    product_name = ""
    latest_prices = {
        "amazon": None,
        "flipkart": None,
        "croma": None
    }
    
    # Clean URLs before use
    amazon_url = clean_url(amazon_url)
    flipkart_url = clean_url(flipkart_url)
    croma_url = clean_url(croma_url)
    
    wait = WebDriverWait(driver, 15)
    
    # Common function to get product name
    def get_product_name():
        nonlocal product_name
        if product_name:
            return product_name
            
        name_selectors = [
            # Flipkart
            {"url": flipkart_url, "selectors": [
                (By.CLASS_NAME, "B_NuCI"),
                (By.CSS_SELECTOR, "h1 span"),
                (By.XPATH, "//h1/span")
            ]},
            # Amazon
            {"url": amazon_url, "selectors": [
                (By.ID, "productTitle"),
                (By.CSS_SELECTOR, "h1 span#productTitle"),
                (By.XPATH, "//span[@id='productTitle']")
            ]},
            # Croma
            {"url": croma_url, "selectors": [
                (By.CLASS_NAME, "pdp-product-title"),
                (By.TAG_NAME, "h1"),
                (By.XPATH, "//h1[contains(@class, 'product-title')]")
            ]}
        ]
        
        for source in name_selectors:
            if not product_name and source["url"]:
                try:
                    driver.get(source["url"])
                    for by, value in source["selectors"]:
                        try:
                            element = driver.find_element(by, value)
                            product_name = element.text.strip()
                            if product_name:
                                return product_name
                        except NoSuchElementException:
                            continue
                except Exception as e:
                    print(f"Error getting name from {source['url']}: {str(e)}")
        return product_name
    
    # Flipkart scraping
    if flipkart_url:
        try:
            print("[+] Scraping Flipkart")
            driver.get(flipkart_url)
            get_product_name()  # Try to get name if not already found
            
            # Price element
            price_element = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//div[contains(@class, '_30jeq3') or contains(text(),'₹')]")
            ))
            flipkart_price = extract_price(price_element.text)
            latest_prices["flipkart"] = flipkart_price
        except Exception as e:
            print(f"Flipkart scraping error: {str(e)}")

    # Amazon scraping
    if amazon_url:
        try:
            print("[+] Scraping Amazon")
            driver.get(amazon_url)
            get_product_name()  # Try to get name if not already found
            
            # Price element (multiple possible selectors)
            price_element = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//span[@class='a-price-whole'] | //span[contains(@class, 'priceToPay')]//span[@class='a-offscreen']")
            ))
            amazon_price = extract_price(price_element.get_attribute("textContent") or price_element.text)
            latest_prices["amazon"] = amazon_price
        except Exception as e:
            print(f"Amazon scraping error: {str(e)}")

    # Croma scraping
    if croma_url:
        try:
            print("[+] Scraping Croma")
            driver.get(croma_url)
            get_product_name()  # Try to get name if not already found
            
            # Price element
            price_element = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//span[contains(@class, 'amount') or contains(@class, 'price')]")
            ))
            croma_price = extract_price(price_element.text)
            latest_prices["croma"] = croma_price
        except Exception as e:
            print(f"Croma scraping error: {str(e)}")

    # Final attempt to get product name if still not found
    if not product_name:
        product_name = get_product_name() or "Unknown Product"

    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    history = [{"timestamp": timestamp, **latest_prices}]

    return product_name[:500], latest_prices, history  # Truncate name if too long