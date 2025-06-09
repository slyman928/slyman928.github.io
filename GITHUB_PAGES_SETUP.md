# GitHub Pages Setup Guide for slyman928.github.io

## 🚀 Quick Setup Steps

### 1. Create the Special Repository
1. Go to [github.com](https://github.com)
2. Click "New Repository"
3. **Repository name**: `slyman928.github.io` (exactly this name!)
4. Set to **Public** (required for free GitHub Pages)
5. ✅ Check "Add a README file"
6. Click "Create repository"

### 2. Clone and Setup Locally
```powershell
# Navigate to your project folder
cd "C:\Users\Sam\Desktop\feed parser"

# Initialize git and connect to your repo
git init
git branch -M main
git remote add origin https://github.com/slyman928/slyman928.github.io.git

# Test the connection
git remote -v
```

### 3. Test the Deployment Script
```powershell
# Run once to test everything works
.\deploy_to_github.ps1

# If successful, your site will be live at:
# https://slyman928.github.io
```

### 4. Enable GitHub Pages (if needed)
1. Go to your repository: `https://github.com/slyman928/slyman928.github.io`
2. Click **Settings** → **Pages**
3. Under **Source**: Should already be set to "Deploy from a branch"
4. **Branch**: `main` / `/ (root)`
5. Click **Save**

## 🔄 Daily Automation

### Windows Task Scheduler Setup:
1. Open **Task Scheduler** (search in Start menu)
2. Click **Create Basic Task**
3. **Name**: "Daily News Update"
4. **Trigger**: Daily at 6:00 AM
5. **Action**: Start a program
   - **Program**: `powershell.exe`
   - **Arguments**: `-ExecutionPolicy Bypass -File "C:\Users\Sam\Desktop\feed parser\deploy_to_github.ps1"`
   - **Start in**: `C:\Users\Sam\Desktop\feed parser`

## 📊 What Happens Daily

1. **6:00 AM**: Task Scheduler runs the script
2. **Script activates** your conda environment
3. **Fetches RSS feeds** from all sources (Science, Tech, Gaming, Movies)
4. **AI summarizes** new articles (using cached summaries for old ones)
5. **Generates HTML** with all articles organized by category
6. **Copies to index.html** (required for GitHub Pages)
7. **Commits and pushes** to GitHub
8. **GitHub Pages deploys** automatically (takes 1-5 minutes)
9. **Site is live** at https://slyman928.github.io

## 🛠️ Manual Commands

```powershell
# Run parser only (no deployment)
.\deploy_to_github.ps1 -SkipParser

# Run everything
.\deploy_to_github.ps1

# Check git status
git status

# View deployment logs
Get-Content deployment.log -Tail 20
```

## 🎯 Your Final URLs

- **GitHub Repository**: https://github.com/slyman928/slyman928.github.io
- **Live Website**: https://slyman928.github.io
- **Raw HTML**: https://raw.githubusercontent.com/slyman928/slyman928.github.io/main/index.html

## 🔧 Troubleshooting

### First Time Setup Issues:
```powershell
# If git asks for credentials, set them:
git config --global user.name "slyman928"
git config --global user.email "your-email@example.com"

# If push fails, you might need to authenticate:
# Use GitHub Desktop or set up SSH keys
```

### Authentication:
- **Easiest**: Install [GitHub Desktop](https://desktop.github.com) and sign in
- **Alternative**: Use Personal Access Token for HTTPS
- **Advanced**: Set up SSH keys

## ✅ Success Indicators

After running the script, you should see:
- ✅ "HTML generated successfully"
- ✅ "Deployment completed successfully!"
- ✅ "🌐 Your news digest is live at: https://slyman928.github.io"
- ✅ No errors in the log

Wait 1-5 minutes, then visit https://slyman928.github.io to see your news digest!

## 📈 Features

Your automated news site will include:
- **Daily updates** with fresh content
- **Multiple categories** (Science, Tech, Gaming, Entertainment)
- **AI summaries** of each article
- **Source attribution** for each article
- **Responsive design** that works on mobile
- **Automatic caching** to save on API costs
- **Professional appearance** with modern styling
