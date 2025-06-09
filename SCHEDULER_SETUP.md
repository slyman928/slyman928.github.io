# Windows Task Scheduler Setup Instructions

## Option 1: Using GUI

1. **Open Task Scheduler**
   - Press `Win + R`, type `taskschd.msc`, press Enter

2. **Create Basic Task**
   - Click "Create Basic Task" in the right panel
   - Name: "Daily RSS News Update"
   - Description: "Fetches and publishes daily news digest"

3. **Set Trigger**
   - Choose "Daily"
   - Set start time (e.g., 6:00 AM)
   - Set to recur every 1 day

4. **Set Action**
   - Choose "Start a program"
   - Program: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\Users\Sam\Desktop\feed parser\deploy_to_github.ps1"`
   - Start in: `C:\Users\Sam\Desktop\feed parser`

5. **Finish Setup**
   - Check "Open Properties when I click Finish"
   - In Properties → General → Check "Run with highest privileges"
   - In Properties → Settings → Check "Run task as soon as possible after a scheduled start is missed"

## Option 2: Using PowerShell Command

Run this in PowerShell as Administrator:

```powershell
$action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-ExecutionPolicy Bypass -File `"C:\Users\Sam\Desktop\feed parser\deploy_to_github.ps1`"" -WorkingDirectory "C:\Users\Sam\Desktop\feed parser"
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00AM
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "Daily RSS News Update" -Action $action -Trigger $trigger -Settings $settings -Description "Fetches and publishes daily news digest"
```

## Testing the Setup

Test manually first:
```powershell
cd "C:\Users\Sam\Desktop\feed parser"
.\deploy_to_github.ps1
```

Check the logs:
```powershell
Get-Content deployment.log -Tail 20
```
