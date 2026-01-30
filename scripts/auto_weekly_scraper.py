#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Weekly Scraper for Turkish Super League
Scrapes completed matches from the current round and updates team Excel files.
"""

import os
import sys
import json
import time
import logging
from pathlib import Path
from datetime import datetime

# Import scraping functions from the existing scraper
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'Data', 'Scraping Code'))
from sofascore_scraper import fetch_event, fetch_lineups, fetch_stats, parse_team_stats, build_row, SofaScoreChallengeError
import pandas as pd

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
    "Fatih Karagümrük": DATA_DIR / "Fatih Karagümrük" / "mixed-seasons" / "Fatih Karagümrük_Games_Input.xlsx",
    "Gaziantep FK": DATA_DIR / "Gaziantep FK" / "mixed-seasons" / "Gaziantep FK_Games_Input.xlsx",
    "Gençlerbirliği": DATA_DIR / "Gençlerbirliği" / "mixed-seasons" / "Gençlerbirliği_Games_Input.xlsx",
    "Göztepe": DATA_DIR / "Göztepe" / "mixed-seasons" / "Göztepe_Games_Input.xlsx",
    "Kasımpaşa": DATA_DIR / "Kasımpaşa" / "mixed-seasons" / "Kasımpaşa_Games_Input.xlsx",
    "Kayserispor": DATA_DIR / "Kayserispor" / "mixed-seasons" / "Kayserispor_Games_Input.xlsx",
    "Kocaelispor": DATA_DIR / "Kocaelispor" / "mixed-seasons" / "Kocaelispor_Games_Input.xlsx",
    "Konyaspor": DATA_DIR / "Konyaspor" / "mixed-seasons" / "Konyaspor_Games_Input.xlsx",
    "Samsunspor": DATA_DIR / "Samsunspor" / "mixed-seasons" / "Samsunspor_Games_Input.xlsx",
}


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
        logging.error(f"❌ Error processing {team_name}: {e}")
        return False


def main():
    """Main automation logic."""
    logging.info("=" * 60)
    logging.info("Starting Automated Weekly Scraper")
    logging.info("=" * 60)
    
    # Load schedule
    schedule = load_schedule()
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
            
            # Polite delay between requests
            time.sleep(1.5)
    
    logging.info("=" * 60)
    logging.info(f"Scraping complete!")
    logging.info(f"✅ Success: {success_count}")
    logging.info(f"❌ Failed: {fail_count}")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
