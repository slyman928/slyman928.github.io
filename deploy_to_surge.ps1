# PowerShell script for RSS parser and Surge.sh deployment
param(
    [switch]$SkipParser,
    [string]$Domain,
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
    Write-Log "Starting RSS News Parser and Surge.sh deployment"
    
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
    
    # Check if surge is installed
    try {
        & surge --version 2>$null | Out-Null
    } catch {
        Write-Log "Installing Surge.sh..." -Type "WARN"
        & npm install -g surge
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to install Surge.sh. Please install Node.js first: https://nodejs.org"
        }
    }
    
    # Deploy to Surge
    Write-Log "Deploying to Surge.sh..."
    
    if ($Domain) {
        & surge news_digest.html $Domain
    } else {
        # Use a default domain based on current date
        $dateStr = Get-Date -Format "yyyy-MM-dd"
        $defaultDomain = "news-digest-$dateStr.surge.sh"
        Write-Log "Using domain: $defaultDomain"
        & surge news_digest.html $defaultDomain
    }
    
    if ($LASTEXITCODE -ne 0) {
        throw "Surge deployment failed"
    }
    
    Write-Log "Deployment completed successfully!"
    Write-Log "Your news digest is available at the URL shown above"
    
} catch {
    Write-Log "ERROR: $($_.Exception.Message)" -Type "ERROR"
    exit 1
}
