#!/usr/bin/env python3
"""
Process futbin_players_league68.xlsx and generate players_data.js for the frontend.
This script reads player data, organizes it by team, and exports it as a JavaScript file.
"""

import pandas as pd
import json
import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
EXCEL_FILE = BASE_DIR / "Data" / "Scraping Code" / "futbin_players_league68.xlsx"
OUTPUT_FILE = BASE_DIR / "public" / "players_data.js"

def calculate_overall_rating(row):
    """Calculate a simple overall rating from main attributes."""
    main_attrs = ['Pace', 'Shooting', 'Passing', 'Dribbling', 'Defending', 'Physical']
    total = sum(row[attr] for attr in main_attrs if pd.notna(row[attr]))
    count = sum(1 for attr in main_attrs if pd.notna(row[attr]))
    return round(total / count) if count > 0 else 0

def clean_player_data(df):
    """Clean and structure player data for frontend consumption."""
    players_by_team = {}
    
    for idx, row in df.iterrows():
        team = row['Club']
        
        # Create player object with all attributes
        player = {
            'id': idx,
            'name': row['PlayerName'],
            'team': team,
            'nationality': row['Nationality'],
            'age': int(row['Age']) if pd.notna(row['Age']) else 0,
            'height': row['Height'] if pd.notna(row['Height']) else 'N/A',
            'foot': row['Foot'] if pd.notna(row['Foot']) else 'N/A',
            'bodyType': row['BodyType'] if pd.notna(row['BodyType']) else 'N/A',
            'rarity': row['Rarity'] if pd.notna(row['Rarity']) else 'N/A',
            'skills': int(row['Skills']) if pd.notna(row['Skills']) else 0,
            'weakFoot': int(row['WeakFoot']) if pd.notna(row['WeakFoot']) else 0,
            
            # Main attributes
            'pace': int(row['Pace']) if pd.notna(row['Pace']) else 0,
            'shooting': int(row['Shooting']) if pd.notna(row['Shooting']) else 0,
            'passing': int(row['Passing']) if pd.notna(row['Passing']) else 0,
            'dribbling': int(row['Dribbling']) if pd.notna(row['Dribbling']) else 0,
            'defending': int(row['Defending']) if pd.notna(row['Defending']) else 0,
            'physical': int(row['Physical']) if pd.notna(row['Physical']) else 0,
            
            # Detailed attributes - Pace
            'acceleration': int(row['Acceleration']) if pd.notna(row['Acceleration']) else 0,
            'sprintSpeed': int(row['Sprint Speed']) if pd.notna(row['Sprint Speed']) else 0,
            
            # Detailed attributes - Shooting
            'attPosition': int(row['Att. Position']) if pd.notna(row['Att. Position']) else 0,
            'finishing': int(row['Finishing']) if pd.notna(row['Finishing']) else 0,
            'shotPower': int(row['Shot Power']) if pd.notna(row['Shot Power']) else 0,
            'longShots': int(row['Long Shots']) if pd.notna(row['Long Shots']) else 0,
            'volleys': int(row['Volleys']) if pd.notna(row['Volleys']) else 0,
            'penalties': int(row['Penalties']) if pd.notna(row['Penalties']) else 0,
            
            # Detailed attributes - Passing
            'vision': int(row['Vision']) if pd.notna(row['Vision']) else 0,
            'crossing': int(row['Crossing']) if pd.notna(row['Crossing']) else 0,
            'fkAcc': int(row['FK Acc.']) if pd.notna(row['FK Acc.']) else 0,
            'shortPass': int(row['Short Pass']) if pd.notna(row['Short Pass']) else 0,
            'longPass': int(row['Long Pass']) if pd.notna(row['Long Pass']) else 0,
            'curve': int(row['Curve']) if pd.notna(row['Curve']) else 0,
            
            # Detailed attributes - Dribbling
            'agility': int(row['Agility']) if pd.notna(row['Agility']) else 0,
            'balance': int(row['Balance']) if pd.notna(row['Balance']) else 0,
            'reactions': int(row['Reactions']) if pd.notna(row['Reactions']) else 0,
            'ballControl': int(row['Ball Control']) if pd.notna(row['Ball Control']) else 0,
            'dribblingSub': int(row['Dribbling_Sub']) if pd.notna(row['Dribbling_Sub']) else 0,
            'composure': int(row['Composure']) if pd.notna(row['Composure']) else 0,
            
            # Detailed attributes - Defending
            'interceptions': int(row['Interceptions']) if pd.notna(row['Interceptions']) else 0,
            'headingAcc': int(row['Heading Acc.']) if pd.notna(row['Heading Acc.']) else 0,
            'defAware': int(row['Def. Aware']) if pd.notna(row['Def. Aware']) else 0,
            'standTackle': int(row['Stand Tackle']) if pd.notna(row['Stand Tackle']) else 0,
            'slideTackle': int(row['Slide Tackle']) if pd.notna(row['Slide Tackle']) else 0,
            
            # Detailed attributes - Physical
            'jumping': int(row['Jumping']) if pd.notna(row['Jumping']) else 0,
            'stamina': int(row['Stamina']) if pd.notna(row['Stamina']) else 0,
            'strength': int(row['Strength']) if pd.notna(row['Strength']) else 0,
            'aggression': int(row['Aggression']) if pd.notna(row['Aggression']) else 0,
        }
        
        # Calculate overall rating
        player['overall'] = calculate_overall_rating(row)
        
        # Add to team
        if team not in players_by_team:
            players_by_team[team] = []
        players_by_team[team].append(player)
    
    # Sort players within each team by overall rating (descending)
    for team in players_by_team:
        players_by_team[team].sort(key=lambda x: x['overall'], reverse=True)
    
    return players_by_team

def generate_js_file(players_by_team):
    """Generate JavaScript file with player data."""
    js_content = "// Auto-generated player data from futbin_players_league68.xlsx\n"
    js_content += "// Generated by scripts/process_players.py\n\n"
    js_content += "const playersData = "
    js_content += json.dumps(players_by_team, indent=2, ensure_ascii=False)
    js_content += ";\n\n"
    js_content += "// Get all team names\n"
    js_content += "const teamNames = Object.keys(playersData).sort();\n"
    
    return js_content

def main():
    print("Processing player data...")
    print(f"Reading from: {EXCEL_FILE}")
    
    # Read Excel file
    df = pd.read_excel(EXCEL_FILE)
    print(f"Loaded {len(df)} players")
    
    # Clean and structure data
    players_by_team = clean_player_data(df)
    print(f"Organized into {len(players_by_team)} teams")
    
    # Generate JavaScript file
    js_content = generate_js_file(players_by_team)
    
    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(js_content)
    
    print(f"Generated: {OUTPUT_FILE}")
    print("\nTeam breakdown:")
    for team, players in sorted(players_by_team.items()):
        print(f"  {team}: {len(players)} players")
    
    print("\n✅ Player data processing complete!")

if __name__ == "__main__":
    main()
