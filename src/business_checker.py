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
    Checks if a phone number belongs to a business using Serper API.
    Searches Google for the phone number and analyzes results.
    """
    
    SERPER_API_URL = "https://google.serper.dev/search"
    
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
            search_query = f'"{phone}"'
            
            headers = {
                'X-API-KEY': self.api_key,
                'Content-Type': 'application/json'
            }
            
            payload = {
                "q": search_query,
                "gl": "ca",
                "hl": "en",
                "num": 10
            }
            
            logger.info(f"Searching Serper for: {phone}")
            
            response = requests.post(
                self.SERPER_API_URL,
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
        Analyze Serper search results to determine if phone is a business.
        
        Args:
            phone: Original phone number
            data: Serper API response data
            societe: Company name from input to fuzzy match
            
        Returns:
            BusinessCheckResult
        """
        organic_results = data.get('organic', [])
        knowledge_graph = data.get('knowledgeGraph', {})
        places = data.get('places', [])
        
        best_match_score = 0.0
        societe_matched = False
        
        if places:
            place = places[0]
            place_name = place.get('title', '')
            
            if societe:
                match_score = self._fuzzy_match(societe, place_name)
                if match_score >= 50:
                    societe_matched = True
                    best_match_score = max(best_match_score, match_score)
            
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.IS_BUSINESS,
                business_name=place_name,
                source="Google Places",
                match_score=best_match_score if societe_matched else 70.0,
                societe_matched=societe_matched
            )
        
        if knowledge_graph:
            title = knowledge_graph.get('title', '')
            kg_type = knowledge_graph.get('type', '').lower()
            
            if societe:
                match_score = self._fuzzy_match(societe, title)
                if match_score >= 50:
                    societe_matched = True
                    best_match_score = max(best_match_score, match_score)
            
            business_types = ['company', 'business', 'organization', 'corporation', 
                           'store', 'restaurant', 'service', 'shop']
            
            if any(bt in kg_type for bt in business_types):
                return BusinessCheckResult(
                    phone=phone,
                    status=BusinessStatus.IS_BUSINESS,
                    business_name=title,
                    source="Knowledge Graph",
                    match_score=best_match_score if societe_matched else 65.0,
                    societe_matched=societe_matched
                )
        
        if organic_results:
            business_indicators = [
                'business', 'company', 'inc', 'ltd', 'corp', 'llc',
                'store', 'shop', 'restaurant', 'service', 'clinic',
                'office', 'agency', 'firm', 'group', 'solutions',
                'contact us', 'call us', 'our phone', 'reach us',
                'hours of operation', 'business hours'
            ]
            
            # Check for société match in organic results
            for result in organic_results[:5]:
                result_title = result.get('title', '')
                result_snippet = result.get('snippet', '')
                
                if societe:
                    title_match = self._fuzzy_match(societe, result_title)
                    snippet_match = self._fuzzy_match(societe, result_snippet)
                    match_score = max(title_match, snippet_match)
                    
                    if match_score >= 50:
                        societe_matched = True
                        best_match_score = max(best_match_score, match_score)
            
            for result in organic_results[:5]:
                title = result.get('title', '').lower()
                snippet = result.get('snippet', '').lower()
                link = result.get('link', '').lower()
                
                combined_text = f"{title} {snippet} {link}"
                
                matches = sum(1 for ind in business_indicators if ind in combined_text)
                
                if matches >= 2:
                    return BusinessCheckResult(
                        phone=phone,
                        status=BusinessStatus.IS_BUSINESS,
                        business_name=result.get('title'),
                        source="Organic Search",
                        match_score=best_match_score if societe_matched else 60.0,
                        societe_matched=societe_matched
                    )
            
            # If société matched but no strong business indicators, still mark as business
            if societe_matched:
                return BusinessCheckResult(
                    phone=phone,
                    status=BusinessStatus.IS_BUSINESS,
                    business_name=organic_results[0].get('title') if organic_results else societe,
                    source="Société Match",
                    match_score=best_match_score,
                    societe_matched=True
                )
            
            # Has search results but no société match - likely personal
            return BusinessCheckResult(
                phone=phone,
                status=BusinessStatus.NOT_BUSINESS,
                source="No Société Match",
                match_score=30.0,
                societe_matched=False
            )
        
        # No search results - likely personal phone
        return BusinessCheckResult(
            phone=phone,
            status=BusinessStatus.NOT_BUSINESS,
            source="No search results",
            match_score=20.0,
            societe_matched=False
        )
