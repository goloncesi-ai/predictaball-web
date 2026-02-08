#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Weekly Scraper for Turkish Super League
Scrapes completed matches from the current round and updates team Excel files.
Uses the working manual scraper's functions directly.
"""

import os
import sys
import json
import time
import random
import logging
import argparse
import pandas as pd
from pathlib import Path
from datetime import datetime
import requests

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/auto_scraper.log'),
        logging.StreamHandler()
    ]
)

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "Data" / "Turkish Super League"
SCHEDULE_FILE = BASE_DIR / "Data" / "schedule" / "season_schedule.json"

# Import from the WORKING manual scraper
scraper_path = BASE_DIR / "Data" / "Scraping Code"
sys.path.insert(0, str(scraper_path))

# Import the working functions
import importlib.util
spec = importlib.util.spec_from_file_location(
    "sofascore_scraper",
    scraper_path / "python sofascore_scraper.py"
)
sofascore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sofascore)

# Use the working scraper's functions
fetch_event = sofascore.fetch_event
fetch_lineups = sofascore.fetch_lineups
fetch_stats = sofascore.fetch_stats
parse_team_stats = sofascore.parse_team_stats
build_row = sofascore.build_row
SofaScoreChallengeError = sofascore.SofaScoreChallengeError

# Team name to Excel file path mapping
TEAM_PATHS = {
    "Fenerbahçe": DATA_DIR / "Fenerbahçe" / "mixed-seasons" / "Fenerbahçe_Games_Input.xlsx",
    "Galatasaray": DATA_DIR / "Galatasaray" / "mixed-seasons" / "Galatasaray_Games_Input.xlsx",
    "Beşiktaş JK": DATA_DIR / "Beşiktaş" / "mixed-seasons" / "Beşiktaş_Games_Input.xlsx",
    "Trabzonspor": DATA_DIR / "Trabzonspor" / "mixed-seasons" / "Trabzonspor_Games_Input.xlsx",
    "Alanyaspor": DATA_DIR / "Alanyaspor" / "mixed-seasons" / "Alanyaspor_Games_Input.xlsx",
    "Antalyaspor": DATA_DIR / "Antalyaspor" / "mixed-seasons" / "Antalyaspor_Games_Input.xlsx",
    "Başakşehir FK": DATA_DIR / "Başakşehir" / "mixed-seasons" / "Başakşehir_Games_Input.xlsx",
    "Çaykur Rizespor": DATA_DIR / "Çaykur Rizespor" / "mixed-seasons" / "Çaykur Rizespor_Games_Input.xlsx",
    "Eyüpspor": DATA_DIR / "Eyüpspor" / "mixed-seasons" / "Eyüpspor_Games_Input.xlsx",
    "Fatih Karagümrük": DATA_DIR / "Karagümrük" / "mixed-seasons" / "Karagümrük_Games_Input.xlsx",
    "Gaziantep FK": DATA_DIR / "Gaziantep" / "mixed-seasons" / "Gaziantep_Games_Input.xlsx",
    "Gençlerbirliği": DATA_DIR / "Gençlerbirliği" / "mixed-seasons" / "Gençlerbirliği_Games_Input.xlsx",
    "Göztepe": DATA_DIR / "Göztepe" / "mixed-seasons" / "Göztepe_Games_Input.xlsx",
    "Kasımpaşa": DATA_DIR / "Kasımpaşa" / "mixed-seasons" / "Kasımpaşa_Games_Input.xlsx",
    "Kayserispor": DATA_DIR / "Kayserispor" / "mixed-seasons" / "Kayserispor_Games_Input.xlsx",
    "Kocaelispor": DATA_DIR / "Kocaelispor" / "mixed-seasons" / "Kocaelispor_Games_Input.xlsx",
    "Konyaspor": DATA_DIR / "Konyaspor" / "mixed-seasons" / "Konyaspor_Games_Input.xlsx",
    "Samsunspor": DATA_DIR / "Samsunspor" / "mixed-seasons" / "Samsunspor_Games_Input.xlsx",
}


# ============================================================================
# Automation Logic
# ============================================================================

def refresh_schedule():
    """Update season_schedule.json with latest results and current round from Sofascore."""
    logging.info("Refreshing schedule from Sofascore API...")
    
    API_BASE = "https://www.sofascore.com/api/v1"
    TOURNAMENT_ID = 52
    SEASON_ID = 77805
    
    try:
        # 1. Fetch rounds to get current round
        rounds_url = f"{API_BASE}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/rounds"
        r = requests.get(rounds_url, timeout=25)
        r.raise_for_status()
        rounds_data = r.json()
        
        current_round = rounds_data.get('currentRound', {}).get('round', 19)
        logging.info(f"API says current round is: {current_round}")
        
        # 2. Load existing schedule
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
        
        # 3. Update current_round if it changed
        old_round = schedule.get('current_round')
        schedule['current_round'] = current_round
        if old_round != current_round:
            logging.info(f"Updated current_round from {old_round} to {current_round}")
        
        # 4. Refresh match statuses for the current round (and maybe the previous one just in case)
        # We'll update the current round and the one before it
        rounds_to_refresh = [current_round]
        if current_round > 1:
            rounds_to_refresh.append(current_round - 1)
            
        for rnd_num in rounds_to_refresh:
            logging.info(f"Refreshing statuses for Round {rnd_num}...")
            matches_url = f"{API_BASE}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{rnd_num}"
            r = requests.get(matches_url, timeout=25)
            r.raise_for_status()
            events = r.json().get('events', [])
            
            # Find the round in our local schedule
            local_round = next((r for r in schedule.get('rounds', []) if r['round'] == rnd_num), None)
            if not local_round:
                logging.warning(f"Round {rnd_num} not found in local schedule.json")
                continue
                
            for event in events:
                match_id = event.get('id')
                status_code = event.get('status', {}).get('code')
                
                # Find matching match in local schedule
                local_match = next((m for m in local_round['matches'] if m['match_id'] == match_id), None)
                if local_match:
                    # Update status
                    if status_code == 100:
                        local_match['status'] = 'finished'
                        # Also update score if available
                        home_score = event.get('homeScore', {}).get('current')
                        away_score = event.get('awayScore', {}).get('current')
                        if home_score is not None and away_score is not None:
                            local_match['actual_score'] = f"{home_score}-{away_score}"
                    elif status_code == 0:
                        local_match['status'] = 'scheduled'
                    else:
                        local_match['status'] = 'in_progress'
        
        # 5. Save updated schedule
        schedule['scraped_at'] = datetime.now().isoformat()
        with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
            json.dump(schedule, f, indent=2, ensure_ascii=False)
            
        logging.info("✅ Schedule refreshed successfully.")
        return schedule
        
    except Exception as e:
        logging.error(f"❌ Failed to refresh schedule: {e}")
        # Return existing schedule as fallback
        with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)


def load_schedule():
    """Load the season schedule JSON."""
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_current_round_matches(schedule):
    """Get all finished matches from the current round."""
    current_round = schedule.get('current_round', 19)
    logging.info(f"Current round: {current_round}")
    
    for round_data in schedule.get('rounds', []):
        if round_data['round'] == current_round:
            finished_matches = [
                m for m in round_data['matches']
                if m.get('status') == 'finished' and m.get('match_id')
            ]
            logging.info(f"Found {len(finished_matches)} finished matches in round {current_round}")
            return finished_matches
    
    logging.warning(f"No data found for round {current_round}")
    return []


def scrape_and_append(match_id, team_name, team_path):
    """Scrape match data and append to team's Excel file."""
    try:
        # Fetch data from Sofascore
        logging.info(f"Fetching match data for ID {match_id}, team: {team_name}")
        event = fetch_event(match_id)
        lineups = fetch_lineups(match_id)
        stats = fetch_stats(match_id)
        stats_dict = parse_team_stats(stats)
        
        home = event["event"]["homeTeam"]["name"]
        away = event["event"]["awayTeam"]["name"]
        logging.info(f"Match: {home} vs {away}")
        
        # Build row
        row = build_row(event, lineups, stats_dict, team_name)
        
        # Load existing Excel or create new
        if team_path.exists():
            df_old = pd.read_excel(team_path)
        else:
            logging.warning(f"File not found: {team_path}, creating new")
            df_old = None
        
        # Define column order
        base = ["Team1", "Team2", "Team1H_A", "Team1Formation", "Team2Formation", "Win(3)_Draw(1)_Lose(0)"]
        t1_names = [f"Team1Player{i}Name" for i in range(1, 12)]
        t2_names = [f"Team2Player{i}Name" for i in range(1, 12)]
        t1_rates = [f"Team1Player{i}" for i in range(1, 12)]
        t2_rates = [f"Team2Player{i}" for i in range(1, 12)]
        goals = ["Team1_Goals", "Team2_Goals"]
        stats_cols = [
            "Team1_BigChances", "Team1_TotalShots", "Team1_Corners", "Team1_Passes", "Team1_Tackels",
            "Team1_FreeKicks", "Team1_BallPosses",
            "Team2_BigChances", "Team2_TotalShots", "Team2_Corners", "Team2_Passes", "Team2_Tackels",
            "Team2_FreeKicks", "Team2_BallPosses"
        ]
        col_order = base + t1_names + t2_names + t1_rates + t2_rates + goals + stats_cols
        
        # Create new dataframe
        df_new = pd.DataFrame([row])
        for c in col_order:
            if c not in df_new.columns:
                df_new[c] = None
        df_new = df_new[col_order]
        
        # Type conversions
        for c in t1_rates + t2_rates:
            df_new[c] = pd.to_numeric(df_new[c], errors="coerce")
        
        int_cols = [
            "Team1_Goals", "Team2_Goals",
            "Team1_BigChances", "Team1_TotalShots", "Team1_Corners", "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks",
            "Team2_BigChances", "Team2_TotalShots", "Team2_Corners", "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks",
        ]
        for c in int_cols:
            df_new[c] = pd.to_numeric(df_new[c], errors="coerce").astype("Int64")
        
        for c in ["Team1_BallPosses", "Team2_BallPosses"]:
            df_new[c] = df_new[c].astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
            df_new[c] = pd.to_numeric(df_new[c], errors="coerce") / 100
        
        # Merge with existing
        if df_old is not None:
            for c in df_new.columns:
                if c not in df_old.columns:
                    df_old[c] = None
            for c in df_old.columns:
                if c not in df_new.columns:
                    df_new[c] = None
            df_old = df_old[df_new.columns]
            df_combined = pd.concat([df_new, df_old], ignore_index=True)
        else:
            df_combined = df_new
        
        # Create directory if it doesn't exist
        team_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save
        df_combined.to_excel(team_path, index=False)
        csv_path = team_path.with_suffix('.csv')
        df_combined.to_csv(csv_path, index=False)
        
        logging.info(f"✅ Updated {team_path.name}")
        return True
        
    except SofaScoreChallengeError as e:
        logging.error(f"❌ Cloudflare challenge detected: {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Error processing {team_name}: {e}", exc_info=True)
        return False



def main(force_round=None):
    """Main automation logic.
    
    Args:
        force_round: If provided, override the automatically detected round and scrape this round instead.
    """
    logging.info("=" * 60)
    logging.info("Starting Automated Weekly Scraper")
    logging.info("=" * 60)
    
    # Refresh schedule first to get latest round and statuses
    schedule = refresh_schedule()
    
    # Allow manual override of round (for missed rounds)
    if force_round is not None:
        logging.info(f"⚠️  MANUAL OVERRIDE: Forcing round to {force_round}")
        schedule['current_round'] = force_round
    
    matches = get_current_round_matches(schedule)
    
    if not matches:
        logging.warning("No matches to process. Exiting.")
        return
    
    # Track processed matches to avoid duplicates
    processed = set()
    success_count = 0
    fail_count = 0
    
    for match in matches:
        match_id = match['match_id']
        home_team = match['home_team']
        away_team = match['away_team']
        
        # Process both teams
        for team_name in [home_team, away_team]:
            if team_name not in TEAM_PATHS:
                logging.warning(f"⚠️  No path mapping for team: {team_name}")
                continue
            
            # Create unique key to avoid processing same match+team twice
            key = f"{match_id}_{team_name}"
            if key in processed:
                continue
            
            team_path = TEAM_PATHS[team_name]
            
            # Scrape and append
            success = scrape_and_append(match_id, team_name, team_path)
            processed.add(key)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # Longer, randomized delay between requests (2-4 seconds)
            time.sleep(2.0 + random.random() * 2.0)
    
    logging.info("=" * 60)
    logging.info(f"Scraping complete!")
    logging.info(f"✅ Success: {success_count}")
    logging.info(f"❌ Failed: {fail_count}")
    logging.info("=" * 60)
    
    # Step 2: Run ingest_data.py if scraping was successful
    if success_count > 0:
        logging.info("")
        logging.info("=" * 60)
        logging.info("Step 2: Updating website data (data.js)...")
        logging.info("=" * 60)
        
        try:
            import subprocess
            ingest_script = BASE_DIR / "scripts" / "ingest_data.py"
            result = subprocess.run(
                ["/Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10", str(ingest_script)],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if result.returncode == 0:
                logging.info("✅ Successfully updated data.js")
                logging.info(result.stdout)
            else:
                logging.error(f"❌ Failed to update data.js: {result.stderr}")
                return
                
        except Exception as e:
            logging.error(f"❌ Error running ingest_data.py: {e}")
            return
        
        # Step 3: Commit and push to GitHub
        logging.info("")
        logging.info("=" * 60)
        logging.info("Step 3: Committing and pushing to GitHub...")
        logging.info("=" * 60)
        
        try:
            # Check if there are changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(BASE_DIR),
                capture_output=True,
                text=True
            )
            
            if result.stdout.strip():
                # Add all changes
                subprocess.run(["git", "add", "Data/", "public/data.js"], cwd=str(BASE_DIR), check=True)
                
                # Commit
                from datetime import datetime
                commit_msg = f"🤖 Auto-update: Round {schedule.get('current_round', '?')} data ({datetime.now().strftime('%Y-%m-%d')})"
                subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(BASE_DIR), check=True)
                
                # Push
                subprocess.run(["git", "push"], cwd=str(BASE_DIR), check=True)
                
                logging.info("✅ Successfully pushed to GitHub - Website will auto-deploy!")
            else:
                logging.info("ℹ️  No changes to commit")
                
        except subprocess.CalledProcessError as e:
            logging.error(f"❌ Git error: {e}")
        except Exception as e:
            logging.error(f"❌ Error during commit/push: {e}")
    
    logging.info("")
    logging.info("=" * 60)
    logging.info("🎉 Full automation complete!")
    logging.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Automated weekly scraper for Turkish Super League',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Normal automatic run (uses current round from API)
  python3 auto_weekly_scraper.py
  
  # Manual override to scrape a specific round
  python3 auto_weekly_scraper.py --round 20
        """
    )
    parser.add_argument(
        '--round',
        type=int,
        help='Override automatic round detection and scrape a specific round'
    )
    
    args = parser.parse_args()
    main(force_round=args.round)
