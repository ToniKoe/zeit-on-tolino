from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
import os

from dotenv import load_dotenv
load_dotenv()



# --- Credentials and URL ---
credentials = {
    'trader': os.environ['TOLINO_PARTNER_SHOP'].lower(),
    'country': 'Deutschland',
    'email': os.environ['TOLINO_USER'],
    'password': os.environ['TOLINO_PASSWORD']
}
URL = "https://webreader.mytolino.com/library/index.html#/mybooks/titles"


# --- Prep: setup browser --
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 20)

# --- Step 1: Open URL + Select Country ---
driver.get(URL)

# Select Country (button with text *Name of country*)
country_elem = wait.until(EC.element_to_be_clickable(
    (By.XPATH, f"//button[normalize-space()='{credentials['country']}']")
))
country_elem.click()


# --- Step 2: Select Trader ---
# (button where the image description  (img alt) contains the text *Trader*)
trader = credentials['trader'].lower()

# Find button containing an <img> with matching alt attribute
trader_elem = wait.until(EC.element_to_be_clickable((
    By.XPATH,
    f"//button[.//img[contains(translate(@alt, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '{trader}')]]"
)))
trader_elem.click()

# --- Step 3: Click "Anmelden" ---
login_button = wait.until(EC.element_to_be_clickable(
    (By.XPATH, "//button[normalize-space()='Anmelden']")
))
login_button.click()

# --- Step 4: Enter Email + Password ---
email_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input[@type='username' or @placeholder='E-Mail Adresse']")))
email_input.send_keys(credentials['email'])

password_input = driver.find_element(By.XPATH, "//input[@type='password' or @placeholder='Passwort']")
password_input.send_keys(credentials['password'])

submit_button = driver.find_element(By.XPATH, "//button[normalize-space()='Anmelden']")
submit_button.click()

# --- Step 5: Wait for login and check success ---
# Wait for page to redirect and confirm login success
try:
    success_element = wait.until(EC.presence_of_element_located(
        (By.XPATH, "//div[contains(@class, 'library') or contains(text(), 'Meine Bücher')]")
    ))
    print("Login successful.")
except:
    # check for invalid credentials warning. Else give time out error. 
    try:
        warning = wait.until(EC.presence_of_element_located((
            By.XPATH,
            "//p[contains(@class, 'hinweis-text') and contains(text(), 'Ungültiger Benutzername oder Passwort.')]"
        )))
        print("Login failed: Ungültiger Benutzername oder Passwort.")
    except TimeoutException:
        print("No login error detected, proceeding.")

# Leave browser open for inspection
time.sleep(10)
driver.quit()


#TODO: make sure webdriver is set to german
# TODO Add logger
# TODO MAke modular
