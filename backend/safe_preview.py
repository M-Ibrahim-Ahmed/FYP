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
PREVIEW_TIMEOUT = int(os.environ.get('PREVIEW_TIMEOUT', '25'))
SCREENSHOT_WIDTH = 1280
SCREENSHOT_HEIGHT = 900

# Fallback remote screenshot API (free, no key needed)
# Normal: /wait/5 = wait 5 seconds for page render (leverages thum.io cache for speed)
# Fresh:  /wait/8/maxAge/0 = force fresh capture when we suspect stale cache
THUM_IO_URL       = 'https://image.thum.io/get/width/{w}/crop/{h}/wait/5/noanimate/{url}'
THUM_IO_URL_FRESH = 'https://image.thum.io/get/width/{w}/crop/{h}/wait/8/maxAge/0/noanimate/{url}'


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
            logger.info('[SafePreview] Docker Selenium sandbox connected (%s)', SELENIUM_REMOTE_URL)
        else:
            logger.info('[SafePreview] Docker Selenium not available -- using remote API fallback')

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
            # Attempt 1: Normal request (uses thum.io cache — fast for repeat URLs)
            result = self._capture_via_api(url, timeout, force_fresh=False)
            if result['success']:
                return result

            # Attempt 2: If first attempt failed (timeout/error), try with fresh capture
            if 'timed out' in str(result.get('error', '')).lower():
                logger.warning('[SafePreview] API timed out, retrying with fresh capture...')
                time.sleep(1)
                result = self._capture_via_api(url, timeout, force_fresh=True)
                if result['success']:
                    return result

            return {
                'success': False,
                'error': f"Safe preview failed. (Error: {result.get('error')}). "
                         "The site might be slow. Try again or start Docker for a better experience."
            }

        return {
            'success': False,
            'error': 'Safe preview unavailable. (urllib/selenium missing)',
        }

    def _wait_for_page_ready(self, driver, timeout):
        """Wait for the page to be fully loaded and rendered.
        
        Strategy:
          0. Detect and wait for Cloudflare/bot-check challenge pages
          1. Wait for document.readyState == 'complete'
          2. Wait for network activity to settle (no pending XHR/fetch)
          3. Extra settle time for JS-rendered content (lazy images, SPAs)
        """
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # 0) Detect Cloudflare / bot-check challenge pages and wait for them to pass
        challenge_detect_script = """
            return (function() {
                var body = document.body ? document.body.innerText : '';
                var title = document.title || '';
                // Common challenge page indicators
                var patterns = [
                    'checking your browser',
                    'just a moment',
                    'please wait',
                    'verifying you are human',
                    'verify you are human',
                    'ddos protection',
                    'attention required',
                    'enable javascript and cookies',
                    'ray id',
                    'performing browser checks',
                    'access denied'
                ];
                var combined = (body + ' ' + title).toLowerCase();
                for (var i = 0; i < patterns.length; i++) {
                    if (combined.indexOf(patterns[i]) !== -1) return true;
                }
                // Cloudflare turnstile / challenge iframe
                if (document.querySelector('iframe[src*="challenges.cloudflare.com"]')) return true;
                if (document.querySelector('#challenge-running, #challenge-form, .cf-browser-verification')) return true;
                return false;
            })();
        """
        try:
            is_challenge = driver.execute_script(challenge_detect_script)
            if is_challenge:
                logger.info('[SafePreview] Challenge page detected (Cloudflare/bot-check), waiting for it to resolve...')
                # Wait up to 15 seconds for the challenge to complete
                challenge_deadline = time.time() + min(15, timeout - 3)
                while time.time() < challenge_deadline:
                    time.sleep(2)
                    still_challenge = driver.execute_script(challenge_detect_script)
                    if not still_challenge:
                        logger.info('[SafePreview] Challenge resolved!')
                        # After challenge resolves, wait a bit for the real page to load
                        time.sleep(3)
                        break
                else:
                    logger.warning('[SafePreview] Challenge did not resolve in time, capturing anyway')
        except Exception:
            logger.warning('[SafePreview] Challenge detection failed, continuing...')

        # 1) Wait for document.readyState == 'complete'
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            logger.info('[SafePreview] document.readyState = complete')
        except Exception:
            logger.warning('[SafePreview] Timed out waiting for readyState, continuing...')

        # 2) Wait for network idle — poll until no new resources are being fetched
        #    Uses the Performance API to detect in-flight requests
        network_idle_script = """
            return (function() {
                // Check if there are pending XHR/fetch requests
                if (window.performance) {
                    var entries = window.performance.getEntriesByType('resource');
                    var now = Date.now();
                    var pending = entries.filter(function(e) {
                        return e.responseEnd === 0;  // Still loading
                    });
                    return pending.length === 0;
                }
                return true;
            })();
        """
        try:
            # Poll for up to 8 seconds for network idle
            idle_deadline = time.time() + min(8, timeout - 2)
            while time.time() < idle_deadline:
                is_idle = driver.execute_script(network_idle_script)
                if is_idle:
                    logger.info('[SafePreview] Network idle detected')
                    break
                time.sleep(0.5)
        except Exception:
            logger.warning('[SafePreview] Network idle check failed, continuing...')

        # 3) Extra settle time for JS-rendered content (React, lazy images, animations)
        #    Wait for images to finish loading, then a final short pause
        image_load_script = """
            return Array.from(document.images).every(function(img) {
                return img.complete && img.naturalHeight !== 0;
            });
        """
        try:
            img_deadline = time.time() + 5
            while time.time() < img_deadline:
                images_ready = driver.execute_script(image_load_script)
                if images_ready:
                    logger.info('[SafePreview] All images loaded')
                    break
                time.sleep(0.5)
        except Exception:
            pass

        # Final settle — let animations/transitions finish
        time.sleep(1.5)

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

            # Smart wait: readyState + network idle + images loaded
            self._wait_for_page_ready(driver, timeout)

            elapsed = round(time.time() - start, 2)
            logger.info('[SafePreview] Page fully loaded in %.2fs, capturing screenshot', elapsed)
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

    def _capture_via_api(self, url, timeout, force_fresh=False):
        """Capture screenshot using remote API (fallback when Docker is not running).
        
        Args:
            url: The target URL to screenshot.
            timeout: Request timeout in seconds.
            force_fresh: If True, busts thum.io cache with a nonce and uses
                         the longer-wait URL template.
        """
        try:
            target_url = url

            if force_fresh:
                # Add cache-busting nonce to force a completely fresh capture
                nonce = str(int(time.time() * 1000))
                separator = '&' if '?' in url else '?'
                target_url = f'{url}{separator}_ss={nonce}'
                template = THUM_IO_URL_FRESH
                logger.info('[SafePreview] API FRESH capture for %s', url[:80])
            else:
                template = THUM_IO_URL
                logger.info('[SafePreview] API capture for %s', url[:80])

            api_url = template.format(w=SCREENSHOT_WIDTH, h=SCREENSHOT_HEIGHT, url=target_url)
            start = time.time()

            req = urllib.request.Request(api_url, headers={
                'User-Agent': 'ScamShield/1.0',
            })
            with urllib.request.urlopen(req, timeout=timeout + 10) as response:
                image_data = response.read()

            elapsed = round(time.time() - start, 2)
            screenshot_b64 = base64.b64encode(image_data).decode('utf-8')

            logger.info('[SafePreview] API screenshot captured in %.2fs (%s)',
                        elapsed, 'fresh' if force_fresh else 'cached ok')

            return {
                'success': True,
                'screenshot_base64': screenshot_b64,
                'page_title': '',
                'final_url': url,
                'load_time': elapsed,
                'method': 'remote_api',
            }
        except urllib.error.HTTPError as e:
            logger.error('[SafePreview] API HTTP Error: %s', e.code)
            return {'success': False, 'error': f'Remote API error: HTTP {e.code}'}
        except urllib.error.URLError as e:
            logger.error('[SafePreview] API URL Error: %s', e.reason)
            return {'success': False, 'error': f'Remote API unreachable: {e.reason}'}
        except Exception as e:
            logger.error('[SafePreview] API Unknown Error: %s', str(e))
            return {'success': False, 'error': f'API error: {str(e) or "Unknown error"}'}

    @property
    def is_available(self):
        return self.available

    @property
    def is_docker_connected(self):
        return self._docker_available
