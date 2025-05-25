#!/usr/bin/env python3
"""
Hot Durham Air Quality Monitoring Setup

This setup.py file allows for proper installation of the Hot Durham project
as a Python package, making imports more reliable and professional.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

# Read requirements
requirements = []
if (this_directory / "requirements.txt").exists():
    requirements = (this_directory / "requirements.txt").read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="hot-durham",
    version="2.0.0",
    author="Hot Durham Project",
    author_email="hotdurham@gmail.com",
    description="Comprehensive air quality monitoring and analysis system for Durham, NC",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/hotdurham/air-quality-monitoring",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Atmospheric Science",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.8",
            "mypy>=0.812",
        ],
        "gui": [
            "streamlit>=1.20.0",
            "plotly>=5.0.0",
            "dash>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hot-durham-collect=data_collection.automated_data_pull:main",
            "hot-durham-analyze=analysis.complete_analysis_suite:main",
            "hot-durham-backup=core.backup_system:main",
            "hot-durham-status=automation.status_check:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json", "*.yml", "*.yaml", "*.txt", "*.md"],
    },
    zip_safe=False,
    keywords="air-quality monitoring durham environmental-data analysis",
    project_urls={
        "Bug Reports": "https://github.com/hotdurham/air-quality-monitoring/issues",
        "Source": "https://github.com/hotdurham/air-quality-monitoring",
        "Documentation": "https://hotdurham.github.io/air-quality-monitoring/",
    },
)
