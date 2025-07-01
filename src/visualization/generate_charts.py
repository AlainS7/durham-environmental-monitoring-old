"""
Chart Generation Module for the Hot Durham Project.

This module provides functions for creating and saving Matplotlib charts from your
data. It is designed to be a central access point for all chart-related logic,
making it easier to integrate with other components of the application.

Key Features:
- Time-series plots for sensor data.
- Bar charts for summary data.
- Scatter plots for correlation analysis.
"""

import matplotlib.pyplot as plt
import pandas as pd

def create_time_series_plot(data, x_col, y_col, title, x_label, y_label, file_path):
    """Creates and saves a time-series plot from the given data."""
    plt.figure(figsize=(12, 6))
    plt.plot(data[x_col], data[y_col])
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.savefig(file_path)
    plt.close()

def create_bar_chart(data, x_col, y_col, title, x_label, y_label, file_path):
    """Creates and saves a bar chart from the given data."""
    plt.figure(figsize=(12, 6))
    plt.bar(data[x_col], data[y_col])
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.savefig(file_path)
    plt.close()

def create_scatter_plot(data, x_col, y_col, title, x_label, y_label, file_path):
    """Creates and saves a scatter plot from the given data."""
    plt.figure(figsize=(12, 6))
    plt.scatter(data[x_col], data[y_col])
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel(y_label)
    plt.grid(True)
    plt.savefig(file_path)
    plt.close()
