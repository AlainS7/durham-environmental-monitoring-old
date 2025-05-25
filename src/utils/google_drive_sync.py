#!/usr/bin/env python3
"""
Google Drive Auto-Sync for Hot Durham Project
Automatically syncs data folders to Google Drive with folder organization.
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime, timedelta