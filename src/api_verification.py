"""
API-based LNNTE verification module.
Uses the public API with 2captcha for CAPTCHA solving and proxy rotation.
"""

import logging
import time
import requests
from typing import Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import random

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
    raw_response: str = ""
    error: Optional[str] = None
    added_at: Optional[str] = None
    active: Optional[bool] = None


@dataclass
class CaptchaToken:
    """Stores a CAPTCHA token with its metadata."""
    token: str
    created_at: float
    uses: int = 0
    max_uses: int = 50  # Conservative limit before refreshing
    ttl_seconds: int = 110  # Token typically valid for ~2 minutes
    
    def is_valid(self) -> bool:
        """Check if token is still usable."""
        age = time.time() - self.created_at
        return age < self.ttl_seconds and self.uses < self.max_uses


class TwoCaptchaSolver:
    """
    Solves reCAPTCHA using 2captcha.com service.
    """
    
    API_URL = "http://2captcha.com"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def solve_recaptcha(self, site_key: str, page_url: str, timeout: int = 180) -> Optional[str]:
        """
        Solve reCAPTCHA v2 and return the token.
        
        Args:
            site_key: The reCAPTCHA site key
            page_url: The URL where CAPTCHA appears
            timeout: Max seconds to wait for solution
            
        Returns:
            CAPTCHA token string or None if failed
        """
        try:
            # Submit CAPTCHA task
            submit_url = f"{self.API_URL}/in.php"
            submit_params = {
                "key": self.api_key,
                "method": "userrecaptcha",
                "googlekey": site_key,
                "pageurl": page_url,
                "json": 1
            }
            
            logger.info("Submitting CAPTCHA to 2captcha...")
            response = requests.post(submit_url, data=submit_params, timeout=30)
            result = response.json()
            
            if result.get("status") != 1:
                error_msg = result.get('request', 'Unknown error')
                logger.error(f"2captcha submit error: {error_msg}")
                # Check for specific errors
                if error_msg == "ERROR_ZERO_BALANCE":
                    logger.error("2captcha account has zero balance - please add funds")
                elif error_msg == "ERROR_WRONG_USER_KEY" or error_msg == "ERROR_KEY_DOES_NOT_EXIST":
                    logger.error("Invalid 2captcha API key")
                elif error_msg == "ERROR_NO_SLOT_AVAILABLE":
                    logger.warning("2captcha is busy, waiting before retry...")
                    time.sleep(10)
                return None
            
            task_id = result.get("request")
            logger.info(f"2captcha task ID: {task_id}")
            
            # Poll for result with initial delay
            result_url = f"{self.API_URL}/res.php"
            result_params = {
                "key": self.api_key,
                "action": "get",
                "id": task_id,
                "json": 1
            }
            
            # Wait initial 15 seconds before first poll (captcha takes time)
            logger.info("Waiting for CAPTCHA solution (usually 20-60 seconds)...")
            time.sleep(15)
            
            start_time = time.time()
            poll_interval = 5
            while (time.time() - start_time) < timeout:
                try:
                    response = requests.get(result_url, params=result_params, timeout=30)
                    result = response.json()
                    
                    if result.get("status") == 1:
                        token = result.get("request")
                        logger.info("CAPTCHA solved successfully!")
                        return token
                    elif result.get("request") == "CAPCHA_NOT_READY":
                        elapsed = int(time.time() - start_time)
                        logger.debug(f"CAPTCHA still being solved... ({elapsed}s elapsed)")
                        time.sleep(poll_interval)
                        continue
                    else:
                        error_msg = result.get('request', 'Unknown error')
                        logger.error(f"2captcha error: {error_msg}")
                        if error_msg == "ERROR_CAPTCHA_UNSOLVABLE":
                            logger.warning("CAPTCHA was unsolvable, will retry with new captcha")
                        return None
                except requests.RequestException as e:
                    logger.warning(f"Network error polling 2captcha: {e}, retrying...")
                    time.sleep(poll_interval)
                    continue
            
            logger.error(f"2captcha timeout after {timeout} seconds")
            return None
            
        except requests.RequestException as e:
            logger.error(f"2captcha network error: {e}")
            return None
        except Exception as e:
            logger.error(f"2captcha error: {e}")
            return None


class ProxyRotator:
    """
    Rotates through a list of proxies for requests.
    """
    
    def __init__(self, proxies: List[str] = None):
        """
        Initialize with proxy list.
        
        Args:
            proxies: List of proxy URLs in format "http://user:pass@host:port" or "http://host:port"
        """
        self.proxies = proxies or []
        self.current_index = 0
        self.failed_proxies = set()
    
    def get_next(self) -> Optional[dict]:
        """Get next proxy in rotation."""
        if not self.proxies:
            return None
        
        available = [p for p in self.proxies if p not in self.failed_proxies]
        if not available:
            # Reset failed proxies if all have failed
            self.failed_proxies.clear()
            available = self.proxies
        
        proxy = random.choice(available)
        return {
            "http": proxy,
            "https": proxy
        }
    
    def mark_failed(self, proxy_dict: dict):
        """Mark a proxy as failed."""
        if proxy_dict:
            proxy_url = proxy_dict.get("http")
            if proxy_url:
                self.failed_proxies.add(proxy_url)
                logger.warning(f"Marked proxy as failed: {proxy_url[:30]}...")
    
    def add_proxy(self, proxy: str):
        """Add a new proxy to the pool."""
        if proxy not in self.proxies:
            self.proxies.append(proxy)


class LNNTEApiVerifier:
    """
    Verifies phone numbers using the LNNTE public API.
    Uses 2captcha for CAPTCHA solving and supports proxy rotation.
    """
    
    API_URL = "https://public-api.lnnte-dncl.gc.ca/v1/Consumer/Check"
    SITE_URL = "https://lnnte-dncl.gc.ca/en/Consumer/Check-your-registration"
    # reCAPTCHA site key extracted from LNNTE website source
    RECAPTCHA_SITE_KEY = "6LdnlkAUAAAAAL2zK68LwI1rDeclqZFiYr9jTSOX"
    
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:146.0) Gecko/20100101 Firefox/146.0",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://lnnte-dncl.gc.ca/",
        "Origin": "https://lnnte-dncl.gc.ca",
        "Content-Type": "application/json",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site"
    }
    
    def __init__(
        self,
        twocaptcha_api_key: str = None,
        proxies: List[str] = None,
        status_callback: Callable[[str], None] = None
    ):
        """
        Initialize the API verifier.
        
        Args:
            twocaptcha_api_key: API key for 2captcha.com
            proxies: List of proxy URLs for rotation
            status_callback: Callback for status updates
        """
        self.captcha_solver = TwoCaptchaSolver(twocaptcha_api_key) if twocaptcha_api_key else None
        self.proxy_rotator = ProxyRotator(proxies)
        self.status_callback = status_callback
        self.current_token: Optional[CaptchaToken] = None
        self.session = requests.Session()
    
    def _update_status(self, message: str):
        """Send status update."""
        logger.info(message)
        if self.status_callback:
            self.status_callback(message)
    
    def _get_captcha_token(self, max_attempts: int = 3) -> Optional[str]:
        """Get a valid CAPTCHA token, solving if needed with retries."""
        # Check if current token is still valid
        if self.current_token and self.current_token.is_valid():
            self.current_token.uses += 1
            logger.debug(f"Reusing captcha token (use {self.current_token.uses})")
            return self.current_token.token
        
        # Need to solve new CAPTCHA
        if not self.captcha_solver:
            self._update_status("No 2captcha API key - cannot solve CAPTCHA automatically")
            return None
        
        # Try multiple times to solve CAPTCHA
        for attempt in range(max_attempts):
            self._update_status(f"Solving CAPTCHA with 2captcha (attempt {attempt + 1}/{max_attempts})...")
            token = self.captcha_solver.solve_recaptcha(
                site_key=self.RECAPTCHA_SITE_KEY,
                page_url=self.SITE_URL
            )
            
            if token:
                self.current_token = CaptchaToken(
                    token=token,
                    created_at=time.time()
                )
                self._update_status("CAPTCHA solved! Token acquired.")
                return token
            
            if attempt < max_attempts - 1:
                self._update_status(f"CAPTCHA solve failed, retrying in 5 seconds...")
                time.sleep(5)
        
        self._update_status("Failed to solve CAPTCHA after all attempts")
        return None
    
    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number for API request."""
        # Remove all non-digits
        digits = ''.join(c for c in phone if c.isdigit())
        
        # Format as XXX-XXX-XXXX if we have 10 digits
        if len(digits) == 10:
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        elif len(digits) == 11 and digits[0] == '1':
            # Remove leading 1
            digits = digits[1:]
            return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
        
        return phone  # Return as-is if format unknown
    
    def verify_phone(self, phone: str, max_retries: int = 3) -> VerificationResult:
        """
        Verify a single phone number against the LNNTE registry.
        
        Args:
            phone: Phone number to verify
            max_retries: Maximum retry attempts
            
        Returns:
            VerificationResult with status
        """
        normalized = self._normalize_phone(phone)
        self._update_status(f"Checking: {normalized}")
        
        for attempt in range(max_retries):
            try:
                # Get proxy for this request
                proxy = self.proxy_rotator.get_next()
                
                # Get CAPTCHA token
                captcha_token = self._get_captcha_token()
                if not captcha_token:
                    return VerificationResult(
                        phone=phone,
                        status=VerificationStatus.UNKNOWN,
                        error="Could not obtain CAPTCHA token"
                    )
                
                # Build request
                headers = self.DEFAULT_HEADERS.copy()
                headers["Authorization-Captcha"] = captcha_token
                
                payload = {"Phone": normalized}
                
                # Make API request
                response = self.session.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    proxies=proxy,
                    timeout=30
                )
                
                # Handle response
                if response.status_code == 200:
                    # Phone IS on the list
                    data = response.json()
                    self._update_status(f"Result: ON LIST (registered since {data.get('AddedAt', 'unknown')})")
                    return VerificationResult(
                        phone=phone,
                        status=VerificationStatus.ON_LIST,
                        raw_response=response.text,
                        added_at=data.get("AddedAt"),
                        active=data.get("Active", True)
                    )
                
                elif response.status_code == 404:
                    # Phone is NOT on the list
                    self._update_status("Result: NOT on list")
                    return VerificationResult(
                        phone=phone,
                        status=VerificationStatus.NOT_ON_LIST,
                        raw_response=response.text
                    )
                
                elif response.status_code == 400:
                    # CAPTCHA token expired or invalid
                    self._update_status("CAPTCHA token expired, getting new one...")
                    self.current_token = None  # Force new token
                    continue
                
                elif response.status_code == 429:
                    # Rate limited
                    self._update_status("Rate limited, switching proxy and waiting...")
                    self.proxy_rotator.mark_failed(proxy)
                    time.sleep(5)
                    continue
                
                else:
                    logger.warning(f"Unexpected status code: {response.status_code}")
                    self._update_status(f"Unexpected response: {response.status_code}")
                    continue
                    
            except requests.Timeout:
                logger.warning(f"Request timeout (attempt {attempt + 1})")
                self.proxy_rotator.mark_failed(proxy)
                continue
                
            except requests.RequestException as e:
                logger.error(f"Request error: {e}")
                self.proxy_rotator.mark_failed(proxy)
                continue
                
            except Exception as e:
                logger.error(f"Verification error: {e}")
                continue
        
        return VerificationResult(
            phone=phone,
            status=VerificationStatus.UNKNOWN,
            error=f"Failed after {max_retries} attempts"
        )
    
    def verify_batch(
        self,
        phones: List[str],
        progress_callback: Callable[[int, int], None] = None
    ) -> List[VerificationResult]:
        """
        Verify multiple phone numbers.
        
        Args:
            phones: List of phone numbers
            progress_callback: Called with (current, total) for progress updates
            
        Returns:
            List of VerificationResults
        """
        results = []
        total = len(phones)
        
        for i, phone in enumerate(phones):
            if progress_callback:
                progress_callback(i + 1, total)
            
            result = self.verify_phone(phone)
            results.append(result)
            
            # Small delay between requests
            time.sleep(0.5)
        
        return results
