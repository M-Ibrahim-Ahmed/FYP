# safe_preview.py — ScamShield Safe Preview Service
# Captures screenshots of suspicious URLs in a SANDBOXED environment.
#
# The malicious page is NEVER loaded on the user's machine.
#
# Methods (in priority order):
#   1) Docker Selenium container (true sandbox — FYP architecture)
#   2) Remote screenshot API (fallback when Docker is not running)

import os
import base64
import time
import logging

logger = logging.getLogger('ScamShield')

try:
    import urllib.request
    import urllib.error
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import WebDriverException, TimeoutException
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False

# ─── Configuration ───
SELENIUM_REMOTE_URL = os.environ.get('SELENIUM_REMOTE_URL', 'http://localhost:4444/wd/hub')
PREVIEW_TIMEOUT = int(os.environ.get('PREVIEW_TIMEOUT', '15'))
SCREENSHOT_WIDTH = 1280
SCREENSHOT_HEIGHT = 900

# Fallback remote screenshot API (free, no key needed)
THUM_IO_URL = 'https://image.thum.io/get/width/{w}/crop/{h}/noanimate/{url}'


class SafePreview:
    """Captures screenshots of suspicious URLs using sandboxed environments.
    
    Primary: Docker Selenium container (isolated browser in a container)
    Fallback: Remote screenshot API (thum.io — when Docker is not running)
    
    The URL is NEVER opened on the user's local machine.
    """

    def __init__(self):
        self._docker_available = False
        self.available = True  # Always available (API fallback)

        # Check if Docker Selenium is reachable
        if HAS_SELENIUM:
            self._docker_available = self._check_docker_selenium()

        if self._docker_available:
            logger.info('[SafePreview] ✅ Docker Selenium sandbox connected (%s)', SELENIUM_REMOTE_URL)
        else:
            logger.info('[SafePreview] ⚠️ Docker Selenium not available — using remote API fallback')

    def _check_docker_selenium(self):
        """Quick check if Docker Selenium is reachable."""
        try:
            req = urllib.request.Request(
                SELENIUM_REMOTE_URL.replace('/wd/hub', '/status'),
                method='GET',
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                return resp.status == 200
        except Exception:
            return False

    def capture(self, url, timeout=None):
        """Capture a screenshot of the given URL via sandboxed service.

        Returns:
            dict with 'success', 'screenshot_base64', 'page_title', 'final_url', 'error'
        """
        if not url or not url.startswith(('http://', 'https://')):
            return {'success': False, 'error': 'Invalid URL — must start with http:// or https://'}

        timeout = timeout or PREVIEW_TIMEOUT

        # Method 1: Docker Selenium (proper sandbox — preferred for FYP)
        if HAS_SELENIUM and self._docker_available:
            result = self._capture_via_selenium(url, timeout)
            if result['success']:
                return result
            logger.warning('[SafePreview] Docker Selenium failed: %s', result.get('error', ''))

        # Method 2: Remote screenshot API (fallback)
        if HAS_URLLIB:
            result = self._capture_via_api(url, timeout)
            if result['success']:
                return result

        return {
            'success': False,
            'error': 'Could not capture preview. Start Docker with: docker-compose up',
        }

    def _capture_via_selenium(self, url, timeout):
        """Capture screenshot using Docker Selenium container (sandboxed)."""
        driver = None
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument(f'--window-size={SCREENSHOT_WIDTH},{SCREENSHOT_HEIGHT}')
            chrome_options.add_argument('--disable-plugins')
            chrome_options.add_argument('--incognito')

            driver = webdriver.Remote(
                command_executor=SELENIUM_REMOTE_URL,
                options=chrome_options,
            )
            driver.set_page_load_timeout(timeout)
            driver.set_script_timeout(timeout)

            logger.info('[SafePreview] Loading via Docker sandbox: %s', url[:80])
            start = time.time()
            driver.get(url)
            time.sleep(2)

            elapsed = round(time.time() - start, 2)
            screenshot = driver.get_screenshot_as_base64()

            return {
                'success': True,
                'screenshot_base64': screenshot,
                'page_title': driver.title or '',
                'final_url': driver.current_url or url,
                'load_time': elapsed,
                'method': 'docker_selenium',
            }
        except TimeoutException:
            return {'success': False, 'error': f'Page load timed out after {timeout}s'}
        except Exception as e:
            return {'success': False, 'error': f'Docker Selenium error: {str(e)[:150]}'}
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

    def _capture_via_api(self, url, timeout):
        """Capture screenshot using remote API (fallback when Docker is not running)."""
        try:
            api_url = THUM_IO_URL.format(w=SCREENSHOT_WIDTH, h=SCREENSHOT_HEIGHT, url=url)
            logger.info('[SafePreview] Fallback: remote API screenshot for %s', url[:80])
            start = time.time()

            req = urllib.request.Request(api_url, headers={
                'User-Agent': 'ScamShield/1.0',
            })
            with urllib.request.urlopen(req, timeout=timeout + 10) as response:
                image_data = response.read()

            elapsed = round(time.time() - start, 2)
            screenshot_b64 = base64.b64encode(image_data).decode('utf-8')

            logger.info('[SafePreview] API screenshot captured in %.2fs', elapsed)

            return {
                'success': True,
                'screenshot_base64': screenshot_b64,
                'page_title': '',
                'final_url': url,
                'load_time': elapsed,
                'method': 'remote_api',
            }
        except Exception as e:
            return {'success': False, 'error': f'API error: {str(e)[:150]}'}

    @property
    def is_available(self):
        return self.available

    @property
    def is_docker_connected(self):
        return self._docker_available
