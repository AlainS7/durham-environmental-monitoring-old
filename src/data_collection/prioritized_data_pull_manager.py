#!/usr/bin/env python3
"""
Prioritized Data Pull Manager for Hot Durham Project

This script addresses the todo item: "Prioritize frequent pulls for 'inside data' 
(if this refers to specific indoor sensors or critical data points)."

It implements intelligent data pull scheduling with different frequencies for different
sensor types based on their importance and data characteristics.
"""

import json
import asyncio
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import logging
from typing import Dict, List, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PrioritizedDataPuller:
    """Manages prioritized data pulls with different frequencies for different sensor types."""
    
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent
        self.config_dir = self.base_dir / "config"
        self.config_file = self.config_dir / "prioritized_pull_config.json"
        self.log_file = self.base_dir / "logs" / f"prioritized_pulls_{datetime.now().strftime('%Y%m')}.log"
        
        # Create directories if they don't exist
        self.config_dir.mkdir(exist_ok=True)
        self.log_file.parent.mkdir(exist_ok=True)
        
        self.config = self._load_or_create_config()
        self._setup_file_logging()
    
    def _setup_file_logging(self):
        """Setup file logging for pull operations."""
        file_handler = logging.FileHandler(self.log_file)
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    def _load_or_create_config(self) -> Dict[str, Any]:
        """Load existing configuration or create default one."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    logger.info("Loaded existing prioritized pull configuration")
                    return config
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        
        # Create default configuration
        default_config = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "description": "Prioritized data pull configuration for Hot Durham sensors",
            
            "sensor_priorities": {
                "critical": {
                    "description": "Indoor air quality sensors and critical monitoring points",
                    "pull_frequency_minutes": 15,
                    "max_gap_tolerance_minutes": 30,
                    "retry_attempts": 3,
                    "sensors": [
                        {
                            "type": "tsi",
                            "criteria": {
                                "location_keywords": ["indoor", "inside", "office", "classroom", "hospital"],
                                "device_names": ["BS-01", "BS-05"],  # Example indoor sensors
                                "pm25_threshold_importance": 25.0  # Higher PM2.5 readings = more critical
                            }
                        }
                    ]
                },
                "high": {
                    "description": "Important outdoor sensors and weather stations",
                    "pull_frequency_minutes": 60,
                    "max_gap_tolerance_minutes": 120,
                    "retry_attempts": 2,
                    "sensors": [
                        {
                            "type": "tsi",
                            "criteria": {
                                "location_keywords": ["outdoor", "ambient", "street", "park"],
                                "device_names": ["BS-11", "BS-13"]  # Example outdoor sensors
                            }
                        },
                        {
                            "type": "wu",
                            "criteria": {
                                "station_ids": ["KNCDURHA548", "KNCDURHA549"],  # Primary weather stations
                                "metrics": ["tempAvg", "humidityAvg", "precipTotal"]
                            }
                        }
                    ]
                },
                "standard": {
                    "description": "Regular monitoring sensors",
                    "pull_frequency_minutes": 240,  # 4 hours
                    "max_gap_tolerance_minutes": 480,
                    "retry_attempts": 1,
                    "sensors": [
                        {
                            "type": "wu",
                            "criteria": {
                                "station_ids": ["KNCDURHA209", "KNCDURHA284", "KNCDURHA590"],
                                "metrics": ["windspeedAvg", "solarRadiationHigh"]
                            }
                        }
                    ]
                }
            },
            
            "pull_windows": {
                "business_hours": {
                    "start_hour": 8,
                    "end_hour": 18,
                    "frequency_multiplier": 1.0,
                    "description": "Normal frequency during business hours"
                },
                "after_hours": {
                    "start_hour": 18,
                    "end_hour": 8,
                    "frequency_multiplier": 0.5,
                    "description": "Reduced frequency after hours (except critical)"
                },
                "weekend": {
                    "frequency_multiplier": 0.3,
                    "description": "Reduced frequency on weekends (except critical)"
                }
            },
            
            "data_retention": {
                "critical_data_days": 365,
                "high_priority_days": 180,
                "standard_data_days": 90
            },
            
            "alert_thresholds": {
                "pm25_unhealthy": 55.0,
                "pm25_dangerous": 150.0,
                "temperature_extreme_low": -10.0,
                "temperature_extreme_high": 40.0,
                "humidity_low": 20.0,
                "humidity_high": 90.0
            }
        }
        
        # Save default configuration
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        logger.info(f"Created default prioritized pull configuration: {self.config_file}")
        return default_config
    
    def classify_sensor_priority(self, sensor_type: str, sensor_info: Dict[str, Any]) -> str:
        """Classify a sensor's priority based on configuration criteria."""
        
        for priority_level, priority_config in self.config["sensor_priorities"].items():
            for sensor_config in priority_config["sensors"]:
                if sensor_config["type"] != sensor_type:
                    continue
                
                criteria = sensor_config["criteria"]
                
                if sensor_type == "tsi":
                    # Check device name
                    device_name = sensor_info.get("device_name", "")
                    if device_name in criteria.get("device_names", []):
                        return priority_level
                    
                    # Check location keywords
                    friendly_name = sensor_info.get("friendly_name", "").lower()
                    location = sensor_info.get("location", "").lower()
                    
                    for keyword in criteria.get("location_keywords", []):
                        if keyword in friendly_name or keyword in location:
                            return priority_level
                    
                    # Check recent PM2.5 readings
                    recent_pm25 = sensor_info.get("recent_pm25", 0)
                    pm25_threshold = criteria.get("pm25_threshold_importance", 999)
                    if recent_pm25 >= pm25_threshold:
                        return priority_level
                
                elif sensor_type == "wu":
                    # Check station ID
                    station_id = sensor_info.get("station_id", "")
                    if station_id in criteria.get("station_ids", []):
                        return priority_level
        
        return "standard"  # Default priority
    
    def calculate_pull_frequency(self, priority: str, current_time: datetime = None) -> int:
        """Calculate actual pull frequency based on priority and time windows."""
        if current_time is None:
            current_time = datetime.now()
        
        base_frequency = self.config["sensor_priorities"][priority]["pull_frequency_minutes"]
        
        # Don't modify critical sensor frequency
        if priority == "critical":
            return base_frequency
        
        # Apply time-based multipliers
        hour = current_time.hour
        is_weekend = current_time.weekday() >= 5
        
        frequency_multiplier = 1.0
        
        if is_weekend:
            frequency_multiplier *= self.config["pull_windows"]["weekend"]["frequency_multiplier"]
        elif 8 <= hour < 18:  # Business hours
            frequency_multiplier *= self.config["pull_windows"]["business_hours"]["frequency_multiplier"]
        else:  # After hours
            frequency_multiplier *= self.config["pull_windows"]["after_hours"]["frequency_multiplier"]
        
        # Calculate final frequency (higher multiplier = longer intervals)
        final_frequency = int(base_frequency / frequency_multiplier)
        return max(final_frequency, 15)  # Minimum 15 minutes
    
    def get_sensor_inventory(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get inventory of all available sensors with their metadata."""
        inventory = {"tsi": [], "wu": []}
        
        # Load TSI device information
        try:
            # This would typically come from the TSI API or stored metadata
            # For now, we'll use example data based on existing device names
            example_tsi_devices = [
                {
                    "device_id": "bs-01",
                    "device_name": "BS-01",
                    "friendly_name": "Indoor Air Quality - Main Office",
                    "location": "indoor office building",
                    "recent_pm25": 15.2,
                    "last_seen": (datetime.now() - timedelta(minutes=30)).isoformat()
                },
                {
                    "device_id": "bs-05", 
                    "device_name": "BS-05",
                    "friendly_name": "Indoor Classroom Monitor",
                    "location": "indoor classroom",
                    "recent_pm25": 22.1,
                    "last_seen": (datetime.now() - timedelta(minutes=45)).isoformat()
                },
                {
                    "device_id": "bs-11",
                    "device_name": "BS-11", 
                    "friendly_name": "Outdoor Ambient Monitor",
                    "location": "outdoor ambient",
                    "recent_pm25": 8.5,
                    "last_seen": (datetime.now() - timedelta(minutes=60)).isoformat()
                },
                {
                    "device_id": "bs-13",
                    "device_name": "BS-13",
                    "friendly_name": "Street Level Monitor",
                    "location": "outdoor street",
                    "recent_pm25": 18.3,
                    "last_seen": (datetime.now() - timedelta(minutes=20)).isoformat()
                }
            ]
            inventory["tsi"] = example_tsi_devices
            
        except Exception as e:
            logger.error(f"Error loading TSI inventory: {e}")
        
        # Load Weather Underground station information
        try:
            example_wu_stations = [
                {
                    "station_id": "KNCDURHA548",
                    "station_name": "Duke-MS-01",
                    "location": "Primary monitoring station",
                    "last_seen": (datetime.now() - timedelta(minutes=15)).isoformat()
                },
                {
                    "station_id": "KNCDURHA549",
                    "station_name": "Duke-MS-02", 
                    "location": "Secondary monitoring station",
                    "last_seen": (datetime.now() - timedelta(minutes=20)).isoformat()
                },
                {
                    "station_id": "KNCDURHA209",
                    "station_name": "Duke-MS-03",
                    "location": "Tertiary monitoring station",
                    "last_seen": (datetime.now() - timedelta(minutes=120)).isoformat()
                }
            ]
            inventory["wu"] = example_wu_stations
            
        except Exception as e:
            logger.error(f"Error loading WU inventory: {e}")
        
        return inventory
    
    def create_pull_schedule(self) -> Dict[str, Any]:
        """Create optimized pull schedule based on sensor priorities."""
        logger.info("Creating prioritized pull schedule...")
        
        inventory = self.get_sensor_inventory()
        schedule = {
            "created_at": datetime.now().isoformat(),
            "next_update": (datetime.now() + timedelta(hours=1)).isoformat(),
            "priority_queues": {
                "critical": [],
                "high": [],
                "standard": []
            },
            "pull_intervals": {},
            "summary": {
                "total_sensors": 0,
                "critical_sensors": 0,
                "high_priority_sensors": 0,
                "standard_sensors": 0
            }
        }
        
        # Process each sensor type
        for sensor_type, sensors in inventory.items():
            for sensor in sensors:
                # Classify priority
                priority = self.classify_sensor_priority(sensor_type, sensor)
                
                # Calculate pull frequency
                pull_frequency = self.calculate_pull_frequency(priority)
                
                # Create schedule entry
                schedule_entry = {
                    "sensor_type": sensor_type,
                    "sensor_id": sensor.get("device_id" if sensor_type == "tsi" else "station_id"),
                    "sensor_name": sensor.get("device_name" if sensor_type == "tsi" else "station_name"),
                    "priority": priority,
                    "pull_frequency_minutes": pull_frequency,
                    "next_pull": (datetime.now() + timedelta(minutes=pull_frequency)).isoformat(),
                    "metadata": sensor
                }
                
                # Add to appropriate priority queue
                schedule["priority_queues"][priority].append(schedule_entry)
                
                # Track pull intervals
                interval_key = f"{sensor_type}_{schedule_entry['sensor_id']}"
                schedule["pull_intervals"][interval_key] = pull_frequency
                
                # Update summary
                schedule["summary"]["total_sensors"] += 1
                if priority == "critical":
                    schedule["summary"]["critical_sensors"] += 1
                elif priority == "high":
                    schedule["summary"]["high_priority_sensors"] += 1
                elif priority == "standard":
                    schedule["summary"]["standard_sensors"] += 1
        
        # Sort each priority queue by next pull time
        for priority in schedule["priority_queues"]:
            schedule["priority_queues"][priority].sort(key=lambda x: x["next_pull"])
        
        # Save schedule
        schedule_file = self.config_dir / f"pull_schedule_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(schedule_file, 'w') as f:
            json.dump(schedule, f, indent=2)
        
        logger.info(f"Pull schedule created: {schedule_file}")
        logger.info(f"Total sensors: {schedule['summary']['total_sensors']}")
        logger.info(f"Critical: {schedule['summary']['critical_sensors']}, "
                   f"High: {schedule['summary']['high_priority_sensors']}, "
                   f"Standard: {schedule['summary']['standard_sensors']}")
        
        return schedule
    
    def generate_pull_schedule(self) -> Dict[str, Any]:
        """Alias for create_pull_schedule() for backward compatibility."""
        return self.create_pull_schedule()
    
    def execute_priority_pull(self, sensor_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a data pull for a specific sensor."""
        sensor_type = sensor_entry["sensor_type"]
        sensor_id = sensor_entry["sensor_id"]
        priority = sensor_entry["priority"]
        
        logger.info(f"Executing {priority} priority pull for {sensor_type} sensor {sensor_id}")
        
        pull_result = {
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "priority": priority,
            "pull_time": datetime.now().isoformat(),
            "success": False,
            "records_pulled": 0,
            "errors": [],
            "next_scheduled_pull": None
        }
        
        try:
            if sensor_type == "tsi":
                # Simulate TSI data pull
                # In reality, this would call the actual TSI API pulling logic
                pull_result.update(self._simulate_tsi_pull(sensor_entry))
            elif sensor_type == "wu":
                # Simulate WU data pull
                # In reality, this would call the actual WU API pulling logic
                pull_result.update(self._simulate_wu_pull(sensor_entry))
            
            # Schedule next pull
            next_pull_minutes = self.calculate_pull_frequency(priority)
            next_pull_time = datetime.now() + timedelta(minutes=next_pull_minutes)
            pull_result["next_scheduled_pull"] = next_pull_time.isoformat()
            
            logger.info(f"✓ Successfully pulled {pull_result['records_pulled']} records from {sensor_id}")
            
        except Exception as e:
            pull_result["errors"].append(str(e))
            logger.error(f"✗ Failed to pull data from {sensor_id}: {e}")
        
        return pull_result
    
    def _simulate_tsi_pull(self, sensor_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate TSI data pull (placeholder for actual implementation)."""
        # This would integrate with the existing TSI data pulling logic
        import random
        
        # Simulate pull results
        records_pulled = random.randint(1, 24)  # Simulate hourly data
        success = random.random() > 0.1  # 90% success rate
        
        return {
            "success": success,
            "records_pulled": records_pulled if success else 0,
            "data_quality_score": random.uniform(0.8, 1.0) if success else 0.0
        }
    
    def _simulate_wu_pull(self, sensor_entry: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Weather Underground data pull (placeholder for actual implementation)."""
        # This would integrate with the existing WU data pulling logic
        import random
        
        # Simulate pull results
        records_pulled = random.randint(1, 48)  # Simulate half-hourly data
        success = random.random() > 0.05  # 95% success rate
        
        return {
            "success": success,
            "records_pulled": records_pulled if success else 0,
            "data_quality_score": random.uniform(0.9, 1.0) if success else 0.0
        }
    
    def run_prioritized_pulls(self, duration_minutes: int = 60) -> Dict[str, Any]:
        """Run prioritized data pulls for specified duration."""
        logger.info(f"Starting prioritized pull session for {duration_minutes} minutes")
        
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        schedule = self.create_pull_schedule()
        pull_results = []
        
        # Create combined priority queue (critical first, then high, then standard)
        combined_queue = []
        for priority in ["critical", "high", "standard"]:
            combined_queue.extend(schedule["priority_queues"][priority])
        
        current_time = datetime.now()
        
        while current_time < end_time and combined_queue:
            # Find sensors that are due for pulling
            due_sensors = []
            
            for sensor_entry in combined_queue:
                next_pull_time = datetime.fromisoformat(sensor_entry["next_pull"])
                if current_time >= next_pull_time:
                    due_sensors.append(sensor_entry)
            
            if due_sensors:
                # Sort by priority (critical first)
                priority_order = {"critical": 0, "high": 1, "standard": 2}
                due_sensors.sort(key=lambda x: priority_order[x["priority"]])
                
                # Execute pulls for due sensors
                for sensor_entry in due_sensors:
                    pull_result = self.execute_priority_pull(sensor_entry)
                    pull_results.append(pull_result)
                    
                    # Update next pull time in the queue
                    if pull_result["next_scheduled_pull"]:
                        sensor_entry["next_pull"] = pull_result["next_scheduled_pull"]
            
            # Wait before next check (check every minute)
            time.sleep(60)  # Simple sleep instead of async await
            current_time = datetime.now()
        
        # Generate session summary
        session_summary = {
            "session_start": start_time.isoformat(),
            "session_end": datetime.now().isoformat(),
            "duration_minutes": duration_minutes,
            "total_pulls": len(pull_results),
            "successful_pulls": len([r for r in pull_results if r["success"]]),
            "failed_pulls": len([r for r in pull_results if not r["success"]]),
            "pulls_by_priority": {
                "critical": len([r for r in pull_results if r["priority"] == "critical"]),
                "high": len([r for r in pull_results if r["priority"] == "high"]),
                "standard": len([r for r in pull_results if r["priority"] == "standard"])
            },
            "total_records": sum(r["records_pulled"] for r in pull_results),
            "pull_results": pull_results
        }
        
        # Save session results
        session_file = self.base_dir / "logs" / f"prioritized_pull_session_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
        with open(session_file, 'w') as f:
            json.dump(session_summary, f, indent=2)
        
        logger.info(f"Pull session completed. Results saved to: {session_file}")
        logger.info(f"Total pulls: {session_summary['total_pulls']}, "
                   f"Successful: {session_summary['successful_pulls']}, "
                   f"Records: {session_summary['total_records']}")
        
        return session_summary
    
    def generate_priority_report(self) -> str:
        """Generate a report showing current sensor priorities and schedules."""
        inventory = self.get_sensor_inventory()
        
        report_lines = [
            "🎯 Hot Durham Prioritized Data Pull Report",
            "=" * 50,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        for sensor_type, sensors in inventory.items():
            if not sensors:
                continue
                
            report_lines.append(f"📊 {sensor_type.upper()} Sensors:")
            report_lines.append("-" * 30)
            
            # Group by priority
            priority_groups = {"critical": [], "high": [], "standard": []}
            
            for sensor in sensors:
                priority = self.classify_sensor_priority(sensor_type, sensor)
                priority_groups[priority].append(sensor)
            
            for priority, sensor_list in priority_groups.items():
                if not sensor_list:
                    continue
                    
                frequency = self.calculate_pull_frequency(priority)
                report_lines.append(f"\n🔴 {priority.upper()} Priority (every {frequency} minutes):")
                
                for sensor in sensor_list:
                    name = sensor.get("device_name" if sensor_type == "tsi" else "station_name", "Unknown")
                    location = sensor.get("friendly_name" if sensor_type == "tsi" else "location", "")
                    report_lines.append(f"  • {name} - {location}")
                    
                    if sensor_type == "tsi" and "recent_pm25" in sensor:
                        report_lines.append(f"    Recent PM2.5: {sensor['recent_pm25']} μg/m³")
        
        # Add configuration summary
        report_lines.extend([
            "",
            "⚙️ Configuration Summary:",
            "-" * 30,
            f"Critical sensors: Pull every {self.config['sensor_priorities']['critical']['pull_frequency_minutes']} minutes",
            f"High priority: Pull every {self.config['sensor_priorities']['high']['pull_frequency_minutes']} minutes", 
            f"Standard sensors: Pull every {self.config['sensor_priorities']['standard']['pull_frequency_minutes']} minutes",
            "",
            "📅 Time-based Adjustments:",
            f"Business hours (8-18): Normal frequency",
            f"After hours: {self.config['pull_windows']['after_hours']['frequency_multiplier']*100}% frequency",
            f"Weekends: {self.config['pull_windows']['weekend']['frequency_multiplier']*100}% frequency",
            "",
            "Note: Critical sensors maintain their frequency regardless of time windows."
        ])
        
        report_content = "\n".join(report_lines)
        
        # Save report
        report_file = self.base_dir / "reports" / f"prioritized_pull_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.parent.mkdir(exist_ok=True)
        
        with open(report_file, 'w') as f:
            f.write(report_content)
        
        logger.info(f"Priority report saved to: {report_file}")
        return report_content

def main():
    """Main execution function."""
    puller = PrioritizedDataPuller()
    
    print("🎯 Hot Durham Prioritized Data Pull Manager")
    print("=" * 50)
    
    # Generate priority report
    print("\n📋 Generating priority classification report...")
    report = puller.generate_priority_report()
    print(report)
    
    # Create pull schedule
    print("\n📅 Creating optimized pull schedule...")
    schedule = puller.create_pull_schedule()
    
    # Show schedule summary
    print(f"\n✅ Schedule created with {schedule['summary']['total_sensors']} sensors:")
    print(f"   🔴 Critical: {schedule['summary']['critical_sensors']} sensors")
    print(f"   🟡 High: {schedule['summary']['high_priority_sensors']} sensors") 
    print(f"   🟢 Standard: {schedule['summary']['standard_sensors']} sensors")
    
    # Option to run a test session
    print(f"\n💡 Configuration saved to: {puller.config_file}")
    print("💡 To run actual pulls, integrate this with your existing data pull scripts")
    print("💡 The prioritized schedule can be used by automated_data_pull.py")

# Export the class with the expected name for compatibility
PrioritizedDataPullManager = PrioritizedDataPuller

if __name__ == "__main__":
    main()
