"""
Data validation framework for sensor data
"""
import pandas as pd
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class ValidationResult:
    """Result of data validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_count: int = 0

class SensorDataValidator:
    """Comprehensive sensor data validation"""
    
    def __init__(self):
        self.tsi_required_columns = ['timestamp', 'device_name', 'mcpm2x5']
        self.wu_required_columns = ['stationID', 'obsTimeUtc', 'tempAvg']
    
    def validate_tsi_data(self, df: pd.DataFrame) -> ValidationResult:
        """Validate TSI sensor data"""
        errors = []
        warnings = []
        original_count = len(df)
        
        # Check required columns
        missing_cols = set(self.tsi_required_columns) - set(df.columns)
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Validate timestamps
        if 'timestamp' in df.columns:
            invalid_timestamps = df['timestamp'].isna().sum()
            if invalid_timestamps > 0:
                warnings.append(f"Found {invalid_timestamps} invalid timestamps")
                df = df.dropna(subset=['timestamp'])
        
        # Validate PM2.5 values
        if 'mcpm2x5' in df.columns:
            invalid_pm25 = (df['mcpm2x5'] < 0) | (df['mcpm2x5'] > 1000)
            if invalid_pm25.any():
                count = invalid_pm25.sum()
                warnings.append(f"Found {count} invalid PM2.5 values (< 0 or > 1000)")
                df = df[~invalid_pm25]
        
        cleaned_count = original_count - len(df)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cleaned_count=cleaned_count
        )
    
    def validate_wu_data(self, df: pd.DataFrame) -> ValidationResult:
        """Validate Weather Underground data"""
        errors = []
        warnings = []
        original_count = len(df)
        
        # Check required columns
        missing_cols = set(self.wu_required_columns) - set(df.columns)
        if missing_cols:
            errors.append(f"Missing required columns: {missing_cols}")
        
        # Validate temperature ranges
        if 'tempAvg' in df.columns:
            invalid_temp = (df['tempAvg'] < -50) | (df['tempAvg'] > 60)
            if invalid_temp.any():
                count = invalid_temp.sum()
                warnings.append(f"Found {count} extreme temperature values")
                df = df[~invalid_temp]
        
        cleaned_count = original_count - len(df)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cleaned_count=cleaned_count
        )
    
    def detect_duplicates(self, df: pd.DataFrame, subset: List[str]) -> Tuple[pd.DataFrame, int]:
        """Detect and remove duplicates"""
        initial_count = len(df)
        df_cleaned = df.drop_duplicates(subset=subset)
        duplicates_removed = initial_count - len(df_cleaned)
        return df_cleaned, duplicates_removed
