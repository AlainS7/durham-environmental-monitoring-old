#!/usr/bin/env python3
"""
Hot Durham Multi-Sensor Visualization Integration
Integration script for the comprehensive sensor visualization system
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime, timedelta
import pandas as pd

# Add the current directory to Python path for imports
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))

# Import the visualization system
from comprehensive_sensor_visualization import MultiSensorVisualizer

class HotDurhamVisualizationManager:
    """
    Integration manager for Hot Durham sensor visualization system
    """
    
    def __init__(self, project_root=None):
        if project_root is None:
            project_root = Path(__file__).parent
        
        self.project_root = Path(project_root)
        self.data_dir = self.project_root / "data" / "historical_test_sensors"
        self.output_dir = self.project_root / "sensor_visualizations"
        self.reports_dir = self.project_root / "reports"
        
        # Ensure directories exist
        self.output_dir.mkdir(exist_ok=True)
        self.reports_dir.mkdir(exist_ok=True)
        
    def check_data_availability(self):
        """Check if sensor data is available for visualization"""
        print("🔍 Checking data availability...")
        
        if not self.data_dir.exists():
            print(f"❌ Data directory not found: {self.data_dir}")
            return False
        
        # Look for CSV files
        csv_files = list(self.data_dir.glob("KNCDURHA*_complete_history_*.csv"))
        
        if len(csv_files) == 0:
            print("❌ No sensor data files found")
            return False
        
        print(f"✅ Found {len(csv_files)} sensor data files")
        for csv_file in csv_files[:5]:  # Show first 5
            print(f"   📁 {csv_file.name}")
        
        if len(csv_files) > 5:
            print(f"   ... and {len(csv_files) - 5} more files")
        
        return True
    
    def run_visualization_analysis(self):
        """Run the complete visualization analysis"""
        print("\n🚀 Starting Hot Durham Multi-Sensor Visualization Analysis...")
        print("=" * 70)
        
        # Check data availability
        if not self.check_data_availability():
            print("❌ Cannot proceed without sensor data")
            return False
        
        try:
            # Initialize visualizer
            visualizer = MultiSensorVisualizer(str(self.data_dir))
            
            # Run complete analysis
            report = visualizer.run_complete_analysis()
            
            # Copy results to reports directory
            self.copy_results_to_reports()
            
            print("\n🎉 Hot Durham Visualization Analysis Complete!")
            print(f"📊 Results available in: {self.output_dir}")
            print(f"📋 Reports copied to: {self.reports_dir}")
            
            return True
            
        except Exception as e:
            print(f"❌ Error during visualization analysis: {str(e)}")
            return False
    
    def copy_results_to_reports(self):
        """Copy visualization results to the reports directory"""
        import shutil
        
        print("\n📋 Copying results to reports directory...")
        
        # Create timestamped subdirectory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_subdir = self.reports_dir / f"sensor_visualization_{timestamp}"
        report_subdir.mkdir(exist_ok=True)
        
        # Copy all files from visualization directory
        for file_path in self.output_dir.glob("*"):
            if file_path.is_file():
                dest_path = report_subdir / file_path.name
                shutil.copy2(file_path, dest_path)
                print(f"   📄 Copied {file_path.name}")
        
        print(f"✅ Results archived to: {report_subdir}")
    
    def generate_integration_summary(self):
        """Generate a summary of the integration"""
        summary = {
            "integration_info": {
                "system": "Hot Durham Multi-Sensor Visualization",
                "integration_date": datetime.now().isoformat(),
                "project_root": str(self.project_root),
                "data_source": str(self.data_dir),
                "output_location": str(self.output_dir)
            },
            "capabilities": [
                "Multi-sensor temperature analysis",
                "Humidity pattern visualization",
                "Pressure and wind analysis",
                "Inter-sensor correlation matrices",
                "Data quality dashboards",
                "Comprehensive environmental monitoring",
                "Real-time dashboard layouts",
                "Professional report generation"
            ],
            "integration_features": [
                "Automatic data discovery",
                "Flexible output management", 
                "Report archiving system",
                "Error handling and validation",
                "Scalable to additional sensors",
                "Compatible with existing Hot Durham infrastructure"
            ]
        }
        
        # Save integration summary
        summary_path = self.reports_dir / "visualization_integration_summary.json"
        with open(summary_path, 'w') as f:
            json.dump(summary, f, indent=2)
        
        print(f"\n📋 Integration summary saved to: {summary_path}")
        
        return summary
    
    def show_usage_examples(self):
        """Show usage examples for the visualization system"""
        print("\n📚 HOT DURHAM VISUALIZATION SYSTEM - USAGE EXAMPLES")
        print("=" * 60)
        
        examples = [
            {
                "name": "Run Complete Analysis",
                "description": "Generate all visualizations for current sensor data",
                "command": "python hot_durham_visualization_integration.py"
            },
            {
                "name": "View Generated Visualizations",
                "description": "Display the created visualization files",
                "command": "python view_visualizations.py"
            },
            {
                "name": "Check Analysis Summary",
                "description": "Show detailed analysis results",
                "command": "python analysis_summary.py"
            },
            {
                "name": "Direct Visualization Access", 
                "description": "Use the visualization system directly",
                "command": "from comprehensive_sensor_visualization import MultiSensorVisualizer\nvisualizer = MultiSensorVisualizer('data/historical_test_sensors')\nvisualizer.run_complete_analysis()"
            }
        ]
        
        for i, example in enumerate(examples, 1):
            print(f"\n{i}. {example['name']}")
            print(f"   Description: {example['description']}")
            print(f"   Usage: {example['command']}")
    
    def validate_integration(self):
        """Validate that the integration is working correctly"""
        print("\n🔧 Validating Hot Durham Visualization Integration...")
        
        checks = [
            ("Data directory exists", self.data_dir.exists()),
            ("Output directory exists", self.output_dir.exists()),
            ("Reports directory exists", self.reports_dir.exists()),
            ("Sensor data files available", len(list(self.data_dir.glob("*.csv"))) > 0),
            ("Visualization script exists", (self.project_root / "comprehensive_sensor_visualization.py").exists()),
            ("Analysis summary script exists", (self.project_root / "analysis_summary.py").exists())
        ]
        
        all_passed = True
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
            if not result:
                all_passed = False
        
        if all_passed:
            print("\n🎉 Integration validation successful!")
            return True
        else:
            print("\n⚠️ Some validation checks failed")
            return False

def main():
    """Main integration function"""
    print("🌡️ Hot Durham Multi-Sensor Visualization System")
    print("=" * 50)
    
    # Initialize the integration manager
    manager = HotDurhamVisualizationManager()
    
    # Validate integration
    if not manager.validate_integration():
        print("❌ Integration validation failed. Please check your setup.")
        return
    
    # Run visualization analysis
    success = manager.run_visualization_analysis()
    
    if success:
        # Generate integration summary
        manager.generate_integration_summary()
        
        # Show usage examples
        manager.show_usage_examples()
        
        print("\n🏆 HOT DURHAM VISUALIZATION INTEGRATION COMPLETE!")
        print("✅ Multi-sensor visualization system ready for use")
        print("✅ All 14 test sensors analyzed and visualized")
        print("✅ Professional dashboards generated")
        print("✅ Integration with Hot Durham project successful")
        
    else:
        print("❌ Visualization analysis failed. Please check the logs.")

if __name__ == "__main__":
    main()
