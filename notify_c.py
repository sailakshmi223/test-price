import aiohttp
import asyncio
import os
from dotenv import load_dotenv
import logging
import platform
from typing import Optional, Dict
from urllib.parse import urlparse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Windows-specific setup
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

class DiscordNotifier:
    def __init__(self):
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
        self.min_drop = float(os.getenv("MIN_DROP_PERCENTAGE", 5.0))
        self.session = None
        self.retailer_icons = {
            'amazon': 'https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg',
            'flipkart': 'https://upload.wikimedia.org/wikipedia/commons/2/2f/Flipkart_logo.png',
            'croma': 'https://www.croma.com/assets/images/croma-logo.png'
        }

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'session') and self.session and not self.session.closed:
            await self.session.close()

    def _clean_url(self, url: str) -> str:
        """Extract clean domain for display"""
        parsed = urlparse(url)
        return parsed.netloc.replace('www.', '')

    async def send_alert(
        self,
        product_name: str,
        old_price: float,
        new_price: float,
        url: str,
        retailer: str
    ) -> bool:
        """Send price drop alert to Discord"""
        if not self.webhook_url:
            logger.warning("No Discord webhook URL configured")
            return False

        try:
            drop_pct = ((old_price - new_price) / old_price) * 100
            if drop_pct < self.min_drop:
                logger.info(f"Price drop {drop_pct:.1f}% below threshold {self.min_drop}%")
                return False

            # Build the Discord message embed
            message = {
                "embeds": [{
                    "title": f"💰 Price Drop Alert! ({retailer.upper()})",
                    "description": (
                        f"**{product_name[:200]}**\n\n"
                        f"🔻 **{drop_pct:.1f}%** price drop!\n"
                        f"📉 Old price: ₹{old_price:,.2f}\n"
                        f"📈 New price: **₹{new_price:,.2f}**\n"
                        f"🛒 [View Product]({url})"
                    ),
                    "color": 3066993,  # Green color
                    "thumbnail": {"url": self.retailer_icons.get(retailer.lower(), "")},
                    "footer": {
                        "text": f"Tracked from {self._clean_url(url)}",
                        "icon_url": "https://cdn-icons-png.flaticon.com/512/2821/2821637.png"
                    }
                }]
            }

            # Initialize session if not exists
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()

            # Send the notification
            async with self.session.post(self.webhook_url, json=message) as response:
                if response.status == 204:
                    logger.info(f"Successfully sent alert for {product_name}")
                    return True
                
                error_text = await response.text()
                logger.error(f"Discord API error: {response.status} - {error_text}")
                return False

        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
            return False
        finally:
            # Don't close session here to allow reuse
            pass