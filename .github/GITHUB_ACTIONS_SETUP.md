# GitHub Actions Automation Setup

## Overview
This workflow runs the automated scraper in the cloud every Tuesday at 10 PM UTC, so you don't need to have your Mac running.

## How It Works

1. **GitHub Actions** runs on GitHub's servers (cloud)
2. Every Tuesday at 22:00 UTC (10 PM UTC), it:
   - Checks out your repository
   - Installs Python and dependencies
   - Runs `auto_weekly_scraper.py`
   - Commits and pushes updated Excel files back to GitHub
3. You pull the changes to see updated data

## Setup Instructions

### 1. Push the workflow file
The workflow is already created at `.github/workflows/weekly-scraper.yml`. Just push it:

```bash
cd "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi"
git add .github/workflows/weekly-scraper.yml
git add scripts/auto_weekly_scraper.py
git commit -m "Add automated weekly scraper with GitHub Actions"
git push
```

### 2. Enable GitHub Actions
1. Go to your GitHub repository
2. Click the "Actions" tab
3. Enable workflows if prompted

### 3. Test it manually
Before waiting for Tuesday, test the workflow:
1. Go to "Actions" tab on GitHub
2. Click "Weekly Match Data Scraper"
3. Click "Run workflow" button
4. Select branch "main"
5. Click "Run workflow"

### 4. Check the results
- View logs in the Actions tab
- See committed changes in your repo
- Pull changes to your local machine

## Timezone Adjustment

The workflow runs at **22:00 UTC** by default. To adjust for Turkish time (UTC+3):

- **10 PM Istanbul time** = **7 PM UTC** = Change cron to `'0 19 * * 2'`
- Keep `'0 22 * * 2'` for 10 PM UTC

Edit `.github/workflows/weekly-scraper.yml` and change the cron expression.

## What Gets Updated

After the workflow runs:
- All team Excel files (`.xlsx`)
- All team CSV files (`.csv`)
- Files are automatically committed and pushed to GitHub

## Pulling Changes Locally

After the workflow runs, pull the changes:

```bash
cd "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi"
git pull
```

## Next Steps After Scraping

You still need to:
1. Pull the updated Excel files
2. Run `python3 scripts/ingest_data.py` to regenerate `public/data.js`
3. Push to deploy the website

**Optional:** I can also automate steps 2-3 in the same workflow!

## Checking Logs

View logs on GitHub:
1. Go to "Actions" tab
2. Click on the latest workflow run
3. Click "scrape-matches"
4. Expand steps to see detailed logs

## Cost

GitHub Actions is **FREE** for public repositories and includes 2,000 minutes/month for private repos. This workflow uses ~2-5 minutes per run, so you're well within the free tier.

## Advantages Over Local (launchd)

✅ Runs even if your Mac is off  
✅ No need to keep your computer on  
✅ Cloud logs and monitoring  
✅ Can run on any schedule  
✅ Automatic version control

## Local vs Cloud: Which to Use?

- **GitHub Actions** (Cloud): Best if you want "set it and forget it"
- **launchd** (Local Mac): Best if you want more control and privacy

You can use both! They won't conflict.
