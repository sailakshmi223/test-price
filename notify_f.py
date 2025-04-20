import aiohttp
import asyncio
import os
from dotenv import load_dotenv
import logging
import platform
from typing import Optional

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

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
        
    async def close(self):
        """Clean up resources"""
        if hasattr(self, 'session') and self.session:
            await self.session.close()

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
            logger.warning("No webhook URL configured")
            return False

        drop_pct = ((old_price - new_price) / old_price) * 100
        if drop_pct < self.min_drop:
            logger.info(f"Price drop {drop_pct:.1f}% below threshold {self.min_drop}%")
            return False

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
                "color": 3066993,
                "footer": {"text": "Price Tracker Notification"}
            }]
        }

        try:
            async with self.session.post(self.webhook_url, json=message) as response:
                if response.status == 204:
                    logger.info(f"Alert sent for {product_name}")
                    return True
                logger.error(f"Discord response: {response.status}")
                return False
        except Exception as e:
            logger.error(f"Notification error: {str(e)}")
            return False