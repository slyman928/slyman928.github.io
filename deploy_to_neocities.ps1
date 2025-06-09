# PowerShell script for RSS parser and Neocities deployment
param(
    [switch]$SkipParser,
    [string]$NeocitiesUsername,
    [string]$NeocitiesPassword,
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

function Deploy-To-Neocities {
    param($Username, $Password, $FilePath)
    
    try {
        Write-Log "Uploading to Neocities..."
        
        # Create credentials for basic auth
        $credentials = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes("$Username`:$Password"))
        
        # Read file content
        $fileContent = Get-Content $FilePath -Raw -Encoding UTF8
        $boundary = [System.Guid]::NewGuid().ToString()
        
        # Create multipart form data
        $bodyLines = @()
        $bodyLines += "--$boundary"
        $bodyLines += 'Content-Disposition: form-data; name="index.html"; filename="index.html"'
        $bodyLines += 'Content-Type: text/html'
        $bodyLines += ''
        $bodyLines += $fileContent
        $bodyLines += "--$boundary--"
        
        $body = $bodyLines -join "`r`n"
        
        # Upload to Neocities
        $headers = @{
            'Authorization' = "Basic $credentials"
            'Content-Type' = "multipart/form-data; boundary=$boundary"
        }
        
        $response = Invoke-RestMethod -Uri "https://neocities.org/api/upload" -Method Post -Body $body -Headers $headers
        
        if ($response.result -eq "success") {
            Write-Log "Successfully uploaded to Neocities!"
            return $true
        } else {
            Write-Log "Neocities upload failed: $($response.error_type)" -Type "ERROR"
            return $false
        }
    }
    catch {
        Write-Log "Error uploading to Neocities: $($_.Exception.Message)" -Type "ERROR"
        return $false
    }
}

try {
    Write-Log "Starting RSS News Parser and Neocities deployment"
    
    # Run the RSS parser
    if (-not $SkipParser) {
        Write-Log "Activating conda environment..."
        
        # Try different methods to activate conda
        $condaActivated = $false
        
        # Method 1: Try direct conda command
        try {
            & conda activate feed 2>$null
            if ($LASTEXITCODE -eq 0) { $condaActivated = $true }
        } catch {}
        
        # Method 2: Try conda hook
        if (-not $condaActivated) {
            try {
                & "C:\Users\Sam\miniconda3\shell\condabin\conda-hook.ps1"
                & conda activate feed
                if ($LASTEXITCODE -eq 0) { $condaActivated = $true }
            } catch {}
        }
        
        # Method 3: Try direct python path
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
        Write-Log "HTML generated successfully ($('{0:N0}' -f (Get-Item 'news_digest.html').Length) bytes)"
    }
    
    # Get Neocities credentials
    if (-not $NeocitiesUsername) {
        $NeocitiesUsername = $env:NEOCITIES_USERNAME
        if (-not $NeocitiesUsername) {
            Write-Log "Please set NEOCITIES_USERNAME environment variable or use -NeocitiesUsername parameter" -Type "ERROR"
            exit 1
        }
    }
    
    if (-not $NeocitiesPassword) {
        $NeocitiesPassword = $env:NEOCITIES_PASSWORD
        if (-not $NeocitiesPassword) {
            Write-Log "Please set NEOCITIES_PASSWORD environment variable or use -NeocitiesPassword parameter" -Type "ERROR"
            exit 1
        }
    }
    
    # Deploy to Neocities
    $uploadSuccess = Deploy-To-Neocities -Username $NeocitiesUsername -Password $NeocitiesPassword -FilePath "news_digest.html"
    
    if ($uploadSuccess) {
        Write-Log "Deployment completed successfully!"
        Write-Log "Your news digest is available at: https://$NeocitiesUsername.neocities.org"
        
        # Log statistics
        $articleCount = (Get-Content "news_digest.html" | Select-String "class=`"article`"").Count
        Write-Log "Deployed $articleCount articles"
    } else {
        throw "Failed to upload to Neocities"
    }
    
} catch {
    Write-Log "ERROR: $($_.Exception.Message)" -Type "ERROR"
    exit 1
}

Write-Log "Process completed!"
