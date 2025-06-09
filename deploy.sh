#!/bin/bash
# Server deployment script for RSS News Summarizer

# Update from git (if using version control)
# git pull origin main

# Activate virtual environment
source venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Run the script
python "import feedparser.py"

# Optional: Copy to web server directory if needed
# cp news_digest.html /var/www/html/
