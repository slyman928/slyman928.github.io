@echo off
REM Windows deployment script for RSS News Summarizer

REM Activate virtual environment (adjust path as needed)
call venv\Scripts\activate

REM Install/update dependencies
pip install -r requirements.txt

REM Run the script
python "import feedparser.py"

REM Optional: Copy to web server directory if needed
REM copy news_digest.html "C:\inetpub\wwwroot\"
