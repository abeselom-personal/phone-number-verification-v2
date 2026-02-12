"""
Business phone number checker using Serper API.
Searches Google to determine if a phone number belongs to a business.
"""

import os
import logging
import requests
from typing import Optional
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class BusinessStatus(Enum):
    """Possible business check statuses."""
    IS_BUSINESS = "Business"
    NOT_BUSINESS = "Not Business"
    UNKNOWN = "Unknown"


@dataclass
class BusinessCheckResult:
    """Result of a business phone lookup."""
    phone: str
    status: BusinessStatus
    business_name: Optional[str] = None
    source: Optional[str] = None
    error: Optional[str] = None
    match_score: float = 0.0  # 0-100 confidence score
    societe_matched: bool = False  # Whether Société field was matched


class SerperBusinessChecker:
    """
    Checks if a phone number belongs to a business using Serper Places API.
    Searches Google Places for the phone number - if found, it's a business (Office).
    """
    
    SERPER_PLACES_URL = "https://google.serper.dev/places"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the business checker.
        
        Args:
            api_key: Serper API key. If not provided, reads from SERPER_API_KEY env var.
        """
        self.api_key = api_key or os.getenv('SERPER_API_KEY')
        if not self.api_key:
            logger.warning("Serper API key not set. Business checking will be disabled.")
    
    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)
    
    def check_phone(self, phone: str, societe: str = "") -> BusinessCheckResult:
        """
        Check if a phone number belongs to a business.
        
        Args:
            phone: Phone number to check (any format)
            societe: Company name from input data for fuzzy matching
            
        Returns:
            BusinessCheckResult with status and details
        """
        if not self.api_key:
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.UNKNOWN,
                error="Serper API key not configured"
            )
        
        self._current_societe = societe.strip() if societe else ""
        
        try:
            # Use just the phone number for Places search
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                "q": phone,
                "gl": "ca",
                "autocorrect": False
            }
            
            logger.info(f"Searching Serper Places for: {phone}")
            
            response = requests.post(
                self.SERPER_PLACES_URL,
                headers=headers,
                json=payload,
                timeout=15
            )
            
            if response.status_code != 200:
                logger.error(f"Serper API error: {response.status_code} - {response.text}")
                return BusinessCheckResult(
                    phone=phone,
                    status=BusinessStatus.UNKNOWN,
                    error=f"API error: {response.status_code}"
                )
            
            data = response.json()
            
            return self._analyze_results(phone, data, self._current_societe)
            
        except requests.Timeout:
            logger.error(f"Serper API timeout for {phone}")
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.UNKNOWN,
                error="API timeout"
            )
        except Exception as e:
            logger.error(f"Serper API error: {e}")
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.UNKNOWN,
                error=str(e)
            )
    
    @staticmethod
    def _fuzzy_match(text1: str, text2: str) -> float:
        """
        Simple fuzzy matching between two strings.
        Returns a score from 0-100.
        """
        if not text1 or not text2:
            return 0.0
        
        t1 = text1.lower().strip()
        t2 = text2.lower().strip()
        
        # Exact match
        if t1 == t2:
            return 100.0
        
        # One contains the other
        if t1 in t2 or t2 in t1:
            return 85.0
        
        # Word-level matching
        words1 = set(t1.split())
        words2 = set(t2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Remove common words that don't help matching
        stop_words = {'inc', 'ltd', 'llc', 'corp', 'the', 'and', 'of', 'a', 'an'}
        words1 = words1 - stop_words
        words2 = words2 - stop_words
        
        if not words1 or not words2:
            return 0.0
        
        common = words1.intersection(words2)
        score = (len(common) / max(len(words1), len(words2))) * 100
        
        return score
    
    def _analyze_results(self, phone: str, data: dict, societe: str = "") -> BusinessCheckResult:
        """
        Analyze Serper Places API results to determine if phone is a business.
        
        Simple logic: If Places API returns results -> Office, if no results -> Cell.
        
        Args:
            phone: Original phone number
            data: Serper Places API response data
            societe: Company name (unused)
            
        Returns:
            BusinessCheckResult
        """
        places = data.get('places', [])
        
        if places:
            # Found a place listing -> Office
            place = places[0]
            place_name = place.get('title', 'Unknown Business')
            address = place.get('address', '')
            
            logger.info(f"Found place for {phone}: {place_name} -> Office")
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.IS_BUSINESS,
                business_name=place_name,
                source=f"Google Places: {address}" if address else "Google Places",
                match_score=95.0
            )
        else:
            # No place results -> Cell
            logger.info(f"No places found for {phone} -> Cell")
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.NOT_BUSINESS,
                source="No place listing found",
                match_score=90.0
            )
