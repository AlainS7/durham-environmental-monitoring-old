#!/usr/bin/env python3
"""
Quick visualization viewer to display the generated graphs
"""
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path

def show_visualization(filename):
    """Display a specific visualization"""
    viz_dir = Path("sensor_visualizations")
    img_path = viz_dir / filename
    
    if img_path.exists():
        img = mpimg.imread(str(img_path))
        plt.figure(figsize=(20, 12))
        plt.imshow(img)
        plt.axis('off')
        plt.title(f'Generated Visualization: {filename}', fontsize=16, fontweight='bold', pad=20)
        plt.tight_layout()
        plt.show()
        print(f"Displayed: {filename}")
    else:
        print(f"File not found: {filename}")

def list_visualizations():
    """List all available visualizations"""
    viz_dir = Path("sensor_visualizations")
    if viz_dir.exists():
        png_files = list(viz_dir.glob("*.png"))
        print("Available visualizations:")
        for i, file in enumerate(png_files, 1):
            print(f"{i}. {file.name}")
        return png_files
    else:
        print("Visualization directory not found")
        return []

if __name__ == "__main__":
    print("Multi-Sensor Visualization Viewer")
    print("=" * 40)
    
    # List available visualizations
    viz_files = list_visualizations()
    
    if viz_files:
        print(f"\nGenerated {len(viz_files)} visualization files successfully!")
        print("\nTo view a specific visualization, modify the script to call:")
        print("show_visualization('filename.png')")
        
        # Example: Show the environmental dashboard
        print("\nDisplaying the comprehensive environmental dashboard...")
        show_visualization('environmental_dashboard.png')
