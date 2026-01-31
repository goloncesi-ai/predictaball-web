import os
import json
import pandas as pd
import unicodedata

# Configuration
BASE_DATA_PATH = "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League"
OUTPUT_JSON_PATH = "/Users/erdilsen/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/public/data/players"

def normalize_filename(name):
    """Normalize string for filename: lowercase, remove accents/spaces."""
    if not name: return "unknown"
    n = unicodedata.normalize('NFKD', str(name)).encode('ASCII', 'ignore').decode('utf-8')
    return n.lower().replace(" ", "").replace("-", "")

def process_team(team_folder_name):
    """Process a single team folder and return player data list."""
    team_path = os.path.join(BASE_DATA_PATH, team_folder_name)
    players_path = os.path.join(team_path, "Players")
    
    if not os.path.exists(players_path):
        print(f"Skipping {team_folder_name}: No 'Players' folder found.")
        return None

    # Find the scraped Excel file
    # We look for files ending in .xlsx and containing "PlayerDetail"
    # e.g. Galatasaray_PlayerDetail_52_77805.xlsx
    xlsx_file = None
    for f in os.listdir(players_path):
        if f.endswith(".xlsx") and "PlayerDetail" in f:
            xlsx_file = os.path.join(players_path, f)
            break
            
    if not xlsx_file:
        print(f"Skipping {team_folder_name}: No PlayerDetail Excel file found.")
        return None

    print(f"Processing {team_folder_name} -> {os.path.basename(xlsx_file)}...")
    
    try:
        # Read Excel sheets
        df_profile = pd.read_excel(xlsx_file, sheet_name="Profile")
        df_stats = pd.read_excel(xlsx_file, sheet_name="Stats")
        
        # Convert to dictionary for easier lookup (assume Name is unique enough for now, 
        # ideally we'd join on ID if available in both, but scraper saves Name in both)
        stats_map = {}
        if not df_stats.empty:
            # Check required columns exist
            cols = df_stats.columns
            # Helper to safely get value or 0
            def get_val(row, col):
                return row[col] if col in row else 0

            for _, row in df_stats.iterrows():
                name = row.get("Name")
                if not name: continue
                
                # Check for HasTournamentStats flag (added in recent scraper fix)
                has_stats = row.get("HasTournamentStats", True)
                
                stats_obj = {
                    "hasStats": bool(has_stats),
                    "appearances": get_val(row, "appearances"),
                    "goals": get_val(row, "goals"),
                    "assists": get_val(row, "assists"),
                    "minutesPlayed": get_val(row, "minutesPlayed"),
                    "rating": get_val(row, "rating"),
                    "yellowCards": get_val(row, "yellowCards"),
                    "redCards": get_val(row, "redCards")
                }
                stats_map[name] = stats_obj

        # Build Player List
        players = []
        for _, row in df_profile.iterrows():
            name = row.get("Name")
            if not name: continue
            
            # Basic Profile
            p = {
                "id": str(row.get("ShirtNumber", "")) + "_" + normalize_filename(name), # Temporary ID if none
                "name": name,
                "position": row.get("Position", ""),
                "shirtNumber": row.get("ShirtNumber", ""),
                "nationality": row.get("Nationality", ""),
                "age": row.get("Age", ""),
                "height": row.get("Height_cm", ""),
                "preferredFoot": row.get("PreferredFoot", ""),
                "team": row.get("Team", ""),
                "stats": stats_map.get(name, {
                    "hasStats": False,
                    "appearances": 0,
                    "goals": 0, 
                    "rating": None
                }) 
            }
            
            # Construct Image URL (using SofaScore ID pattern if we can find it, 
            # currently Scraper output doesn't explicitly save PlayerID in Profile sheet
            # but usually Name is good enough for display. 
            # Future improvement: Save PlayerID in Profile sheet)
            
            players.append(p)
            
        return players

    except Exception as e:
        print(f"Error processing {team_folder_name}: {e}")
        return None

def main():
    if not os.path.exists(BASE_DATA_PATH):
        print(f"Error: Base path not found: {BASE_DATA_PATH}")
        return

    # Create output directory if needed
    if not os.path.exists(OUTPUT_JSON_PATH):
        try:
            os.makedirs(OUTPUT_JSON_PATH)
        except OSError as e:
            print(f"Error creating output directory: {e}")
            return

    print("--- Starting Excel -> JSON Conversion ---")
    
    # Iterate over all directories in TSL folder
    for folder_name in sorted(os.listdir(BASE_DATA_PATH)):
        full_path = os.path.join(BASE_DATA_PATH, folder_name)
        if not os.path.isdir(full_path):
            continue
            
        # Skip special folders if any
        if folder_name.startswith("."): continue
        
        # Process this team
        player_data = process_team(folder_name)
        
        if player_data:
            # Create JSON object
            team_json = {
                "teamName": folder_name, # Can also use team name from profile rows if available
                "generatedAt": pd.Timestamp.now().isoformat(),
                "playerCount": len(player_data),
                "players": player_data
            }
            
            # Save to JSON
            out_filename = f"{normalize_filename(folder_name)}.json"
            out_path = os.path.join(OUTPUT_JSON_PATH, out_filename)
            
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(team_json, f, indent=2, ensure_ascii=False)
                
            print(f"✅ Saved {out_filename} ({len(player_data)} players)")

    print("\n--- Conversion Complete ---")

if __name__ == "__main__":
    main()
