# Setup Instructions for Automated Weekly Scraping

## Overview
This guide will help you set up automated weekly scraping of Turkish Super League match data from Sofascore. The automation runs every Tuesday at 11 PM.

## Files Created
1. `scripts/auto_weekly_scraper.py` - The automated scraping script
2. `scripts/com.goloncesi.weekly-scraper.plist` - macOS scheduler configuration
3. `scripts/AUTOMATION_SETUP.md` - This file

## How It Works
1. Every Tuesday at 11 PM, the script automatically runs
2. It reads `Data/schedule/season_schedule.json` to find the current round
3. For each finished match in that round:
   - Fetches data from Sofascore API
   - Updates both home and away team Excel files
   - Saves both XLSX and CSV versions
4. Generates predictions for the next scheduled round using `scripts/weekly_predictions.py`
5. Commits and pushes updated data/predictions so the Recent Games tab refreshes

## Setup (macOS - launchd)

### Step 1: Load the Schedule
```bash
cd "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi"
launchctl load ~/Library/LaunchAgents/com.goloncesi.weekly-scraper.plist
```

### Step 2: Copy the plist file to LaunchAgents
```bash
cp scripts/com.goloncesi.weekly-scraper.plist ~/Library/LaunchAgents/
```

### Step 3: Load the scheduler
```bash
launchctl load ~/Library/LaunchAgents/com.goloncesi.weekly-scraper.plist
```

### Step 4: Verify it's loaded
```bash
launchctl list | grep goloncesi
```

## Manual Testing

Before waiting for Tuesday, you can test the script manually:

```bash
cd "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi"
python3 scripts/auto_weekly_scraper.py
```

## Manual Round Override

If you need to manually scrape a specific round (e.g., if you missed Round 20):

```bash
cd "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi"
python3 scripts/auto_weekly_scraper.py --round 20
```

This will:
- Still refresh the schedule from the API (to get latest statuses)
- Override the automatic round detection
- Scrape all finished matches from the specified round
- Update data.js and push to GitHub

**Note:** This is intended for one-time manual corrections. The automated scheduler will continue to use automatic round detection.

## Logs

Check logs to see if the automation is working:
- Main log: `/tmp/auto_scraper.log`
- Standard output: `/tmp/weekly-scraper-stdout.log`
- Standard error: `/tmp/weekly-scraper-stderr.log`

```bash
tail -f /tmp/auto_scraper.log
```

## Stopping the Automation

If you need to stop the weekly automation:

```bash
launchctl unload ~/Library/LaunchAgents/com.goloncesi.weekly-scraper.plist
```

## Modifying the Schedule

To change the time or day, edit the plist file:
- `Weekday`: 0=Sunday, 1=Monday, 2=Tuesday, etc.
- `Hour`: 0-23 (24-hour format)
- `Minute`: 0-59

After editing, reload:
```bash
launchctl unload ~/Library/LaunchAgents/com.goloncesi.weekly-scraper.plist
launchctl load ~/Library/LaunchAgents/com.goloncesi.weekly-scraper.plist
```

## Team Path Mapping

The script currently supports these teams:
- Fenerbahçe, Galatasaray, Beşiktaş JK, Trabzonspor
- Alanyaspor, Antalyaspor, Başakşehir FK
- Çaykur Rizespor, Eyüpspor, Fatih Karagümrük
- Gaziantep FK, Gençlerbirliği, Göztepe
- Kasımpaşa, Kayserispor, Kocaelispor, Konyaspor, Samsunspor

If a team is not in the list, you'll see a warning in the logs, and you can add it to the `TEAM_PATHS` dictionary in `auto_weekly_scraper.py`.

## Troubleshooting

### Cloudflare Blocks
If Sofascore blocks the scraper with a Cloudflare challenge, you'll see errors in the logs. Solutions:
1. Wait 15-60 minutes and try again
2. Open sofascore.com in your browser first (to pass the challenge)
3. Try from a different network (e.g., phone hotspot)

### Missing Matches
If some matches aren't being processed:
1. Check that `season_schedule.json` is up to date
2. Verify the match status is "finished"
3. Check logs for specific errors

### Permission Issues
If the script can't write to Excel files:
```bash
chmod +x scripts/auto_weekly_scraper.py
```

## Alternative: GitHub Actions (Cloud-Based)

If you want cloud-based scheduling instead of running on your Mac, let me know and I can create a GitHub Actions workflow that runs in the cloud every Tuesday at 10 PM.

## Next Steps After Scraping

All steps are now automated:
1. Scrape + update team files
2. Regenerate `public/data.js`
3. Generate upcoming round predictions JSON
4. Commit + push to GitHub
