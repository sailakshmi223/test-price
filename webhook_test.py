import aiohttp
import asyncio
import os
from dotenv import load_dotenv
import platform

# Windows-specific event loop policy
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

load_dotenv()

async def test_webhook():
    WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")
    if not WEBHOOK:
        print("❌ No webhook found in .env file")
        return

    print(f"Testing webhook: {WEBHOOK.split('/')[-2]}...")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                WEBHOOK,
                json={"content": f"TEST MESSAGE {os.urandom(4).hex()}"}  # Unique message each time
            ) as response:
                if response.status == 204:
                    print("✅ Success! Check your Discord channel")
                else:
                    print(f"❌ Failed (Status {response.status}): {await response.text()}")
    except Exception as e:
        print(f"🚨 Error: {type(e).__name__}: {e}")

def main():
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(test_webhook())
    finally:
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

if __name__ == "__main__":
    main()