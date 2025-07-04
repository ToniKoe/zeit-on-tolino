import logging
import glob
import os
import time
from pathlib import Path
from typing import Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from zeit_on_tolino.env_vars import EnvVars, MissingEnvironmentVariable
from zeit_on_tolino.web import Delay

ZEIT_LOGIN_URL = "https://epaper.zeit.de/abo/diezeit"
ZEIT_DATE_FORMAT = "%d.%m.%Y"

BUTTON_TEXT_TO_RECENT_EDITION = "ZUR AKTUELLEN AUSGABE"
BUTTON_TEXT_DOWNLOAD_EPUB = "EPUB FÜR E-READER LADEN"
BUTTON_TEXT_EPUB_DOWNLOAD_IS_PENDING = "EPUB FOLGT IN KÜRZE"

log = logging.getLogger(__name__)

def _get_credentials() -> Tuple[str, str]:
    try:
        username = os.environ[EnvVars.ZEIT_PREMIUM_USER]
        password = os.environ[EnvVars.ZEIT_PREMIUM_PASSWORD]
        return username, password
    except KeyError:
        raise MissingEnvironmentVariable(
            f"Ensure to export your ZEIT username and password as environment variables "
            f"'{EnvVars.ZEIT_PREMIUM_USER}' and '{EnvVars.ZEIT_PREMIUM_PASSWORD}'. For "
            "Github Actions, use repository secrets."
        )


def _login(webdriver: WebDriver) -> None:
    username, password = _get_credentials()
    webdriver.get(ZEIT_LOGIN_URL)

    username_field = webdriver.find_element(By.ID, "username")
    username_field.send_keys(username)
    password_field = webdriver.find_element(By.ID, "password")
    password_field.send_keys(password)

    btn = webdriver.find_element(By.ID, "kc-login")
    btn.click()
    time.sleep(Delay.small)

    if "anmelden" in webdriver.current_url:
        raise RuntimeError("Failed to login, check your login credentials.")
    
    time.sleep(Delay.medium)
    # WebDriverWait(webdriver, Delay.medium).until(EC.presence_of_element_located((By.CLASS_NAME, "page-section-header hidden-xs")))


def _get_latest_downloaded_file_path(download_dir: str) -> Path:
    download_dir_files = glob.glob(f"{download_dir}/*")
    latest_file = max(download_dir_files, key=os.path.getctime)
    return Path(latest_file)


def wait_for_downloads(path):
    time.sleep(Delay.small)
    if not os.path.isdir(path):
        raise FileNotFoundError(f"Download directory does not exist: {path}")

    start = time.time()
    while any([filename.endswith(".crdownload") for filename in os.listdir(path)]):
        now = time.time()
        if now > start + Delay.large:
            raise TimeoutError(f"Did not manage to download file within {Delay.large} seconds.")
        else:
            log.info(f"waiting for download to be finished...")
            time.sleep(2)


def download_e_paper(webdriver: WebDriver) -> str:
    log.info("logging into ZEIT premium...")
    _login(webdriver)

    # go to most recent edition
    log.info("downloading most recent ZEIT e-paper...")
    time.sleep(Delay.large)
    # time.sleep(Delay.large)
    # for link in webdriver.find_elements(By.TAG_NAME, "a"):
    #     log.info('\t' + link.text)
    #     if link.text == BUTTON_TEXT_TO_RECENT_EDITION:
    #         link.click()
    #         log.info('clicked ' + link.text)
    #         break

    link = WebDriverWait(webdriver, Delay.medium).until(
        EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'ZUR AKTUELLEN AUSGABE')]"))
    )
    link.click()

    if BUTTON_TEXT_EPUB_DOWNLOAD_IS_PENDING in webdriver.page_source:
        raise RuntimeError("New ZEIT release is available, however, EPUB version is not. Retry again later.")

    # trigger epub download
    time.sleep(Delay.medium)
    log.info('going through links')
    for link in webdriver.find_elements(By.TAG_NAME, "a"):
        log.info('\t' + link.text)
        if link.text == BUTTON_TEXT_DOWNLOAD_EPUB:
            log.info("clicking download button now...")
            link.click()
            break 
    
    wait_for_downloads(webdriver.download_dir_path)
    e_paper_path = _get_latest_downloaded_file_path(webdriver.download_dir_path)

    if not e_paper_path.is_file():
        raise RuntimeError("Could not download e paper, check your login credentials.")

    return e_paper_path
