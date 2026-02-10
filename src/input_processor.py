"""
Input processing module for CSV/Excel files.
Handles phone number normalization and validation.
"""

import re
import pandas as pd
from pathlib import Path
from typing import Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


class InputProcessor:
    """Handles input file parsing and phone number normalization."""
    
    PHONE_COLUMNS = ['Téléphone', 'Telephone', 'Phone', 'Portable', 'Mobile', 'Cell', 'Office']
    
    def __init__(self):
        self.df: Optional[pd.DataFrame] = None
        self.phone_entries: List[dict] = []
        self.source_file: Optional[Path] = None
    
    def load_file(self, file_path: str) -> pd.DataFrame:
        """
        Load CSV or Excel file and return DataFrame.
        
        Args:
            file_path: Path to input file (CSV or Excel)
            
        Returns:
            pandas DataFrame with original data
            
        Raises:
            ValueError: If file format is not supported
            FileNotFoundError: If file doesn't exist
        """
        path = Path(file_path)
        self.source_file = path
        
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {file_path}")
        
        suffix = path.suffix.lower()
        
        if suffix == '.csv':
            self.df = pd.read_csv(file_path, dtype=str)
            logger.info(f"Loaded CSV file: {file_path} ({len(self.df)} rows)")
        elif suffix in ['.xlsx', '.xls']:
            self.df = pd.read_excel(file_path, dtype=str)
            logger.info(f"Loaded Excel file: {file_path} ({len(self.df)} rows)")
        else:
            raise ValueError(f"Unsupported file format: {suffix}. Use CSV or Excel files.")
        
        self.df = self.df.fillna('')
        return self.df
    
    @staticmethod
    def normalize_phone(phone: str) -> Optional[str]:
        """
        Normalize phone number to format accepted by LNNTÉ (XXX-XXX-XXXX).
        
        Args:
            phone: Raw phone number string
            
        Returns:
            Normalized phone number or None if invalid
        """
        if not phone or not isinstance(phone, str):
            return None
        
        digits = re.sub(r'\D', '', phone)
        
        if len(digits) == 11 and digits.startswith('1'):
            digits = digits[1:]
        
        if len(digits) != 10:
            return None
        
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    
    @staticmethod
    def validate_canadian_phone(phone: str) -> bool:
        """
        Validate that phone number could be Canadian.
        Canadian area codes start with 2-9.
        
        Args:
            phone: Normalized phone number (XXX-XXX-XXXX format)
            
        Returns:
            True if valid Canadian format
        """
        if not phone:
            return False
        
        digits = re.sub(r'\D', '', phone)
        if len(digits) != 10:
            return False
        
        if digits[0] in '01':
            return False
            
        return True
    
    def extract_phone_entries(self) -> List[dict]:
        """
        Extract phone numbers from DataFrame with source column tracking.
        
        Returns:
            List of dicts with row_index, phone, source_column, normalized_phone
        """
        if self.df is None:
            raise ValueError("No file loaded. Call load_file() first.")
        
        self.phone_entries = []
        
        found_columns = [col for col in self.df.columns if col in self.PHONE_COLUMNS]
        
        if not found_columns:
            found_columns = []
            for col in self.df.columns:
                col_lower = col.lower()
                for phone_col in self.PHONE_COLUMNS:
                    if phone_col.lower() in col_lower:
                        found_columns.append(col)
                        break
        
        logger.info(f"Found phone columns: {found_columns}")
        
        for idx, row in self.df.iterrows():
            for col in found_columns:
                raw_phone = str(row.get(col, '')).strip()
                if raw_phone:
                    normalized = self.normalize_phone(raw_phone)
                    if normalized and self.validate_canadian_phone(normalized):
                        source_type = self._determine_source_type(col)
                        self.phone_entries.append({
                            'row_index': idx,
                            'raw_phone': raw_phone,
                            'normalized_phone': normalized,
                            'source_column': col,
                            'source_type': source_type
                        })
                        logger.debug(f"Row {idx}: Found {normalized} in {col} ({source_type})")
        
        logger.info(f"Extracted {len(self.phone_entries)} valid phone numbers")
        return self.phone_entries
    
    def _determine_source_type(self, column_name: str) -> str:
        """
        Determine if phone is Cell or Office based on column name.
        
        Args:
            column_name: Name of the source column
            
        Returns:
            'Cell' or 'Office'
        """
        col_lower = column_name.lower()
        cell_indicators = ['portable', 'mobile', 'cell', 'cellulaire', 'cellular']
        
        for indicator in cell_indicators:
            if indicator in col_lower:
                return 'Cell'
        
        return 'Office'
    
    def get_dataframe(self) -> pd.DataFrame:
        """Return the loaded DataFrame."""
        return self.df
    
    def get_row_count(self) -> int:
        """Return total number of rows in the loaded file."""
        return len(self.df) if self.df is not None else 0
    
    def get_phone_count(self) -> int:
        """Return number of extracted phone entries."""
        return len(self.phone_entries)
