#!/usr/bin/env python3
"""
Production Sensor PDF Report Generator - Standalone Script
==========================================================

This script generates comprehensive PDF reports for production sensors using the 
Central Asian Data Center PDF system methodology. It integrates with your existing
data collection workflow and can be run manually or automated.

Features:
- Automatically detects and loads production sensor data
- Generates comprehensive PDF reports with charts and analysis
- Calculates sensor uptime and performance metrics
- Creates summary visualizations and individual sensor reports
- Uploads reports to Google Drive (optional)
- Saves reports locally for backup

Usage:
    python generate_production_pdf_report.py [options]

Options:
    --days-back N     : Number of days to include in analysis (default: 16)
    --upload-drive    : Upload report to Google Drive
    --no-upload       : Skip Google Drive upload
    --output-dir PATH : Custom output directory
    --verbose         : Enable verbose logging

Author: Hot Durham Project
Date: June 2025
"""

import sys
import os
import argparse
from pathlib import Path
from datetime import datetime
import logging

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src'))

# Import the PDF reporter
from src.visualization.production_pdf_reports import ProductionSensorPDFReporter

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(project_root / 'logs' / 'pdf_report_generation.log')
        ]
    )
    
    return logging.getLogger(__name__)

def upload_to_google_drive(pdf_path: str, logger) -> bool:
    """
    Upload PDF report to Google Drive.
    
    Args:
        pdf_path: Path to the PDF file
        logger: Logger instance
        
    Returns:
        True if upload successful, False otherwise
    """
    try:
        # Import data manager for Google Drive functionality
        from src.core.data_manager import DataManager
        
        data_manager = DataManager(project_root)
        
        # Upload to production sensor reports folder
        drive_folder = "HotDurham/Production/Reports"
        
        logger.info(f"Uploading PDF report to Google Drive: {drive_folder}")
        
        # Use the data manager's upload functionality
        success = data_manager.upload_to_drive(
            local_path=Path(pdf_path),
            drive_folder=drive_folder
        )
        
        if success:
            logger.info("✅ PDF report uploaded to Google Drive successfully")
            return True
        else:
            logger.warning("⚠️ Failed to upload PDF report to Google Drive")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error uploading to Google Drive: {e}")
        return False

def main():
    """Main function to generate production sensor PDF report."""
    parser = argparse.ArgumentParser(
        description="Generate comprehensive PDF reports for Hot Durham production sensors"
    )
    
    parser.add_argument(
        '--days-back',
        type=int,
        default=16,
        help='Number of days to include in analysis (default: 16)'
    )
    
    parser.add_argument(
        '--upload-drive',
        action='store_true',
        help='Upload report to Google Drive'
    )
    
    parser.add_argument(
        '--no-upload',
        action='store_true',
        help='Skip Google Drive upload (overrides --upload-drive)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        help='Custom output directory for PDF reports'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    print("🏭 Hot Durham Production Sensor PDF Report Generator")
    print("=" * 65)
    print(f"📅 Report Period: Last {args.days_back} days")
    print(f"📁 Project Root: {project_root}")
    
    try:
        # Ensure logs directory exists
        (project_root / 'logs').mkdir(exist_ok=True)
        
        # Initialize the PDF reporter
        logger.info("Initializing PDF reporter...")
        reporter = ProductionSensorPDFReporter(project_root)
        
        # Set custom output directory if provided
        if args.output_dir:
            reporter.output_dir = Path(args.output_dir)
            reporter.output_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Using custom output directory: {reporter.output_dir}")
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"production_sensors_report_{timestamp}.pdf"
        
        # Generate the PDF report
        logger.info("🔄 Loading production sensor data...")
        print("📊 Loading production sensor data...")
        
        if not reporter.load_production_data():
            print("❌ Failed to load production sensor data")
            logger.error("Failed to load production sensor data")
            return 1
        
        logger.info("📈 Calculating sensor metrics and generating charts...")
        print("📈 Calculating sensor metrics and generating charts...")
        
        # Generate the PDF report
        pdf_path = reporter.generate_pdf_report(filename)
        
        if not os.path.exists(pdf_path):
            print("❌ Failed to generate PDF report")
            logger.error("PDF report file not found after generation")
            return 1
        
        print(f"✅ PDF report generated successfully!")
        print(f"📄 Report location: {pdf_path}")
        
        # Log summary statistics
        total_sensors = len(reporter.uptime_data)
        avg_uptime = sum(reporter.uptime_data.values()) / len(reporter.uptime_data) if reporter.uptime_data else 0
        high_uptime_sensors = len([u for u in reporter.uptime_data.values() if u >= 90])
        
        print(f"\n📊 Report Summary:")
        print(f"   - Total production sensors: {total_sensors}")
        print(f"   - Average network uptime: {avg_uptime:.1f}%")
        print(f"   - Sensors with >90% uptime: {high_uptime_sensors}")
        print(f"   - Report period: {reporter.get_period(args.days_back)}")
        
        logger.info(f"Report generated - {total_sensors} sensors, {avg_uptime:.1f}% avg uptime")
        
        # Upload to Google Drive if requested
        upload_success = False
        
        if args.upload_drive and not args.no_upload:
            print("\n☁️ Uploading to Google Drive...")
            upload_success = upload_to_google_drive(pdf_path, logger)
        elif not args.no_upload:
            # Ask user if they want to upload
            try:
                upload_choice = input("\n☁️ Upload report to Google Drive? (y/n): ").lower().strip()
                if upload_choice in ['y', 'yes']:
                    upload_success = upload_to_google_drive(pdf_path, logger)
            except (KeyboardInterrupt, EOFError):
                print("\n⏭️ Skipping Google Drive upload")
        
        # Final summary
        print(f"\n🎉 Production sensor PDF report generation complete!")
        print(f"📁 Local file: {pdf_path}")
        
        if upload_success:
            print(f"☁️ Google Drive: Successfully uploaded")
        
        # Save generation info for automation tracking
        info_file = reporter.output_dir / "last_generation_info.json"
        generation_info = {
            "timestamp": datetime.now().isoformat(),
            "pdf_path": str(pdf_path),
            "total_sensors": total_sensors,
            "average_uptime": avg_uptime,
            "high_uptime_sensors": high_uptime_sensors,
            "uploaded_to_drive": upload_success,
            "report_period_days": args.days_back
        }
        
        import json
        with open(info_file, 'w') as f:
            json.dump(generation_info, f, indent=2)
        
        logger.info(f"Generation info saved to: {info_file}")
        
        return 0
        
    except KeyboardInterrupt:
        print("\n⏹️ Report generation cancelled by user")
        logger.info("Report generation cancelled by user")
        return 1
        
    except Exception as e:
        print(f"❌ Error generating PDF report: {e}")
        logger.error(f"Error generating PDF report: {e}", exc_info=True)
        return 1

if __name__ == "__main__":
    exit(main())
