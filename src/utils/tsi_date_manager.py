#!/usr/bin/env python3
"""
TSI API 90-Day Limitation Handler

This module provides utilities to handle the TSI API's 90-day historical data limitation.
It includes functions to:
1. Check if a date range exceeds the 90-day limit
2. Split date ranges into 90-day chunks
3. Provide adjusted date ranges that work with the TSI API
"""

from datetime import datetime, timedelta
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)

class TSIDateRangeManager:
    """Manages date ranges for TSI API calls to respect the 90-day limitation."""
    
    # TSI API limitation: start_date cannot be more than 90 days in the past
    # This is different from a 90-day span limit - it's about how far back the start date can be
    MAX_DAYS_BACK_TSI = 90
    
    @classmethod
    def is_within_limit(cls, start_date: str, end_date: str) -> bool:
        """Check if the start date is within TSI's 90-day historical limit."""
        try:
            start_dt = cls._parse_date(start_date)
            today = datetime.now()
            
            # Check if start date is more than 90 days in the past
            days_back = (today - start_dt).days
            return days_back <= cls.MAX_DAYS_BACK_TSI
        except Exception as e:
            logger.error(f"Error checking date range: {e}")
            return False
    
    @classmethod
    def get_days_back_from_start(cls, start_date: str) -> int:
        """Get the number of days the start date is in the past from today."""
        try:
            start_dt = cls._parse_date(start_date)
            today = datetime.now()
            return (today - start_dt).days
        except Exception:
            return 0
    
    @classmethod
    def get_days_difference(cls, start_date: str, end_date: str) -> int:
        """Get the number of days between two dates."""
        try:
            start_dt = cls._parse_date(start_date)
            end_dt = cls._parse_date(end_date)
            return (end_dt - start_dt).days
        except Exception:
            return 0
    
    @classmethod
    def split_date_range(cls, start_date: str, end_date: str) -> List[Tuple[str, str]]:
        """Split a date range into chunks that respect TSI's start date limitation."""
        start_dt = cls._parse_date(start_date)
        end_dt = cls._parse_date(end_date)
        today = datetime.now()
        
        # For TSI API, we can only fetch data where the start date is within 90 days of today
        earliest_allowed_start = today - timedelta(days=cls.MAX_DAYS_BACK_TSI)
        
        # If the entire range is too old, return the most recent valid range
        if start_dt < earliest_allowed_start and end_dt < earliest_allowed_start:
            # Both dates are too old, return the most recent valid range
            valid_start = earliest_allowed_start
            # valid_end = min(today, end_dt + timedelta(days=(today - end_dt).days))
            return [(valid_start.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))]
        
        chunks = []
        
        # Adjust start date if it's too far back
        effective_start = max(start_dt, earliest_allowed_start)
        
        # If the adjusted start is after the end, we can't fetch this data
        if effective_start > end_dt:
            return []
        
        # For TSI, typically we just need one chunk from the earliest valid start to the end
        chunks.append((
            effective_start.strftime("%Y-%m-%d"),
            end_dt.strftime("%Y-%m-%d")
        ))
        
        return chunks
    
    @classmethod
    def get_recent_valid_range(cls, days_back: int = 89) -> Tuple[str, str]:
        """Get a recent date range that's within TSI's limits."""
        end_date = datetime.now()
        # Ensure we don't go beyond the TSI limit
        days_back = min(days_back, cls.MAX_DAYS_BACK_TSI - 1)
        start_date = end_date - timedelta(days=days_back)
        
        return (
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
    
    @classmethod
    def adjust_date_range_for_tsi(cls, start_date: str, end_date: str, 
                                  prefer_recent: bool = True) -> Tuple[str, str, bool]:
        """
        Adjust date range to work with TSI API.
        
        Returns:
            Tuple of (adjusted_start_date, adjusted_end_date, was_adjusted)
        """
        start_dt = cls._parse_date(start_date)
        end_dt = cls._parse_date(end_date)
        today = datetime.now()
        
        # Check if start date is beyond the 90-day limit
        days_back = (today - start_dt).days
        
        if days_back <= cls.MAX_DAYS_BACK_TSI:
            return start_date, end_date, False
        
        logger.warning(f"Start date {start_date} is {days_back} days back, exceeds TSI's {cls.MAX_DAYS_BACK_TSI}-day limit")
        
        if prefer_recent:
            # Adjust start date to be within the limit, keep end date
            earliest_allowed_start = today - timedelta(days=cls.MAX_DAYS_BACK_TSI)
            adjusted_start_dt = max(earliest_allowed_start, start_dt)
            
            # If the end date is also too far in the past, adjust it to today
            if (today - end_dt).days > cls.MAX_DAYS_BACK_TSI:
                adjusted_end_dt = today
            else:
                adjusted_end_dt = end_dt
            
            adjusted_start = adjusted_start_dt.strftime("%Y-%m-%d")
            adjusted_end = adjusted_end_dt.strftime("%Y-%m-%d")
            
            logger.info(f"Adjusted to recent range: {adjusted_start} to {adjusted_end}")
            return adjusted_start, adjusted_end, True
        else:
            # This case is less useful for TSI since we can't go back beyond 90 days
            # But we'll provide the earliest valid range
            earliest_start = today - timedelta(days=cls.MAX_DAYS_BACK_TSI)
            earliest_end = min(earliest_start + timedelta(days=cls.MAX_DAYS_BACK_TSI), today)
            
            adjusted_start = earliest_start.strftime("%Y-%m-%d")
            adjusted_end = earliest_end.strftime("%Y-%m-%d")
            
            logger.info(f"Adjusted to earliest valid range: {adjusted_start} to {adjusted_end}")
            return adjusted_start, adjusted_end, True
    
    @classmethod
    def _parse_date(cls, date_str: str) -> datetime:
        """Parse date string in various formats."""
        for fmt in ["%Y-%m-%d", "%Y%m%d", "%Y/%m/%d"]:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        raise ValueError(f"Unable to parse date: {date_str}")

def demonstrate_tsi_date_limitations():
    """Demonstrate the TSI date limitation handling."""
    print("🔍 TSI API Date Range Limitation Demo")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        ("2025-03-01", "2025-06-13"),  # Original problematic range (start too far back)
        ("2025-05-01", "2025-06-13"),  # Within limit (start within 90 days)
        ("2024-01-01", "2024-12-31"),  # Very old range (start way too far back)
        ("2025-06-10", "2025-06-13"),  # Recent small range (start within limit)
    ]
    
    manager = TSIDateRangeManager()
    
    for start_date, end_date in test_cases:
        print(f"\n📅 Testing range: {start_date} to {end_date}")
        
        days_back = manager.get_days_back_from_start(start_date)
        days_span = manager.get_days_difference(start_date, end_date)
        print(f"   Start date is {days_back} days back")
        print(f"   Date range span: {days_span} days")
        
        is_valid = manager.is_within_limit(start_date, end_date)
        print(f"   Start within 90-day limit: {'✅ Yes' if is_valid else '❌ No'}")
        
        if not is_valid:
            # Show adjusted range (prefer recent)
            adj_start, adj_end, was_adj = manager.adjust_date_range_for_tsi(start_date, end_date, prefer_recent=True)
            print(f"   Adjusted (recent): {adj_start} to {adj_end}")
            
            # Show chunks
            chunks = manager.split_date_range(start_date, end_date)
            print(f"   Would require {len(chunks)} API calls:")
            for i, (chunk_start, chunk_end) in enumerate(chunks[:3], 1):  # Show first 3 chunks
                chunk_days = manager.get_days_difference(chunk_start, chunk_end)
                chunk_days_back = manager.get_days_back_from_start(chunk_start)
                print(f"     Chunk {i}: {chunk_start} to {chunk_end} ({chunk_days} days, start {chunk_days_back} days back)")
            if len(chunks) > 3:
                print(f"     ... and {len(chunks) - 3} more chunks")
    
    # Show current valid range
    print("\n🕒 Current valid range (last 89 days):")
    recent_start, recent_end = manager.get_recent_valid_range()
    print(f"   {recent_start} to {recent_end}")

if __name__ == "__main__":
    demonstrate_tsi_date_limitations()
