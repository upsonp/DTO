from django.test import LiveServerTestCase
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
import time


class LanguageSwaperSeleniumTests(LiveServerTestCase):
    def setUp(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.binary_location = '/usr/bin/chromium'

        self.browser = webdriver.Chrome(options=chrome_options)
        self.browser.implicitly_wait(10)

    def tearDown(self):
        if hasattr(self, 'browser'):
            self.browser.quit()

    def test_language_swaper_dropdown(self):
        # Visit the homepage using reverse
        home_url = self.live_server_url + reverse('dto:index')
        self.browser.get(home_url)

        # Print page source for debugging
        print("Page source:", self.browser.page_source)

        try:
            # Find the language select element with explicit wait
            select_element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='language']"))
            )

            # Give the page a moment to fully load
            time.sleep(2)

            select = Select(select_element)

            # Select French
            select.select_by_value("fr")

            # Wait for page reload
            time.sleep(2)

            # Verify we're on French version
            self.assertIn("/fr/", self.browser.current_url)

            # Find the language select element again
            select_element = WebDriverWait(self.browser, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select[name='language']"))
            )
            select = Select(select_element)

            # Switch back to English
            select.select_by_value("en")

            # Wait for page reload
            time.sleep(2)

            # Verify English version
            self.assertIn("/en/", self.browser.current_url)

        except Exception as e:
            # Print page source if there's an error
            print("Current URL:", self.browser.current_url)
            print("Page source after error:", self.browser.page_source)
            raise e