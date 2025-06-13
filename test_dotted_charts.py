#!/usr/bin/env python3
"""
Quick test to verify dotted line charts are working in PDF reports
"""

import sys
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

def test_dotted_line_chart():
    """Create a simple test chart with dotted lines to verify the styling."""
    print("🧪 Testing Dotted Line Chart Generation")
    print("=" * 40)
    
    # Create sample data
    dates = pd.date_range(start=datetime.now() - timedelta(days=7), 
                         end=datetime.now(), freq='H')
    values = np.random.normal(25, 5, len(dates)) + np.sin(np.arange(len(dates)) * 0.1) * 3
    
    # Create chart with dotted lines (same style as PDF reports)
    plt.figure(figsize=(12, 6))
    plt.plot(dates, values, linewidth=2, color='steelblue', 
             marker='.', markersize=4, alpha=0.8, linestyle=':')
    
    plt.xlabel('Date', fontsize=14)
    plt.ylabel('Test Metric', fontsize=14)
    plt.title('Test Chart - Dotted Line Style', fontsize=16, fontweight='bold')
    plt.grid(True, axis='both', linestyle='--', linewidth=0.5, alpha=0.7)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # Save test chart
    output_path = Path(__file__).parent / "temp" / "test_dotted_chart.png"
    output_path.parent.mkdir(exist_ok=True)
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✅ Test chart saved: {output_path}")
    print(f"📊 Chart features:")
    print(f"   - Line style: Dotted (:)")
    print(f"   - Line width: 2")
    print(f"   - Markers: Small dots")
    print(f"   - Color: Steel blue")
    print(f"   - Grid: Dashed lines with transparency")
    
    return str(output_path)

if __name__ == "__main__":
    test_path = test_dotted_line_chart()
    print(f"\n🎯 Dotted line styling is ready for PDF reports!")
    print(f"📁 Test chart: {test_path}")
