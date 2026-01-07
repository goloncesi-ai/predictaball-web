import os
import pandas as pd
import glob
import json
import unicodedata
import re

# Base paths
BASE_DIR = "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League"
OUTPUT_FILE = "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/data.js"

def normalize_name(name):
    """Normalize unicode characters to NFC form."""
    if not isinstance(name, str):
        return ""
    return unicodedata.normalize('NFC', name).strip()

def scan_and_process():
    teams_data = []
    # Dictionary to aggregate player stats: { "PlayerName": { "team": "TeamName", "ratings": [], "games": 0, "avg_rating": 0.0 } }
    players_data = {}

    print(f"Scanning directory: {BASE_DIR}")
    if not os.path.exists(BASE_DIR):
        print("Error: Base directory does not exist.")
        return

    all_entries = os.listdir(BASE_DIR)
    print(f"Found {len(all_entries)} entries in base directory.")

    # Iterate over directories
    for raw_team_name in all_entries:
        team_name = normalize_name(raw_team_name)
        team_path = os.path.join(BASE_DIR, raw_team_name)
        
        if not os.path.isdir(team_path):
            continue

        mixed_seasons_path = os.path.join(team_path, "mixed-seasons")
        if not os.path.exists(mixed_seasons_path):
            print(f"Skipping {team_name}: 'mixed-seasons' folder not found.")
            continue
            
        data_file = None
        try:
            files_in_mixed = os.listdir(mixed_seasons_path)
            csvs = [f for f in files_in_mixed if f.endswith('.csv') and "_Games_Input" in f]
            xlsxs = [f for f in files_in_mixed if f.endswith('.xlsx') and "_Games_Input" in f]
            
            if csvs:
                data_file = os.path.join(mixed_seasons_path, csvs[0])
            elif xlsxs:
                data_file = os.path.join(mixed_seasons_path, xlsxs[0])
                
        except Exception as e:
            print(f"Error listing files for {team_name}: {e}")
            continue
        
        if not data_file:
            print(f"No suitable data file found for {team_name}")
            continue
            
        try:
            if data_file.endswith('.csv'):
                df = pd.read_csv(data_file)
            else:
                df = pd.read_excel(data_file)
                
            # Process Team Stats
            stats = process_team_df(df, team_name)
            if stats:
                teams_data.append(stats)
                print(f"Processed Team Stats: {team_name}")
            else:
                print(f"Failed to extract stats for {team_name}")

            # Process Player Stats
            process_players_df(df, team_name, players_data)
                
        except Exception as e:
            print(f"Error reading/processing {team_name}: {e}")

    # Finalize Player Stats (Calculate Avg)
    final_players_list = []
    for pname, pdata in players_data.items():
        if pdata['games'] > 0:
            # Extract just ratings for avg calc
            ratings_only = [r['rating'] for r in pdata['ratings']]
            avg = sum(ratings_only) / pdata['games']
            
            final_players_list.append({
                "name": pname,
                "team": pdata['team'],
                "avg_rating": round(avg, 2),
                "games": pdata['games'],
                "ratings": pdata['ratings'] # Now list of {rating, opponent}
            })
    
    # Sort data
    teams_data.sort(key=lambda x: x['name'])
    final_players_list.sort(key=lambda x: x['name'])

    # Write to JS file with TWO variables
    teams_json = json.dumps(teams_data, indent=2)
    players_json = json.dumps(final_players_list, indent=2)
    
    js_content = f"window.teamData = {teams_json};\n\nwindow.playerData = {players_json};"
    
    with open(OUTPUT_FILE, 'w') as f:
        f.write(js_content)
    
    print(f"Successfully wrote data for {len(teams_data)} teams and {len(final_players_list)} players to {OUTPUT_FILE}")

def process_team_df(df, team_name):
    stats_acc = {
        'games': 0, 'goals_scored': 0, 'goals_conceded': 0,
        'shots': 0, 'possession_sum': 0.0, 'corners': 0,
        'wins': 0, 'draws': 0, 'losses': 0
    }
    
    cols_to_numeric = [
        'Team1_Goals', 'Team2_Goals', 'Team1_TotalShots', 'Team2_TotalShots',
        'Team1_BallPosses', 'Team2_BallPosses', 'Team1_Corners', 'Team2_Corners'
    ]
    for c in cols_to_numeric:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)

    for _, row in df.iterrows():
        t1 = str(row.get('Team1', ''))
        t2 = str(row.get('Team2', ''))
        
        is_team1 = fuzz_match(team_name, t1)
        is_team2 = fuzz_match(team_name, t2)
        
        if not is_team1 and not is_team2:
            continue
            
        stats_acc['games'] += 1
        
        if is_team1:
            my_goals = row.get('Team1_Goals', 0)
            op_goals = row.get('Team2_Goals', 0)
            my_shots = row.get('Team1_TotalShots', 0)
            my_poss = row.get('Team1_BallPosses', 0)
            my_corners = row.get('Team1_Corners', 0)
        else:
            my_goals = row.get('Team2_Goals', 0)
            op_goals = row.get('Team1_Goals', 0)
            my_shots = row.get('Team2_TotalShots', 0)
            my_poss = row.get('Team2_BallPosses', 0)
            my_corners = row.get('Team2_Corners', 0)
            
        stats_acc['goals_scored'] += my_goals
        stats_acc['goals_conceded'] += op_goals
        stats_acc['shots'] += my_shots
        stats_acc['possession_sum'] += my_poss
        stats_acc['corners'] += my_corners
        
        if my_goals > op_goals: stats_acc['wins'] += 1
        elif my_goals == op_goals: stats_acc['draws'] += 1
        else: stats_acc['losses'] += 1

    if stats_acc['games'] == 0:
        return None
        
    g = stats_acc['games']
    return {
        'name': team_name,
        'stats': {
            'win_rate': stats_acc['wins'] / g,
            'avg_goals_scored': stats_acc['goals_scored'] / g,
            'avg_goals_conceded': stats_acc['goals_conceded'] / g,
            'avg_shots': stats_acc['shots'] / g,
            'avg_possession': stats_acc['possession_sum'] / g,
            'avg_corners': stats_acc['corners'] / g,
            'total_games': g
        }
    }

def process_players_df(df, team_name, players_dict):
    """
    Extract player ratings.
    Columns: Team1Player1Name...Team1Player11Name, Team2Player1Name...
    Ratings: Team1Player1...Team1Player11 (Note: Rating columns usually lack 'Name' suffix)
    The CSV analysis showed: 
    Team1Player1Name (Name) -> Team1Player1 (Rating)
    """
    
    # Pre-process columns to find player columns
    # We iterate 1 to 11
    
    for _, row in df.iterrows():
        t1 = str(row.get('Team1', ''))
        t2 = str(row.get('Team2', ''))
        
        # Determine if this match belongs to the team we are currently processing (team_name)
        # We only want to process players FOR THIS TEAM to tag them correctly.
        # Actually, players might move or appear in opponent lists. 
        # But for simplicity, we assign "Team" based on the folder we are in.
        
        is_team1 = fuzz_match(team_name, t1)
        is_team2 = fuzz_match(team_name, t2)
        
        if not is_team1 and not is_team2:
            continue
            
        target_side = "Team1" if is_team1 else "Team2"
        # Opponent name for context?
        opponent = t2 if is_team1 else t1
        
        # Iterate players 1-11
        for i in range(1, 12):
            name_col = f"{target_side}Player{i}Name"
            rating_col = f"{target_side}Player{i}"
            
            p_name = row.get(name_col)
            try:
                p_rating = float(row.get(rating_col, 0))
            except:
                p_rating = 0.0
                
            if isinstance(p_name, str) and len(p_name) > 1 and p_rating > 0:
                p_name_clean = normalize_name(p_name)
                
                if p_name_clean not in players_dict:
                    players_dict[p_name_clean] = {
                        "team": team_name, # Assign current folder team
                        "ratings": [],
                        "games": 0
                    }
                else:
                    # Update team if they played most recently for this team?
                    # Or just keep first found? For now keeping first found is okay, or overwrite.
                    # Overwriting might be better if they transferred.
                    players_dict[p_name_clean]["team"] = team_name
                
                players_dict[p_name_clean]["ratings"].append({
                    "rating": p_rating,
                    "opponent": opponent
                })
                players_dict[p_name_clean]["games"] += 1

def fuzz_match(target, candidate):
    def clean(s): 
        s_nfd = unicodedata.normalize('NFD', s)
        s_base = ''.join(c for c in s_nfd if unicodedata.category(c) != 'Mn')
        return re.sub(r'[\W_]+', '', s_base.lower())
    return clean(target) in clean(candidate)

if __name__ == "__main__":
    scan_and_process()
