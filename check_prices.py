import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import logging
from db_d import get_db, update_product_prices
from scrap_f import scrape_product_data,init_driver
from notify_c import DiscordNotifier
from db_d import Product

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PRICE_DROP_THRESHOLD = 0.05  # 5% minimum drop to alert
MIN_ABSOLUTE_DROP = 500      # ₹500 minimum absolute drop
MAX_HISTORY_DAYS = 30        # Only compare prices from last 30 days
ALERT_COOLDOWN_HOURS = 24    # Don't re-alert for same product within 24h

class PriceMonitor:
    def __init__(self):
        load_dotenv()
        self.notifier = DiscordNotifier()
        self.last_alert_times: Dict[str, datetime] = {}
        self.driver = init_driver(headless=True) 

    def is_significant_drop(self, current: float, previous: float) -> bool:
        """Check if price drop meets both percentage and absolute thresholds"""
        drop_amount = previous - current
        percentage_drop = drop_amount / previous
        
        absolute_ok = drop_amount >= MIN_ABSOLUTE_DROP
        percentage_ok = percentage_drop >= PRICE_DROP_THRESHOLD
        
        return absolute_ok and percentage_ok

    def should_alert(self, product_url: str) -> bool:
        """Check if we should send alert (cooldown period)"""
        last_alert = self.last_alert_times.get(product_url)
        if not last_alert:
            return True
        return (datetime.now() - last_alert) > timedelta(hours=ALERT_COOLDOWN_HOURS)

    async def check_product(self, product_url: str) -> None:
        """Check price for a single product"""
        db_session = next(get_db())
        try:
            product = db_session.query(Product).filter(Product.url == product_url).first()
            if not product or not product.price_history:
                logger.info(f"No history found for {product_url}")
                return

            latest_price = product.price_history[-1]['value']
            
            # Fixed scraper call
            scraped_data = scrape_product_data(
                driver=self.driver,  # Add this line
                amazon_url=product_url if 'amazon.' in product_url else None,
                flipkart_url=product_url if 'flipkart.' in product_url else None,
                croma_url=product_url if 'croma.' in product_url else None
            )
            
            if not scraped_data or 'price' not in scraped_data:
                logger.warning(f"Failed to scrape {product_url}")
                return

            current_price = scraped_data['price']
            update_product_prices(
                db_session,
                product_url,
                {'value': current_price, 'currency': 'INR'}
            )

            if self.is_significant_drop(current_price, latest_price):
                if self.should_alert(product_url):
                    await self.notifier.send_alert(
                        product_name=scraped_data.get('name', 'Unknown Product'),
                        old_price=latest_price,
                        new_price=current_price,
                        url=product_url,
                        retailer=scraped_data.get('retailer', 'unknown')
                    )
                    self.last_alert_times[product_url] = datetime.now()

        except Exception as e:
            logger.error(f"Error checking {product_url}: {str(e)}")
        finally:
            db_session.close()

    async def check_all_products(self) -> None:
        """Check prices for all tracked products"""
        db_session = next(get_db())
        try:
            products = db_session.query(Product).all()
            if not products:
                logger.info("No products found in database")
                return

            for product in products:
                await self.check_product(product.url)

        except Exception as e:
            logger.error(f"Fatal error in price check: {str(e)}")
        finally:
            db_session.close()
            await self.notifier.close()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up resources"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()
        await self.notifier.close()

async def main():
    monitor = PriceMonitor()
    await monitor.check_all_products()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())