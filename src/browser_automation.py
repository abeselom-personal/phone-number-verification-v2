"""
Browser automation module for LNNTÉ verification.
Uses Playwright for browser control with human CAPTCHA handling.
"""

import logging
import time
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum
from playwright.sync_api import sync_playwright, Page, Browser, BrowserContext, TimeoutError as PlaywrightTimeout

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Possible verification result statuses."""
    ON_LIST = "On list"
    NOT_ON_LIST = "Not on list"
    UNKNOWN = "Unknown"


@dataclass
class VerificationResult:
    """Result of a single phone verification."""
    phone: str
    status: VerificationStatus
    raw_message: str = ""
    error: Optional[str] = None


class LNNTEAutomation:
    """
    Automates the LNNTÉ phone verification process.
    Handles browser control with pause for human CAPTCHA solving.
    """
    
    LNNTE_URL = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration"
    
    PHONE_INPUT_ID = "phone"
    NEXT_BUTTON_SELECTOR = "button.btn.btn-primary[type='submit']"
    CHECK_BUTTON_SELECTOR = "button.btn.btn-primary[type='submit']"
    
    NOT_REGISTERED_PATTERNS = [
        "is not registered on the national dncl",
        "is not registered on the national do not call list",
        "n'est pas inscrit sur la lnnte",
        "n'est pas inscrite sur la liste nationale",
        "your number is not registered",
        "not currently registered"
    ]
    
    REGISTERED_PATTERNS = [
        "is registered on the national dncl",
        "is registered on the national do not call list",
        "est inscrit sur la lnnte",
        "est inscrite sur la liste nationale",
        "your number is registered",
        "currently registered"
    ]
    
    def __init__(self, headless: bool = False, timeout: int = 30000):
        """
        Initialize automation engine.
        
        Args:
            headless: Run browser in headless mode (False for CAPTCHA solving)
            timeout: Default timeout in milliseconds
        """
        self.headless = headless
        self.timeout = timeout
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self._captcha_callback: Optional[Callable] = None
        self._status_callback: Optional[Callable] = None
    
    def set_captcha_callback(self, callback: Callable[[str], None]):
        """Set callback to notify UI when CAPTCHA needs solving."""
        self._captcha_callback = callback
    
    def set_status_callback(self, callback: Callable[[str], None]):
        """Set callback for status updates."""
        self._status_callback = callback
    
    def _update_status(self, message: str):
        """Send status update to callback if set."""
        logger.info(message)
        if self._status_callback:
            self._status_callback(message)
    
    def start_browser(self):
        """Launch browser and navigate to LNNTÉ page."""
        self._update_status("Starting browser...")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=['--start-maximized']
        )
        self.context = self.browser.new_context(
            viewport={'width': 1280, 'height': 800},
            locale='en-CA',
            ignore_https_errors=True
        )
        self.page = self.context.new_page()
        self.page.set_default_timeout(self.timeout)
        
        self._update_status("Browser started successfully")
    
    def close_browser(self):
        """Clean up browser resources."""
        try:
            if self.page:
                self.page.close()
            if self.context:
                self.context.close()
            if self.browser:
                self.browser.close()
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.warning(f"Error closing browser: {e}")
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
    
    def navigate_to_form(self) -> bool:
        """
        Navigate to the LNNTÉ verification form.
        
        Returns:
            True if navigation successful
        """
        try:
            self._update_status(f"Navigating to {self.LNNTE_URL}")
            self.page.goto(self.LNNTE_URL, wait_until='networkidle')
            
            self.page.wait_for_selector(f"#{self.PHONE_INPUT_ID}", state='visible')
            self._update_status("Form loaded successfully")
            return True
            
        except PlaywrightTimeout:
            logger.error("Timeout waiting for form to load")
            return False
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    def enter_phone_number(self, phone: str) -> bool:
        """
        Enter phone number in the input field.
        
        Args:
            phone: Normalized phone number (XXX-XXX-XXXX)
            
        Returns:
            True if successful
        """
        try:
            phone_input = self.page.locator(f"#{self.PHONE_INPUT_ID}")
            phone_input.wait_for(state='visible')
            
            phone_input.clear()
            phone_input.fill(phone)
            
            self._update_status(f"Entered phone: {phone}")
            return True
            
        except Exception as e:
            logger.error(f"Error entering phone number: {e}")
            return False
    
    def click_next(self) -> bool:
        """
        Click the Next button to proceed to CAPTCHA step.
        
        Returns:
            True if successful
        """
        try:
            next_btn = self.page.locator(self.NEXT_BUTTON_SELECTOR).first
            next_btn.wait_for(state='visible')
            next_btn.click()
            
            self.page.wait_for_load_state('networkidle')
            self._update_status("Clicked Next button")
            return True
            
        except Exception as e:
            logger.error(f"Error clicking Next: {e}")
            return False
    
    def wait_for_captcha_solution(self, timeout_seconds: int = 300) -> bool:
        """
        Wait for human to solve CAPTCHA.
        Detects when CAPTCHA is solved by checking for the reCAPTCHA response being filled.
        
        Args:
            timeout_seconds: Maximum time to wait for CAPTCHA solution
            
        Returns:
            True if CAPTCHA was solved
        """
        self._update_status("Waiting for CAPTCHA to be solved...")
        
        if self._captcha_callback:
            self._captcha_callback("⚠️ PLEASE SOLVE THE CAPTCHA IN THE BROWSER WINDOW ⚠️")
        
        time.sleep(1)
        
        has_captcha = self.page.locator("iframe[src*='recaptcha']").count() > 0
        if not has_captcha:
            has_captcha = self.page.locator(".g-recaptcha").count() > 0
        
        if not has_captcha:
            self._update_status("No CAPTCHA detected on page, proceeding...")
            return True
        
        self._update_status("CAPTCHA detected - waiting for you to solve it...")
        
        start_time = time.time()
        captcha_solved = False
        
        while (time.time() - start_time) < timeout_seconds:
            try:
                recaptcha_response = self.page.evaluate("""
                    () => {
                        const response = document.querySelector('[name="g-recaptcha-response"]');
                        if (response && response.value && response.value.length > 0) {
                            return true;
                        }
                        // Also check for hCaptcha
                        const hResponse = document.querySelector('[name="h-captcha-response"]');
                        if (hResponse && hResponse.value && hResponse.value.length > 0) {
                            return true;
                        }
                        return false;
                    }
                """)
                
                if recaptcha_response:
                    self._update_status("CAPTCHA solved! Proceeding...")
                    captcha_solved = True
                    break
                
            except Exception as e:
                logger.debug(f"CAPTCHA check iteration: {e}")
            
            time.sleep(1)
        
        if not captcha_solved:
            logger.error("CAPTCHA solution timeout")
            if self._captcha_callback:
                self._captcha_callback("CAPTCHA timeout - please solve faster next time")
            return False
        
        return True
    
    def click_check_registration(self) -> bool:
        """
        Click the Check Registration button after CAPTCHA is solved.
        
        Returns:
            True if successful
        """
        try:
            time.sleep(0.5)
            
            check_btn = self.page.locator(self.CHECK_BUTTON_SELECTOR).first
            check_btn.wait_for(state='visible')
            check_btn.click()
            
            self.page.wait_for_load_state('networkidle')
            self._update_status("Clicked Check Registration")
            return True
            
        except Exception as e:
            logger.error(f"Error clicking Check Registration: {e}")
            return False
    
    def _wait_for_result_page(self, timeout_seconds: int = 30) -> bool:
        """
        Wait for the result page to load after submitting.
        
        Returns:
            True if result page detected
        """
        start_time = time.time()
        
        while (time.time() - start_time) < timeout_seconds:
            try:
                body_text = self.page.locator("body").inner_text().lower()
                
                # Check for any result indicators
                result_indicators = [
                    "is registered",
                    "is not registered",
                    "n'est pas inscrit",
                    "est inscrit",
                    "registration status",
                    "your phone number"
                ]
                
                for indicator in result_indicators:
                    if indicator in body_text:
                        return True
                
                # Check if still on CAPTCHA page
                has_captcha = self.page.locator("iframe[src*='recaptcha']").count() > 0
                if has_captcha:
                    logger.debug("Still on CAPTCHA page...")
                    time.sleep(1)
                    continue
                    
            except Exception as e:
                logger.debug(f"Result page check: {e}")
            
            time.sleep(0.5)
        
        return False
    
    def extract_result(self) -> VerificationResult:
        """
        Extract verification result from the results page.
        
        Returns:
            VerificationResult with status and details
        """
        try:
            self.page.wait_for_load_state('networkidle')
            
            # Wait for actual result page content
            if not self._wait_for_result_page(timeout_seconds=15):
                self._update_status("Result: Unknown (result page not loaded)")
                return VerificationResult(
                    phone="",
                    status=VerificationStatus.UNKNOWN,
                    error="Result page did not load - may still be on CAPTCHA or error page"
                )
            
            time.sleep(0.5)
            
            body_text = self.page.locator("body").inner_text().lower()
            
            # Log the page content for debugging
            logger.debug(f"Page content (first 300 chars): {body_text[:300]}")
            
            # Check NOT registered first (more specific)
            for pattern in self.NOT_REGISTERED_PATTERNS:
                if pattern.lower() in body_text:
                    self._update_status("Result: NOT on list")
                    return VerificationResult(
                        phone="",
                        status=VerificationStatus.NOT_ON_LIST,
                        raw_message=body_text[:500]
                    )
            
            # Check if registered
            for pattern in self.REGISTERED_PATTERNS:
                if pattern.lower() in body_text:
                    self._update_status("Result: On list")
                    return VerificationResult(
                        phone="",
                        status=VerificationStatus.ON_LIST,
                        raw_message=body_text[:500]
                    )
            
            # If we got here, we couldn't determine the status
            self._update_status("Result: Unknown (patterns not matched)")
            logger.warning(f"Could not match result patterns. Page text: {body_text[:500]}")
            return VerificationResult(
                phone="",
                status=VerificationStatus.UNKNOWN,
                raw_message=body_text[:500],
                error="Could not determine registration status from page content"
            )
            
        except Exception as e:
            logger.error(f"Error extracting result: {e}")
            return VerificationResult(
                phone="",
                status=VerificationStatus.UNKNOWN,
                error=str(e)
            )
    
    def verify_phone(self, phone: str, max_retries: int = 2) -> VerificationResult:
        """
        Complete verification flow for a single phone number.
        
        Args:
            phone: Normalized phone number
            max_retries: Number of retries for non-CAPTCHA failures
            
        Returns:
            VerificationResult
        """
        attempt = 0
        
        while attempt <= max_retries:
            try:
                self._update_status(f"Verifying {phone} (attempt {attempt + 1})")
                
                if not self.navigate_to_form():
                    attempt += 1
                    continue
                
                if not self.enter_phone_number(phone):
                    attempt += 1
                    continue
                
                if not self.click_next():
                    attempt += 1
                    continue
                
                if not self.wait_for_captcha_solution():
                    return VerificationResult(
                        phone=phone,
                        status=VerificationStatus.UNKNOWN,
                        error="CAPTCHA solution timeout"
                    )
                
                if not self.click_check_registration():
                    attempt += 1
                    continue
                
                result = self.extract_result()
                result.phone = phone
                return result
                
            except Exception as e:
                logger.error(f"Verification attempt {attempt + 1} failed: {e}")
                attempt += 1
        
        return VerificationResult(
            phone=phone,
            status=VerificationStatus.UNKNOWN,
            error=f"Failed after {max_retries + 1} attempts"
        )
    
    def __enter__(self):
        """Context manager entry."""
        self.start_browser()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close_browser()
