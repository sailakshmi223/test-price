import asyncio
from notify_f import DiscordNotifier

# CURRENT TEST PRODUCTS (Update these periodically)
TEST_PRODUCTS = {
    "amazon": {
        "url": "https://www.amazon.in/dp/B0BY8JZ22W",  # iPhone 14
        "name": "Apple iPhone 14 (128GB, Blue)",
        "old_price": 79900,
        "new_price": 72900
    },
    "flipkart": {
        "url": "https://www.flipkart.com/apple-iphone-14-blue-128-gb/p/itmdb77f40da6b6d",
        "name": "Apple iPhone 14 (128GB, Blue)",
        "old_price": 79900,
        "new_price": 72900
    },
    "croma": {
        "url": "https://www.croma.com/apple-iphone-14-128gb-blue-/p/261013",
        "name": "Apple iPhone 14 (128GB, Blue)",
        "old_price": 79900,
        "new_price": 73900
    }
}

async def run_tests():
    async with DiscordNotifier() as notifier:
        # Test Amazon
        await notifier.send_alert(
            product_name=TEST_PRODUCTS["amazon"]["name"] + " [AMAZON TEST]",
            old_price=TEST_PRODUCTS["amazon"]["old_price"],
            new_price=TEST_PRODUCTS["amazon"]["new_price"],
            url=TEST_PRODUCTS["amazon"]["url"],
            retailer="amazon"
        )
        
        # Test Flipkart
        await notifier.send_alert(
            product_name=TEST_PRODUCTS["flipkart"]["name"] + " [FLIPKART TEST]",
            old_price=TEST_PRODUCTS["flipkart"]["old_price"],
            new_price=TEST_PRODUCTS["flipkart"]["new_price"],
            url=TEST_PRODUCTS["flipkart"]["url"],
            retailer="flipkart"
        )
        
        # Test Croma
        await notifier.send_alert(
            product_name=TEST_PRODUCTS["croma"]["name"] + " [CROMA TEST]",
            old_price=TEST_PRODUCTS["croma"]["old_price"],
            new_price=TEST_PRODUCTS["croma"]["new_price"],
            url=TEST_PRODUCTS["croma"]["url"],
            retailer="croma"
        )

if __name__ == "__main__":
    asyncio.run(run_tests())