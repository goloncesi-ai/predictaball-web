#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Schedule Updater for Turkish Super League
Updates match statuses and scores in season_schedule.json
"""

import json
import time
import random
import logging
import requests
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Paths
BASE_DIR = Path(__file__).parent.parent
SCHEDULE_FILE = BASE_DIR / "Data" / "schedule" / "season_schedule.json"

# Sofascore API
API_BASE = "https://api.sofascore.com/api/v1"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/"
})


def polite_sleep():
    """Add delay between requests to be polite to the API."""
    time.sleep(0.8 + random.random() * 0.8)


def get_match_status(match_id):
    """Fetch current status and score for a match from Sofascore."""
    try:
        polite_sleep()
        url = f"{API_BASE}/event/{match_id}"
        response = SESSION.get(url, timeout=25)
        
        if not response.ok:
            logging.warning(f"Failed to fetch match {match_id}: {response.status_code}")
            return None
        
        data = response.json()
        event = data.get("event", {})
        
        # Get status
        status_obj = event.get("status", {})
        status_code = status_obj.get("code")
        status_type = status_obj.get("type")
        
        # Map Sofascore status to our format
        if status_code == 100 or status_type == "finished":
            status = "finished"
        elif status_code == 0 or status_type == "notstarted":
            status = "scheduled"
        elif status_type == "inprogress":
            status = "in_progress"
        else:
            status = "scheduled"
        
        # Get score if finished
        actual_score = None
        if status == "finished":
            home_score = event.get("homeScore", {}).get("current") or event.get("homeScore", {}).get("display")
            away_score = event.get("awayScore", {}).get("current") or event.get("awayScore", {}).get("display")
            if home_score is not None and away_score is not None:
                actual_score = f"{home_score}-{away_score}"
        
        return {
            "status": status,
            "actual_score": actual_score
        }
        
    except Exception as e:
        logging.error(f"Error fetching match {match_id}: {e}")
        return None


def update_schedule():
    """Update the schedule file with latest match statuses."""
    logging.info("=" * 60)
    logging.info("Starting Schedule Update")
    logging.info("=" * 60)
    
    # Load schedule
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        schedule = json.load(f)
    
    current_round = schedule.get('current_round', 19)
    logging.info(f"Current round: {current_round}")
    
    # Find current round
    round_data = None
    for r in schedule.get('rounds', []):
        if r.get('round') == current_round:
            round_data = r
            break
    
    if not round_data:
        logging.error(f"Round {current_round} not found in schedule")
        return
    
    matches = round_data.get('matches', [])
    logging.info(f"Found {len(matches)} matches in round {current_round}")
    
    updated_count = 0
    
    # Update each match
    for match in matches:
        match_id = match.get('match_id')
        if not match_id:
            continue
        
        home_team = match.get('home_team', 'Unknown')
        away_team = match.get('away_team', 'Unknown')
        current_status = match.get('status', 'scheduled')
        
        logging.info(f"Checking: {home_team} vs {away_team} (ID: {match_id})")
        
        # Fetch latest status
        latest = get_match_status(match_id)
        
        if latest:
            # Update if changed
            if latest['status'] != current_status or latest['actual_score'] != match.get('actual_score'):
                match['status'] = latest['status']
                match['actual_score'] = latest['actual_score']
                updated_count += 1
                logging.info(f"  ✅ Updated: {latest['status']} - {latest['actual_score']}")
            else:
                logging.info(f"  ⏭️  No change: {current_status}")
    
    # Update scraped_at timestamp
    schedule['scraped_at'] = datetime.utcnow().isoformat()
    
    # Save updated schedule
    with open(SCHEDULE_FILE, 'w', encoding='utf-8') as f:
        json.dump(schedule, f, indent=2, ensure_ascii=False)
    
    logging.info("=" * 60)
    logging.info(f"Schedule update complete!")
    logging.info(f"✅ Updated: {updated_count} matches")
    logging.info("=" * 60)


if __name__ == "__main__":
    update_schedule()
