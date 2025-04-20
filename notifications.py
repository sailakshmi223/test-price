from dotenv import load_dotenv
import os
import aiohttp
import asyncio
import logging
from typing import Optional, Dict, Any
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

class PriceAlert:
    """Handles price drop notifications and alerts"""
    
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.min_drop_percentage = float(os.getenv("MIN_DROP_PERCENTAGE", "5.0"))
        self.session = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def _clean_url(self, url: str) -> str:
        """Clean URL for display purposes"""
        if not url:
            return url
        parsed = urlparse(url)
        return f"{parsed.netloc}{parsed.path}"
    
    def _calculate_drop(self, old_price: float, new_price: float) -> float:
        """Calculate price drop percentage"""
        if not old_price or not new_price or old_price <= 0:
            return 0.0
        return ((old_price - new_price) / old_price) * 100
    
    async def send_discord_alert(
        self,
        product_name: str,
        old_price: float,
        new_price: float,
        url: str,
        retailer: str,
        currency: str = "₹"
    ) -> bool:
        """
        Send price drop alert to Discord
        Returns True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("No Discord webhook URL configured")
            return False
            
        drop_percentage = self._calculate_drop(old_price, new_price)
        
        if drop_percentage < self.min_drop_percentage:
            logger.info(f"Price drop {drop_percentage:.1f}% below threshold {self.min_drop_percentage}% - not sending alert")
            return False
        
        clean_url = self._clean_url(url)
        price_format = f"{currency}{new_price:,.2f}"
        old_price_format = f"{currency}{old_price:,.2f}"
        
        message = {
            "embeds": [
                {
                    "title": f"💰 Price Drop Alert! ({retailer.upper()})",
                    "description": (
                        f"**{product_name[:200]}**\n\n"
                        f"🔻 **{drop_percentage:.1f}%** price drop!\n"
                        f"📉 Old price: {old_price_format}\n"
                        f"📈 New price: **{price_format}**\n"
                        f"🛒 [View Product]({url})"
                    ),
                    "color": 3066993,  # Green color
                    "footer": {
                        "text": f"Tracked from {clean_url}"
                    },
                    "thumbnail": {
                        "url": self._get_retailer_icon(retailer)
                    }
                }
            ]
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=message) as response:
                    if response.status == 204:
                        logger.info(f"Successfully sent Discord alert for {product_name}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to send Discord alert. Status: {response.status}, Error: {error_text}"
                        )
                        return False
        except Exception as e:
            logger.error(f"Error sending Discord notification: {str(e)}")
            return False
    
    def _get_retailer_icon(self, retailer: str) -> str:
        """Get retailer icon URL for Discord embed"""
        icons = {
            "amazon": "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a9/Amazon_logo.svg/1024px-Amazon_logo.svg.png",
            "flipkart": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Flipkart_logo.png/800px-Flipkart_logo.png",
            "croma": "https://www.croma.com/assets/images/croma-logo.png"
        }
        return icons.get(retailer.lower(), "")
    
    async def check_and_notify(
        self,
        product_name: str,
        current_prices: Dict[str, Optional[float]],
        previous_prices: Dict[str, Optional[float]],
        product_urls: Dict[str, str]
    ) -> None:
        """
        Check for price drops across all retailers and send notifications
        """
        tasks = []
        for retailer in current_prices:
            current_price = current_prices.get(retailer)
            previous_price = previous_prices.get(retailer)
            url = product_urls.get(retailer)
            
            if current_price and previous_price and url:
                tasks.append(
                    self.send_discord_alert(
                        product_name=product_name,
                        old_price=previous_price,
                        new_price=current_price,
                        url=url,
                        retailer=retailer
                    )
                )
        
        if tasks:
            await asyncio.gather(*tasks)

# Example usage
async def example_usage():
    async with PriceAlert() as alert:
        await alert.send_discord_alert(
            product_name="Apple iPhone 14 Pro (128GB)",
            old_price=129900,
            new_price=119900,
            url="https://www.flipkart.com/apple-iphone-14-pro-deep-purple-128-gb/p/itm75f73f63239fa",
            retailer="flipkart"
        )

if __name__ == "__main__":
    asyncio.run(example_usage())