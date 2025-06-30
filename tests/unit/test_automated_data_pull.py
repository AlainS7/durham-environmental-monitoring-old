"""
Unit Tests for the Automated Data Pull Script.

This test suite verifies the correctness of the functions in the refactored
`automated_data_pull.py` script. It focuses on ensuring that the core logic,
such as date range calculations, is reliable and accurate.

Key Tests:
- `test_get_date_range_daily`: Ensures the daily pull fetches yesterday's data.
- `test_get_date_range_weekly`: Validates that the weekly pull covers the correct Monday-Sunday range.
- `test_get_date_range_monthly`: Checks that the monthly pull targets the entire previous month.
"""

import unittest
from datetime import datetime, timedelta
import os
import sys

# Add project root to Python path for module imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, PROJECT_ROOT)

from scripts.automated_data_pull import get_date_range, parse_arguments

class TestAutomatedDataPull(unittest.TestCase):

    def test_get_date_range_daily(self):
        """Verify that the daily date range is always yesterday."""
        yesterday = datetime.now() - timedelta(days=1)
        expected_date = yesterday.strftime('%Y-%m-%d')
        start_date, end_date = get_date_range('daily')
        self.assertEqual(start_date, expected_date)
        self.assertEqual(end_date, expected_date)

    def test_get_date_range_weekly(self):
        """Verify that the weekly date range covers the previous Monday to Sunday."""
        today = datetime.now()
        # Calculate the most recent Monday
        start_of_this_week = today - timedelta(days=today.weekday())
        # The start date should be the Monday of the *previous* week
        expected_start_date = start_of_this_week - timedelta(days=7)
        expected_end_date = expected_start_date + timedelta(days=6)
        
        start_date, end_date = get_date_range('weekly')
        
        self.assertEqual(start_date, expected_start_date.strftime('%Y-%m-%d'))
        self.assertEqual(end_date, expected_end_date.strftime('%Y-%m-%d'))

    def test_get_date_range_monthly(self):
        """Verify that the monthly date range covers the entire previous month."""
        today = datetime.now()
        first_day_of_this_month = today.replace(day=1)
        last_day_of_last_month = first_day_of_this_month - timedelta(days=1)
        first_day_of_last_month = last_day_of_last_month.replace(day=1)
        
        expected_start_date = first_day_of_last_month.strftime('%Y-%m-%d')
        expected_end_date = last_day_of_last_month.strftime('%Y-%m-%d')
        
        start_date, end_date = get_date_range('monthly')
        
        self.assertEqual(start_date, expected_start_date)
        self.assertEqual(end_date, expected_end_date)

    def test_unsupported_pull_type(self):
        """Verify that an unsupported pull type raises a ValueError."""
        with self.assertRaises(ValueError):
            get_date_range('yearly')

    def test_parse_arguments_defaults(self):
        """Verify that default arguments are parsed correctly."""
        sys.argv = ['test_automated_data_pull.py']
        args = parse_arguments()
        self.assertEqual(args.pull_type, 'daily')
        self.assertFalse(args.no_sheets)
        self.assertFalse(args.no_sync)

    def test_parse_arguments_custom(self):
        """Verify that custom arguments are parsed correctly."""
        sys.argv = ['test_automated_data_pull.py', '--pull_type', 'weekly', '--no_sheets', '--no_sync']
        args = parse_arguments()
        self.assertEqual(args.pull_type, 'weekly')
        self.assertTrue(args.no_sheets)
        self.assertTrue(args.no_sync)

if __name__ == '__main__':
    unittest.main()
