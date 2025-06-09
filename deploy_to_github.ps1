# PowerShell script for RSS parser and GitHub Pages deployment
# For slyman928.github.io repository
param(
    [switch]$SkipParser,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"
$GITHUB_USERNAME = "slyman928"
$REPO_NAME = "$GITHUB_USERNAME.github.io"

function Write-Log {
    param($Message, $Type = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Type] $Message"
    $color = switch($Type) { "ERROR" {"Red"} "WARN" {"Yellow"} default {"Green"} }
    Write-Host $logMessage -ForegroundColor $color
    Add-Content -Path "deployment.log" -Value $logMessage
}

try {
    Write-Log "Starting RSS News Parser for slyman928.github.io deployment"
    
    # Run the RSS parser
    if (-not $SkipParser) {
        Write-Log "Activating conda environment..."
        
        # Try multiple methods to activate conda
        $condaActivated = $false
        
        try {
            & conda activate feed 2>$null
            if ($LASTEXITCODE -eq 0) { $condaActivated = $true }
        } catch {}
        
        if (-not $condaActivated) {
            try {
                & "C:\Users\Sam\miniconda3\shell\condabin\conda-hook.ps1"
                & conda activate feed
                if ($LASTEXITCODE -eq 0) { $condaActivated = $true }
            } catch {}
        }
        
        if (-not $condaActivated) {
            Write-Log "Using direct Python path..." -Type "WARN"
            $env:PATH = "C:\Users\Sam\miniconda3\envs\feed\Scripts;C:\Users\Sam\miniconda3\envs\feed;" + $env:PATH
        }
        
        # Run the RSS parser
        Write-Log "Running RSS parser..."
        if (Test-Path "multi_feed_parser.py") {
            & python multi_feed_parser.py
        } else {
            & python "import feedparser.py"
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "RSS parser failed with exit code $LASTEXITCODE"
        }
        
        # Verify HTML was generated
        if (-not (Test-Path "news_digest.html")) {
            throw "news_digest.html was not generated"
        }
        
        $fileSize = (Get-Item "news_digest.html").Length
        Write-Log "HTML generated successfully ($('{0:N0}' -f $fileSize) bytes)"
    }
      # Check if we're in a git repository
    if (-not (Test-Path ".git")) {
        Write-Log "Initializing git repository for $REPO_NAME..." -Type "WARN"
        git init
        git branch -M main
        
        # Set up the remote for your GitHub Pages repo
        $repoUrl = "https://github.com/$GITHUB_USERNAME/$REPO_NAME.git"
        git remote add origin $repoUrl
        Write-Log "Added remote: $repoUrl"
    }
    
    # Rename the HTML file to index.html for GitHub Pages
    if (Test-Path "news_digest.html") {
        Copy-Item "news_digest.html" "index.html" -Force
        Write-Log "Copied news_digest.html to index.html for GitHub Pages"
    }
    
    # Create a simple README if it doesn't exist
    if (-not (Test-Path "README.md")) {
        $readmeContent = @"
# slyman928.github.io

Daily updated news digest featuring:
- 🔬 Science & Research news
- 🤖 AI & Technology updates  
- 🎮 Gaming news
- 🎬 Entertainment news
- 💻 Tech community discussions

Updated automatically every day via RSS feeds and AI summarization.

Visit: https://slyman928.github.io
"@
        Set-Content -Path "README.md" -Value $readmeContent
        Write-Log "Created README.md"
    }
    
    # Git operations
    Write-Log "Deploying to GitHub Pages..."
    $timestamp = Get-Date -Format "MMM dd, yyyy HH:mm"
    
    # Add files for GitHub Pages
    git add index.html article_cache.json deployment.log README.md
    
    # Check if there are changes to commit
    $status = git status --porcelain
    if (-not $status) {
        Write-Log "No changes to commit" -Type "WARN"
        return
    }
    
    git commit -m "📰 Daily news update - $timestamp"
    
    # Push to GitHub
    git push origin main
    if ($LASTEXITCODE -ne 0) {
        # Try to set upstream if it's the first push
        Write-Log "Setting upstream and pushing..." -Type "WARN"
        git push --set-upstream origin main
    }
    
    Write-Log "Deployment completed successfully!"
    Write-Log "🌐 Your news digest is live at: https://slyman928.github.io"
    
    # Count articles for stats
    $articleCount = (Get-Content "index.html" | Select-String 'class="article"').Count
    Write-Log "📊 Deployed $articleCount articles"
    
} catch {
    Write-Log "ERROR: $($_.Exception.Message)" -Type "ERROR"
    exit 1
}
