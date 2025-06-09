# PowerShell script for RSS parser and Netlify deployment
param(
    [switch]$SkipParser,
    [string]$SiteName,
    [switch]$Verbose
)

$ErrorActionPreference = "Stop"

function Write-Log {
    param($Message, $Type = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Type] $Message"
    Write-Host $logMessage -ForegroundColor $(if($Type -eq "ERROR"){"Red"} elseif($Type -eq "WARN"){"Yellow"} else{"Green"})
    Add-Content -Path "deployment.log" -Value $logMessage
}

try {
    Write-Log "Starting RSS News Parser and Netlify deployment"
    
    # Run the RSS parser
    if (-not $SkipParser) {
        Write-Log "Running RSS parser..."
        
        # Try to activate conda and run parser
        try {
            & "C:\Users\Sam\miniconda3\shell\condabin\conda-hook.ps1" 2>$null
            & conda activate feed 2>$null
        } catch {}
        
        if (Test-Path "multi_feed_parser.py") {
            & python multi_feed_parser.py
        } else {
            & python "import feedparser.py"
        }
        
        if ($LASTEXITCODE -ne 0) {
            throw "RSS parser failed"
        }
        
        if (-not (Test-Path "news_digest.html")) {
            throw "news_digest.html was not generated"
        }
        Write-Log "HTML generated successfully"
    }
    
    # Check if Netlify CLI is installed
    try {
        & netlify --version 2>$null | Out-Null
    } catch {
        Write-Log "Installing Netlify CLI..." -Type "WARN"
        & npm install -g netlify-cli
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install Netlify CLI. Please install Node.js first: https://nodejs.org"
        }
    }
    
    # Deploy to Netlify
    Write-Log "Deploying to Netlify..."
    
    if ($SiteName) {
        & netlify deploy --prod --dir . --site $SiteName
    } else {
        # Create a new site or deploy to existing
        & netlify deploy --prod --dir .
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Netlify deployment failed"
    }
    
    Write-Log "Deployment completed successfully!"
    Write-Log "Your news digest is available at the URL shown above"
    
} catch {
    Write-Log "ERROR: $($_.Exception.Message)" -Type "ERROR"
    exit 1
}
