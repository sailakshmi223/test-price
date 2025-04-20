

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time

def init_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--ignore-certificate-errors')
    options.add_argument('--start-maximized')
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    return driver

if __name__ == "__main__":
    try:
        driver = init_driver()
        driver.get("https://www.google.com")
        print("[+] Chrome launched successfully")
        time.sleep(5)
        driver.quit()
    except Exception as e:
        print("[-] Error occurred:", e)
