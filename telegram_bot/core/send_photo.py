from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import random
import time
import requests

from config import CREATEP_TOP_URL

HEART_EMOJIS = [
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎"
]

def get_random_createp_image():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1920,1080")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        print("Загружаем сайт...")
        driver.get(CREATEP_TOP_URL)
        time.sleep(3)

        # Автоскролл до конца страницы
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        while scroll_attempts < 20:  # максимум 20 прокруток
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)  # подождать, чтобы сайт успел подгрузить
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_attempts += 1

        print("Страница полностью загружена!")

        images = driver.find_elements(By.CSS_SELECTOR, "a[href^='/post'] img")
        print(f"Найдено <img>: {len(images)}")

        image_data = []
        for img in images:
            try:
                parent = img.find_element(By.XPATH, "./..")
                img_url = img.get_attribute("src")
                post_url = parent.get_attribute("href")
                caption = random.choice(HEART_EMOJIS)
                image_data.append((img_url, caption))
            except Exception:
                continue

        if not image_data:
            raise Exception("Не найдено ни одной картинки")

        print(f"Вернём: {random.choice(image_data)}")
        return random.choice(image_data)

    finally:
        driver.quit()
