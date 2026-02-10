"""
Output processing module.
Handles result aggregation and file generation.
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

from .browser_automation import VerificationResult, VerificationStatus
from .business_checker import BusinessCheckResult, BusinessStatus

logger = logging.getLogger(__name__)


class OutputProcessor:
    """Handles output file generation with verification results."""
    
    def __init__(self, original_df: pd.DataFrame):
        """
        Initialize with original DataFrame.
        
        Args:
            original_df: Original input DataFrame to preserve
        """
        self.original_df = original_df.copy()
        self.results: Dict[int, List[dict]] = {}
        self.business_results: Dict[int, List[dict]] = {}
    
    def add_result(self, row_index: int, phone: str, source_type: str, 
                   result: VerificationResult, business_result: Optional[BusinessCheckResult] = None):
        """
        Add verification result for a row.
        
        Args:
            row_index: Original DataFrame row index
            phone: Phone number verified
            source_type: 'Cell' or 'Office'
            result: VerificationResult from automation
            business_result: Optional BusinessCheckResult from Serper
        """
        if row_index not in self.results:
            self.results[row_index] = []
        
        self.results[row_index].append({
            'phone': phone,
            'source_type': source_type,
            'status': result.status.value,
            'error': result.error
        })
        
        if business_result:
            if row_index not in self.business_results:
                self.business_results[row_index] = []
            self.business_results[row_index].append({
                'phone': phone,
                'is_business': business_result.status.value,
                'business_name': business_result.business_name,
                'match_score': business_result.match_score,
                'societe_matched': business_result.societe_matched
            })
        
        logger.info(f"Row {row_index}: {phone} -> {result.status.value}")
    
    # Expected output column order
    OUTPUT_COLUMNS = [
        'Prénom', 'Nom', 'Société', 'Titre', 'Téléphone', 
        'Cell or Office', 'LNNTE', 'Certainty', 'ext', 'Portable', 
        'E-mail', 'Email Secondaire', 'Barreau', 'Année Graduation'
    ]
    
    def _calculate_certainty(self, lnnte_status: str, cell_or_office: str, match_score: float) -> int:
        """
        Calculate certainty percentage for whether phone is callable.
        
        Rules:
        - Phone is CALLABLE if: Not on LNNTE list AND is personal (Cell)
        - High certainty = more confident the phone is callable
        
        Args:
            lnnte_status: 'On list', 'Not on list', or 'Unknown'
            cell_or_office: 'Cell', 'Office', or ''
            match_score: Business match score from Serper (0-100)
            
        Returns:
            Certainty percentage (0-100)
        """
        certainty = 50  # Base certainty
        
        # LNNTE status impact
        if lnnte_status == VerificationStatus.NOT_ON_LIST.value:
            certainty += 30  # Good - not on do-not-call list
        elif lnnte_status == VerificationStatus.ON_LIST.value:
            certainty -= 40  # Bad - on do-not-call list, cannot call
        # Unknown leaves certainty at base
        
        # Cell/Office impact
        if cell_or_office == 'Cell':
            certainty += 20  # Good - personal phone, can call
        elif cell_or_office == 'Office':
            certainty -= 20  # Bad - business phone, should not cold call
        
        # Match score impact (how confident we are about Cell/Office determination)
        if match_score >= 80:
            # High confidence in our Cell/Office determination
            pass  # No adjustment needed
        elif match_score >= 50:
            # Medium confidence - slight reduction
            certainty -= 5
        elif match_score > 0:
            # Low confidence
            certainty -= 10
        
        # Clamp to 0-100
        return max(0, min(100, certainty))
    
    def build_output_dataframe(self) -> pd.DataFrame:
        """
        Build output DataFrame with original columns plus result columns.
        
        Returns:
            DataFrame with columns in specified order plus Cell or Office, LNNTE columns
        """
        output_df = self.original_df.copy()
        
        # Ensure all required columns exist
        for col in self.OUTPUT_COLUMNS:
            if col not in output_df.columns:
                output_df[col] = ''
        
        # Initialize result columns
        output_df['Cell or Office'] = ''
        output_df['LNNTE'] = ''
        output_df['Certainty'] = ''
        
        for row_index, results_list in self.results.items():
            if row_index in output_df.index:
                statuses = []
                
                for r in results_list:
                    statuses.append(r['status'])
                
                if VerificationStatus.ON_LIST.value in statuses:
                    final_status = VerificationStatus.ON_LIST.value
                elif all(s == VerificationStatus.NOT_ON_LIST.value for s in statuses):
                    final_status = VerificationStatus.NOT_ON_LIST.value
                else:
                    final_status = VerificationStatus.UNKNOWN.value
                
                output_df.at[row_index, 'LNNTE'] = final_status
        
        # Determine Cell or Office based on Serper business check results
        # Business = Office (business phone), Not Business = Cell (personal phone)
        for row_index, business_list in self.business_results.items():
            if row_index in output_df.index:
                business_statuses = [b['is_business'] for b in business_list]
                match_scores = [b.get('match_score', 0) for b in business_list]
                best_match_score = max(match_scores) if match_scores else 0
                
                if BusinessStatus.IS_BUSINESS.value in business_statuses:
                    output_df.at[row_index, 'Cell or Office'] = 'Office'
                elif all(s == BusinessStatus.NOT_BUSINESS.value for s in business_statuses):
                    output_df.at[row_index, 'Cell or Office'] = 'Cell'
                # Leave empty if unknown/not checked
                
                # Calculate Certainty based on LNNTE status and Cell/Office
                # Callable = Not on list + Cell (personal) = HIGH certainty
                # Not callable = On list OR Office = certainty varies
                lnnte_status = output_df.at[row_index, 'LNNTE']
                cell_or_office = output_df.at[row_index, 'Cell or Office']
                
                certainty = self._calculate_certainty(
                    lnnte_status, cell_or_office, best_match_score
                )
                output_df.at[row_index, 'Certainty'] = f"{certainty}%"
        
        # Reorder columns: OUTPUT_COLUMNS first, then any extra columns from input
        final_columns = self.OUTPUT_COLUMNS.copy()
        for col in output_df.columns:
            if col not in final_columns:
                final_columns.append(col)
        
        # Only include columns that exist in output_df
        final_columns = [c for c in final_columns if c in output_df.columns]
        
        return output_df[final_columns]
    
    def save_output(self, output_path: str, format: str = 'csv') -> str:
        """
        Save results to file.
        
        Args:
            output_path: Base path for output file
            format: 'csv' or 'excel'
            
        Returns:
            Actual path of saved file
        """
        output_df = self.build_output_dataframe()
        
        path = Path(output_path)
        
        if format.lower() == 'excel':
            if path.suffix.lower() not in ['.xlsx', '.xls']:
                path = path.with_suffix('.xlsx')
            output_df.to_excel(path, index=False)
        else:
            if path.suffix.lower() != '.csv':
                path = path.with_suffix('.csv')
            output_df.to_csv(path, index=False)
        
        logger.info(f"Saved output to: {path}")
        return str(path)
    
    @staticmethod
    def generate_output_filename(input_path: str, suffix: str = "_verified") -> str:
        """
        Generate output filename based on input filename.
        
        Args:
            input_path: Original input file path
            suffix: Suffix to add before extension
            
        Returns:
            Generated output path
        """
        path = Path(input_path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        new_name = f"{path.stem}{suffix}_{timestamp}{path.suffix}"
        return str(path.parent / new_name)
    
    def get_summary(self) -> dict:
        """
        Get summary statistics of verification results.
        
        Returns:
            Dict with counts for each status
        """
        summary = {
            'total_rows': len(self.original_df),
            'verified_rows': len(self.results),
            'on_list': 0,
            'not_on_list': 0,
            'unknown': 0
        }
        
        for row_index, results_list in self.results.items():
            statuses = [r['status'] for r in results_list]
            
            if VerificationStatus.ON_LIST.value in statuses:
                summary['on_list'] += 1
            elif all(s == VerificationStatus.NOT_ON_LIST.value for s in statuses):
                summary['not_on_list'] += 1
            else:
                summary['unknown'] += 1
        
        return summary


class VerificationLog:
    """Handles logging of verification attempts with timestamps."""
    
    def __init__(self, log_path: Optional[str] = None):
        """
        Initialize verification log.
        
        Args:
            log_path: Path to log file (optional)
        """
        self.entries: List[dict] = []
        self.log_path = log_path
    
    def log_attempt(self, phone: str, status: str, error: Optional[str] = None):
        """
        Log a verification attempt.
        
        Args:
            phone: Phone number
            status: Result status
            error: Error message if any
        """
        entry = {
            'timestamp': datetime.now().isoformat(),
            'phone': phone,
            'status': status,
            'error': error or ''
        }
        self.entries.append(entry)
        
        logger.info(f"[{entry['timestamp']}] {phone}: {status}")
    
    def save_log(self, path: Optional[str] = None) -> str:
        """
        Save log to file.
        
        Args:
            path: Override path for log file
            
        Returns:
            Path to saved log file
        """
        log_path = path or self.log_path
        if not log_path:
            log_path = f"verification_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        log_df = pd.DataFrame(self.entries)
        log_df.to_csv(log_path, index=False)
        
        return log_path
    
    def get_entries(self) -> List[dict]:
        """Return all log entries."""
        return self.entries.copy()
