#!/usr/bin/env python3
"""
Sofascore Schedule Scraper for Turkish Super League
Uses Sofascore's internal API to fetch match schedules and results
"""

import json
import os
import argparse
from datetime import datetime
import requests

# Sofascore API constants
BASE_API_URL = "https://www.sofascore.com/api/v1"
TOURNAMENT_ID = 52  # Trendyol Süper Lig
SEASON_ID = 77805  # 2024-25 season

def fetch_season_rounds():
    """
    Fetch list of all rounds in the season
    
    Returns:
        dict: API response with rounds data including current round
    """
    url = f"{BASE_API_URL}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/rounds"
    
    print(f"Fetching rounds list from Sofascore API...")
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    print(f"✓ Found {len(data.get('rounds', []))} rounds")
    print(f"  Current round: {data.get('currentRound', {}).get('round', 'N/A')}")
    
    return data


def fetch_round_matches(round_number):
    """
    Fetch all matches for a specific round
    
    Args:
        round_number: Round number (1-34)
    
    Returns:
        list: List of match objects
    """
    url = f"{BASE_API_URL}/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{round_number}"
    
    response = requests.get(url)
    response.raise_for_status()
    
    data = response.json()
    return data.get('events', [])


def parse_match_data(match):
    """
    Parse match data from Sofascore API response
    
    Args:
        match: Raw match object from API
    
    Returns:
        dict: Cleaned match data
    """
    match_id = match.get('id')
    start_timestamp = match.get('startTimestamp')
    
    # Convert timestamp to datetime
    match_datetime = datetime.fromtimestamp(start_timestamp) if start_timestamp else None
    
    home_team = match.get('homeTeam', {})
    away_team = match.get('awayTeam', {})
    
    status = match.get('status', {})
    status_code = status.get('code')  # 0 = not started, 100 = finished
    
    # Extract actual scores if match is finished
    actual_score = None
    if status_code == 100:  # Match finished
        home_score_obj = match.get('homeScore', {})
        away_score_obj = match.get('awayScore', {})
        
        home_goals = home_score_obj.get('current')
        away_goals = away_score_obj.get('current')
        
        if home_goals is not None and away_goals is not None:
            actual_score = f"{home_goals}-{away_goals}"
    
    # Determine match status
    if status_code == 0:
        match_status = 'scheduled'
    elif status_code == 100:
        match_status = 'finished'
    else:
        match_status = 'in_progress'
    
    return {
        'match_id': match_id,
        'date': match_datetime.strftime('%Y-%m-%d') if match_datetime else None,
        'time': match_datetime.strftime('%H:%M') if match_datetime else None,
        'datetime_iso': match_datetime.isoformat() if match_datetime else None,
        'timestamp': start_timestamp,
        'home_team': home_team.get('name'),
        'home_team_id': home_team.get('id'),
        'away_team': away_team.get('name'),
        'away_team_id': away_team.get('id'),
        'actual_score': actual_score,
        'status': match_status
    }


def scrape_full_schedule():
    """
    Scrape the complete season schedule for all rounds
    
    Returns:
        dict: Complete season schedule data
    """
    # Get rounds metadata
    rounds_data = fetch_season_rounds()
    current_round = rounds_data.get('currentRound', {}).get('round', 1)
    
    schedule = {
        'season': '2024-25',
        'season_id': SEASON_ID,
        'tournament_id': TOURNAMENT_ID,
        'current_round': current_round,
        'scraped_at': datetime.now().isoformat(),
        'rounds': []
    }
    
    # Fetch matches for each round
    for round_info in rounds_data.get('rounds', []):
        round_num = round_info.get('round')
        
        if not round_num:
            continue
        
        print(f"\nFetching Round {round_num}...")
        
        try:
            matches_raw = fetch_round_matches(round_num)
            matches = [parse_match_data(m) for m in matches_raw]
            
            print(f"  ✓ {len(matches)} matches")
            
            # Print a sample match
            if matches:
                sample = matches[0]
                status_emoji = "✅" if sample['status'] == 'finished' else "📅"
                score_display = f"({sample['actual_score']})" if sample['actual_score'] else ""
                print(f"    {status_emoji} {sample['home_team']} vs {sample['away_team']} {score_display}")
            
            round_data = {
                'round': round_num,
                'matches': matches
            }
            schedule['rounds'].append(round_data)
        
        except Exception as e:
            print(f"  ✗ Error fetching round {round_num}: {e}")
            continue
    
    return schedule


def update_match_results(schedule_data, round_number=None):
    """
    Update schedule with latest actual results for specified round(s)
    
    Args:
        schedule_data: Existing schedule dictionary
        round_number: Specific round to update (None = all rounds)
    
    Returns:
        dict: Updated schedule
    """
    rounds_to_update = [round_number] if round_number else range(1, 35)
    
    for rnd in rounds_to_update:
        # Find the round in our schedule
        round_data = next((r for r in schedule_data['rounds'] if r['round'] == rnd), None)
        
        if not round_data:
            print(f"Round {rnd} not found in schedule, skipping...")
            continue
        
        print(f"\nUpdating results for Round {rnd}...")
        
        try:
            # Fetch latest data from API
            matches_raw = fetch_round_matches(rnd)
            
            # Update each match
            updates_count = 0
            for match_raw in matches_raw:
                match_id = match_raw.get('id')
                parsed = parse_match_data(match_raw)
                
                # Find matching entry in our schedule
                existing_match = next(
                    (m for m in round_data['matches'] if m['match_id'] == match_id),
                    None
                )
                
                if existing_match:
                    # Update with latest data
                    if parsed['actual_score'] and not existing_match.get('actual_score'):
                        print(f"  ✓ {parsed['home_team']} {parsed['actual_score']} {parsed['away_team']}")
                        updates_count += 1
                    
                    existing_match['actual_score'] = parsed['actual_score']
                    existing_match['status'] = parsed['status']
            
            if updates_count > 0:
                print(f"  Updated {updates_count} match results")
            else:
                print(f"  No new results found")
        
        except Exception as e:
            print(f"  ✗ Error updating round {rnd}: {e}")
    
    # Update metadata
    schedule_data['last_updated'] = datetime.now().isoformat()
    
    return schedule_data


def save_schedule(schedule_data, output_path):
    """Save schedule data to JSON file"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(schedule_data, f, ensure_ascii=False, indent=2)
    
    total_matches = sum(len(r['matches']) for r in schedule_data['rounds'])
    finished_matches = sum(
        1 for r in schedule_data['rounds']
        for m in r['matches']
        if m['status'] == 'finished'
    )
    
    print(f"\n{'='*60}")
    print(f"✓ Schedule saved to: {output_path}")
    print(f"  Total rounds: {len(schedule_data['rounds'])}")
    print(f"  Total matches: {total_matches}")
    print(f"  Finished matches: {finished_matches}")
    print(f"  Current round: {schedule_data.get('current_round', 'N/A')}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(
        description='Scrape Turkish Super League schedule from Sofascore API'
    )
    parser.add_argument(
        '--output',
        default='Data/schedule/season_schedule.json',
        help='Output JSON file path (relative to project root)'
    )
    parser.add_argument(
        '--update-results',
        action='store_true',
        help='Update existing schedule with latest match results'
    )
    parser.add_argument(
        '--round',
        type=int,
        help='Specific round number to update (1-34)'
    )
    
    args = parser.parse_args()
    
    # Get absolute output path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    output_path = os.path.join(project_root, args.output)
    
    if args.update_results:
        # Load existing schedule and update with latest results
        if not os.path.exists(output_path):
            print(f"Error: Schedule file not found at {output_path}")
            print("Run without --update-results first to create the schedule.")
            return
        
        print(f"Loading existing schedule from {output_path}...")
        with open(output_path, 'r', encoding='utf-8') as f:
            schedule_data = json.load(f)
        
        schedule_data = update_match_results(schedule_data, args.round)
        save_schedule(schedule_data, output_path)
    
    else:
        # Scrape full season schedule from scratch
        print("Scraping full season schedule from Sofascore API...")
        print(f"Tournament ID: {TOURNAMENT_ID}")
        print(f"Season ID: {SEASON_ID}\n")
        
        schedule_data = scrape_full_schedule()
        save_schedule(schedule_data, output_path)
        
        print("Next steps:")
        print("1. Review the generated JSON file")
        print("2. To update results later, run:")
        print(f"   python3 {__file__} --update-results")


if __name__ == '__main__':
    main()
