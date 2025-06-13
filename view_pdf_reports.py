#!/usr/bin/env python3
"""
PDF Content Viewer for Production Sensor Reports
================================================

This script provides tools to analyze and view the content of generated PDF reports,
including metadata extraction, chart analysis, and content verification.

Author: Hot Durham Project
Date: June 2025
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PDFContentViewer:
    """PDF content analysis and viewing tools."""
    
    def __init__(self, project_root: str = None):
        if project_root is None:
            self.project_root = Path(__file__).parent
        else:
            self.project_root = Path(project_root)
        
        self.pdf_dir = self.project_root / "sensor_visualizations" / "production_pdf_reports"
        
    def list_available_pdfs(self):
        """List all available PDF reports."""
        if not self.pdf_dir.exists():
            print("❌ PDF reports directory not found")
            return []
        
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        print(f"📄 Available PDF Reports ({len(pdf_files)} found)")
        print("=" * 60)
        
        pdf_info = []
        for i, pdf_file in enumerate(sorted(pdf_files, key=lambda x: x.stat().st_mtime, reverse=True)):
            file_stats = pdf_file.stat()
            size_mb = file_stats.st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(file_stats.st_mtime)
            
            info = {
                'index': i + 1,
                'filename': pdf_file.name,
                'path': str(pdf_file),
                'size_mb': size_mb,
                'modified': modified,
                'age_hours': (datetime.now() - modified).total_seconds() / 3600
            }
            
            pdf_info.append(info)
            
            print(f"  {i+1:2d}. {pdf_file.name}")
            print(f"      Size: {size_mb:.2f} MB")
            print(f"      Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')} ({info['age_hours']:.1f}h ago)")
            print()
        
        return pdf_info
    
    def analyze_latest_report(self):
        """Analyze the most recent PDF report."""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        if not pdf_files:
            print("❌ No PDF reports found")
            return None
        
        # Get the most recent file
        latest_pdf = max(pdf_files, key=lambda x: x.stat().st_mtime)
        
        print(f"🔍 Analyzing Latest Report: {latest_pdf.name}")
        print("=" * 60)
        
        return self.analyze_pdf_file(latest_pdf)
    
    def analyze_pdf_file(self, pdf_path):
        """Analyze a specific PDF file."""
        pdf_file = Path(pdf_path)
        
        if not pdf_file.exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return None
        
        # Basic file information
        file_stats = pdf_file.stat()
        size_mb = file_stats.st_size / (1024 * 1024)
        modified = datetime.fromtimestamp(file_stats.st_mtime)
        
        analysis = {
            'filename': pdf_file.name,
            'path': str(pdf_file),
            'size_bytes': file_stats.st_size,
            'size_mb': size_mb,
            'modified': modified,
            'analysis_time': datetime.now()
        }
        
        # Determine if this is a substantial report or error report
        is_substantial = size_mb > 0.1  # More than 100KB suggests real content
        is_large_report = size_mb > 5.0  # More than 5MB suggests full charts
        
        analysis['content_type'] = 'full_report' if is_large_report else 'error_report' if not is_substantial else 'partial_report'
        analysis['estimated_charts'] = 'many' if is_large_report else 'few' if is_substantial else 'none'
        
        print(f"📊 File Analysis:")
        print(f"  Filename: {pdf_file.name}")
        print(f"  Size: {size_mb:.2f} MB ({file_stats.st_size:,} bytes)")
        print(f"  Modified: {modified.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Content Type: {analysis['content_type']}")
        print(f"  Estimated Charts: {analysis['estimated_charts']}")
        
        # Try to extract metadata from filename
        if 'production_sensors_report_' in pdf_file.name:
            timestamp_part = pdf_file.name.replace('production_sensors_report_', '').replace('.pdf', '')
            try:
                report_time = datetime.strptime(timestamp_part, '%Y%m%d_%H%M%S')
                analysis['report_timestamp'] = report_time
                print(f"  Report Generated: {report_time.strftime('%Y-%m-%d %H:%M:%S')}")
            except ValueError:
                analysis['report_timestamp'] = None
        
        # Check for generation info file
        info_file = pdf_file.parent / "last_generation_info.json"
        if info_file.exists():
            try:
                with open(info_file, 'r') as f:
                    gen_info = json.load(f)
                analysis['generation_info'] = gen_info
                
                print(f"\n📋 Generation Info:")
                print(f"  Sensors: {gen_info.get('sensor_count', 'Unknown')}")
                print(f"  Average Uptime: {gen_info.get('average_uptime', 'Unknown')}")
                print(f"  Period: {gen_info.get('report_period', 'Unknown')}")
                print(f"  Google Drive: {gen_info.get('uploaded_to_drive', 'Unknown')}")
                
            except Exception as e:
                print(f"  ⚠️ Could not read generation info: {e}")
        
        return analysis
    
    def open_pdf_viewer(self, pdf_path=None):
        """Open PDF in system default viewer."""
        if pdf_path is None:
            # Get latest PDF
            pdf_files = list(self.pdf_dir.glob("*.pdf"))
            if not pdf_files:
                print("❌ No PDF reports found")
                return False
            pdf_path = max(pdf_files, key=lambda x: x.stat().st_mtime)
        
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            print(f"❌ PDF file not found: {pdf_path}")
            return False
        
        try:
            import subprocess
            if sys.platform == "darwin":  # macOS
                subprocess.run(["open", str(pdf_file)])
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(pdf_file)])
            elif sys.platform == "win32":
                os.startfile(str(pdf_file))
            else:
                print(f"⚠️ Unsupported platform for auto-opening: {sys.platform}")
                return False
            
            print(f"📖 Opened PDF viewer for: {pdf_file.name}")
            return True
            
        except Exception as e:
            print(f"❌ Error opening PDF viewer: {e}")
            return False
    
    def compare_reports(self, limit=5):
        """Compare recent reports to show trends."""
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        if len(pdf_files) < 2:
            print("❌ Need at least 2 reports for comparison")
            return
        
        # Sort by modification time (newest first)
        pdf_files = sorted(pdf_files, key=lambda x: x.stat().st_mtime, reverse=True)[:limit]
        
        print(f"📈 Report Comparison (Last {len(pdf_files)} Reports)")
        print("=" * 60)
        
        comparisons = []
        for pdf_file in pdf_files:
            file_stats = pdf_file.stat()
            size_mb = file_stats.st_size / (1024 * 1024)
            modified = datetime.fromtimestamp(file_stats.st_mtime)
            
            # Try to get generation info
            gen_info = {}
            info_file = pdf_file.parent / "last_generation_info.json"
            if info_file.exists() and pdf_file == pdf_files[0]:  # Only for latest
                try:
                    with open(info_file, 'r') as f:
                        gen_info = json.load(f)
                except:
                    pass
            
            comparison = {
                'filename': pdf_file.name,
                'size_mb': size_mb,
                'modified': modified,
                'generation_info': gen_info
            }
            comparisons.append(comparison)
            
            status = "📊 Full" if size_mb > 5 else "⚠️ Partial" if size_mb > 0.1 else "❌ Error"
            print(f"  {modified.strftime('%m/%d %H:%M')} | {size_mb:6.2f} MB | {status}")
        
        # Show trends
        if len(comparisons) >= 2:
            latest_size = comparisons[0]['size_mb']
            previous_size = comparisons[1]['size_mb']
            size_change = latest_size - previous_size
            
            print(f"\n📊 Trends:")
            print(f"  Size Change: {size_change:+.2f} MB from previous report")
            
            if latest_size > 5:
                print(f"  Status: ✅ Generating full reports with charts")
            elif latest_size > 0.1:
                print(f"  Status: ⚠️ Partial reports - may be missing data")
            else:
                print(f"  Status: ❌ Error reports - system needs attention")
        
        return comparisons
    
    def show_menu(self):
        """Show interactive menu."""
        while True:
            print("\n🔍 PDF Content Viewer - Hot Durham Production Reports")
            print("=" * 60)
            print("1. List all available PDF reports")
            print("2. Analyze latest report")
            print("3. Open latest report in viewer")
            print("4. Compare recent reports")
            print("5. Analyze specific report")
            print("6. Open specific report")
            print("0. Exit")
            
            try:
                choice = input("\nSelect option (0-6): ").strip()
                
                if choice == "0":
                    print("👋 Goodbye!")
                    break
                elif choice == "1":
                    self.list_available_pdfs()
                elif choice == "2":
                    self.analyze_latest_report()
                elif choice == "3":
                    self.open_pdf_viewer()
                elif choice == "4":
                    self.compare_reports()
                elif choice == "5":
                    pdf_files = self.list_available_pdfs()
                    if pdf_files:
                        try:
                            index = int(input(f"Enter report number (1-{len(pdf_files)}): "))
                            if 1 <= index <= len(pdf_files):
                                self.analyze_pdf_file(pdf_files[index-1]['path'])
                            else:
                                print("❌ Invalid selection")
                        except ValueError:
                            print("❌ Please enter a valid number")
                elif choice == "6":
                    pdf_files = self.list_available_pdfs()
                    if pdf_files:
                        try:
                            index = int(input(f"Enter report number (1-{len(pdf_files)}): "))
                            if 1 <= index <= len(pdf_files):
                                self.open_pdf_viewer(pdf_files[index-1]['path'])
                            else:
                                print("❌ Invalid selection")
                        except ValueError:
                            print("❌ Please enter a valid number")
                else:
                    print("❌ Invalid option")
                    
                input("\nPress Enter to continue...")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
                input("Press Enter to continue...")

def main():
    """Main function."""
    try:
        viewer = PDFContentViewer()
        
        # If command line arguments provided, run specific function
        if len(sys.argv) > 1:
            command = sys.argv[1].lower()
            if command == "list":
                viewer.list_available_pdfs()
            elif command == "analyze":
                viewer.analyze_latest_report()
            elif command == "open":
                viewer.open_pdf_viewer()
            elif command == "compare":
                viewer.compare_reports()
            else:
                print(f"❌ Unknown command: {command}")
                print("Available commands: list, analyze, open, compare")
                return 1
        else:
            # Interactive mode
            viewer.show_menu()
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
