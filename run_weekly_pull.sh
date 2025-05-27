#!/bin/bash
# Hot Durham Weekly Data Pull and Maintenance Script
cd "/Users/alainsoto/IdeaProjects/Hot Durham"

echo "🔄 Running weekly data pull..."
"/Users/alainsoto/IdeaProjects/Hot Durham/.venv/bin/python3" "/Users/alainsoto/IdeaProjects/Hot Durham/src/data_collection/automated_data_pull.py" --weekly

echo "🧹 Running maintenance cleanup..."
"/Users/alainsoto/IdeaProjects/Hot Durham/.venv/bin/python3" "/Users/alainsoto/IdeaProjects/Hot Durham/maintenance_cleanup.py"

echo "✅ Weekly tasks completed"
