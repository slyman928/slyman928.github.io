@echo off
REM Windows script to run RSS parser and deploy to GitHub Pages

echo [%TIME%] Starting RSS News Parser...

REM Activate conda environment
call conda activate feed

REM Run the RSS parser
python multi_feed_parser.py

REM Check if HTML was generated successfully
if not exist "news_digest.html" (
    echo [%TIME%] ERROR: news_digest.html was not generated!
    exit /b 1
)

echo [%TIME%] HTML generated successfully, deploying to GitHub...

REM Add timestamp to commit message
for /f "tokens=2 delims==" %%a in ('wmic OS Get localdatetime /value') do set "dt=%%a"
set "YY=%dt:~2,2%" & set "MM=%dt:~4,2%" & set "DD=%dt:~6,2%"
set "timestamp=%DD%/%MM%/%YY%"

REM Git operations
git add news_digest.html article_cache.json
git commit -m "Daily news update - %timestamp%"
git push origin main

echo [%TIME%] Deployment complete!

REM Optional: Log the results
echo %DATE% %TIME% - News update deployed successfully >> deployment.log
