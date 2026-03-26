# safe_preview.py — ScamShield Safe Preview Service
# Opens suspicious URLs inside a headless browser to capture a screenshot
# without exposing the user to any risk.
#
# Uses Selenium with a remote Chrome container (via Docker)
# or a local Chrome/Chromium install as fallback.

import os
import base64
import time
import logging

logger = logging.getLogger('ScamShield')

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.common.exceptions import WebDriverException, TimeoutException
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False
    logger.warning('[SafePreview] selenium not installed — safe preview disabled')

# ─── Configuration ───
SELENIUM_REMOTE_URL = os.environ.get('SELENIUM_REMOTE_URL', 'http://localhost:4444/wd/hub')
PREVIEW_TIMEOUT = int(os.environ.get('PREVIEW_TIMEOUT', '15'))  # seconds
SCREENSHOT_WIDTH = 1280
SCREENSHOT_HEIGHT = 900


class SafePreview:
    """Captures screenshots of suspicious URLs using a sandboxed browser."""

    def __init__(self):
        self.available = HAS_SELENIUM
        if self.available:
            logger.info('[SafePreview] Safe preview service initialized')

    def capture(self, url, timeout=None):
        """Capture a screenshot of the given URL.

        Returns:
            dict with 'success', 'screenshot_base64', 'page_title', 'final_url', 'error'
        """
        if not self.available:
            return {
                'success': False,
                'error': 'Selenium not installed — install selenium package to enable safe preview',
            }

        if not url or not url.startswith(('http://', 'https://')):
            return {'success': False, 'error': 'Invalid URL — must start with http:// or https://'}

        timeout = timeout or PREVIEW_TIMEOUT
        driver = None

        try:
            driver = self._create_driver()
            driver.set_page_load_timeout(timeout)
            driver.set_script_timeout(timeout)

            logger.info('[SafePreview] Loading URL: %s', url[:100])
            start = time.time()
            driver.get(url)

            # Wait a moment for dynamic content to render
            time.sleep(2)

            elapsed = round(time.time() - start, 2)
            screenshot = driver.get_screenshot_as_base64()
            page_title = driver.title or ''
            final_url = driver.current_url or url

            logger.info('[SafePreview] Screenshot captured in %.2fs (%s)', elapsed, final_url[:80])

            return {
                'success': True,
                'screenshot_base64': screenshot,
                'page_title': page_title,
                'final_url': final_url,
                'load_time': elapsed,
            }

        except TimeoutException:
            return {'success': False, 'error': f'Page load timed out after {timeout}s'}
        except WebDriverException as e:
            error_msg = str(e).split('\n')[0][:200]
            logger.error('[SafePreview] WebDriver error: %s', error_msg)
            return {'success': False, 'error': f'Browser error: {error_msg}'}
        except Exception as e:
            logger.error('[SafePreview] Unexpected error: %s', str(e))
            return {'success': False, 'error': str(e)}
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _create_driver(self):
        """Create a Selenium WebDriver instance.

        Tries remote Selenium first (Docker container), then falls back to local Chrome.
        """
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-popup-blocking')
        chrome_options.add_argument(f'--window-size={SCREENSHOT_WIDTH},{SCREENSHOT_HEIGHT}')
        # Security: disable file access, plugins, etc.
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-file-system')
        chrome_options.add_argument('--incognito')

        # Try remote Selenium (Docker container) first
        try:
            driver = webdriver.Remote(
                command_executor=SELENIUM_REMOTE_URL,
                options=chrome_options,
            )
            logger.info('[SafePreview] Connected to remote Selenium at %s', SELENIUM_REMOTE_URL)
            return driver
        except Exception:
            pass

        # Fallback: local Chrome/Chromium
        try:
            driver = webdriver.Chrome(options=chrome_options)
            logger.info('[SafePreview] Using local Chrome browser')
            return driver
        except Exception as e:
            raise WebDriverException(
                f'Could not start browser. Ensure Chrome is installed or Selenium container is running. Error: {e}'
            )

    @property
    def is_available(self):
        return self.available
