import sys
import os
import json
import math
from pathlib import Path

# Dynamic Path Calculation
current_dir = Path(__file__).parent.resolve()
# Go up 2 levels to project root (scripts/simulations -> scripts -> root)
project_root = current_dir.parent.parent
ALGO_DIR = str(project_root / "Data" / "Algorithm" / "PredictaBall")

sys.path.append(ALGO_DIR)

# Import the combined script
try:
    from unittest.mock import patch
    # Patch Path.mkdir during import to avoid "Permission denied" or "FileNotFound" 
    # on hardcoded paths in the script (e.g. //Users/kagancalikoglu/...)
    with patch('pathlib.Path.mkdir'):
        import gol_oncesi_combined_v3 as gol_oncesi_combined

    # Monkeypatch engineer_dataset to impute NaNs (fixes crash in RandomForest)
    original_engineer = gol_oncesi_combined.engineer_dataset
    def patched_engineer_dataset(df):
        out = original_engineer(df)
        return out.fillna(0) # Impute NaNs with 0 to prevent crashes
    gol_oncesi_combined.engineer_dataset = patched_engineer_dataset

    # Import and patch image generation modules to fix hardcoded paths
    import KimKazanır
    import tahmini_skor
    


except ImportError as e:
    print(f"Error importing gol_oncesi_combined_v3: {e}")
    # Attempt fallback if running from root
    try:
        sys.path.append(os.path.abspath("Data/Algorithm/PredictaBall"))
        from unittest.mock import patch
        with patch('pathlib.Path.mkdir'):
            import gol_oncesi_combined_v3 as gol_oncesi_combined
            
            # Monkeypatch logic for fallback
            original_engineer = gol_oncesi_combined.engineer_dataset
            def patched_engineer_dataset(df):
                out = original_engineer(df)
                return out.fillna(0)
            gol_oncesi_combined.engineer_dataset = patched_engineer_dataset
            
            import KimKazanır
            import tahmini_skor
            


    except ImportError:
        raise


def normalize_to_ascii(text):
    import unicodedata
    if not isinstance(text, str):
        return str(text)
    # Normalize to NFD form to decompose characters
    normalized = unicodedata.normalize('NFD', text)
    # Filter out non-spacing mark characters (accents) and encode to ascii
    return "".join(c for c in normalized if unicodedata.category(c) != 'Mn').lower()

def resolve_team_name(base_dir, input_name):
    """
    Attempts to find the matching folder name for 'input_name' in 'base_dir'.
    1. Checks exact match (Unicode NFC normalized).
    2. Checks ASCII fuzzy match (ignoring accents/case).
    Returns the actual folder name on disk if found, else returns input_name.
    """
    import unicodedata
    import os
    
    target_norm = unicodedata.normalize('NFC', input_name).lower()
    
    if not os.path.exists(base_dir):
        return input_name
        
    items = os.listdir(base_dir)
    
    # 1. Exact / NFC match
    for item in items:
        if not os.path.isdir(os.path.join(base_dir, item)):
            continue
            
        item_norm = unicodedata.normalize('NFC', item).lower()
        if item_norm == target_norm:
            return item

    # 2. ASCII Fuzzy match (fallback for Besiktas -> Beşiktaş)
    target_ascii = normalize_to_ascii(input_name)
    for item in items:
        if not os.path.isdir(os.path.join(base_dir, item)):
            continue
        
        item_ascii = normalize_to_ascii(item)
        if item_ascii == target_ascii:
            return item
            
    return input_name

def simulate_match(team1, team2, assets_path, base_data_dir, output_dir, sim_type=None, team1_adj=0, team2_adj=0):
    """
    Runs the combined simulation for team1 vs team2.
    Overrides the output folder to save images to assets_path.
    Returns a dictionary with results and image URLs.
    
    Args:
        team1: Home team name
        team2: Away team name
        assets_path: Path for assets
        base_data_dir: Base data directory
        output_dir: Output directory for images
        sim_type: Simulation type (unused, for compatibility)
        team1_adj: Adjustment percentage for team1 (-10 to +10)
        team2_adj: Adjustment percentage for team2 (-10 to +10)
    """
    print(f"Starting Combined Simulation: {team1} vs {team2}")
    print(f"Adjustments: {team1} = {team1_adj:+.1f}%, {team2} = {team2_adj:+.1f}%")
    
    # Resolve team names to match disk (fixes NFC/NFD issues on Linux)
    # Also handle specific manual mappings where folder name differs significantly from UI name
    # Sofascore uses "FK" and "JK" suffixes that our local folders don't have
    team_mappings = {
        "Fatih Karagümrük": "Karagümrük",
        "Fatih Karagumruk": "Karagümrük",
        "Başakşehir FK": "Başakşehir",
        "Basaksehir FK": "Başakşehir",
        "Beşiktaş JK": "Beşiktaş",
        "Besiktas JK": "Beşiktaş",
        "Gaziantep FK": "Gaziantep"
    }
    
    if team1 in team_mappings:
        team1 = team_mappings[team1]
    if team2 in team_mappings:
        team2 = team_mappings[team2]

    real_team1 = resolve_team_name(base_data_dir, team1)
    real_team2 = resolve_team_name(base_data_dir, team2)
    
    if real_team1 != team1:
        print(f"Resolved Team1 '{team1}' -> '{real_team1}'")
        team1 = real_team1
        
    if real_team2 != team2:
        print(f"Resolved Team2 '{team2}' -> '{real_team2}'")
        team2 = real_team2
    
    # Override paths in the module
    gol_oncesi_combined.OUTPUT_FOLDER = Path(output_dir)
    gol_oncesi_combined.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    gol_oncesi_combined.MAIN_FOLDER = Path(base_data_dir)

    # 1. Performance Patch: Reduce simulation count for server environment
    gol_oncesi_combined.SIMS_PER_COMBO = 50 # Increased to 50 (with 120s timeout) for better consistency

    # 2. Font Patch: Ensure fonts don't crash on Linux
    from PIL import ImageFont
    original_truetype = ImageFont.truetype
    def safe_truetype(font, size=10, index=0, encoding="", layout_engine=None):
        try:
            return original_truetype(font, size, index, encoding, layout_engine)
        except OSError:
            # If specified font fails (e.g. /System/Library/...), fallback to default
            print(f"Font {font} failed, loading default.")
            return ImageFont.load_default()
    ImageFont.truetype = safe_truetype

    # Override paths for KimKazanır (Use new ASCII name)
    KimKazanır.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    KimKazanır.OUTPUT_FOLDER = Path(output_dir)
    KimKazanır.TEMPLATE_PATH = KimKazanır.LOGO_FOLDER / "kim_kazanir.png" 
    
    # Override paths for tahmini_skor
    tahmini_skor.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    tahmini_skor.OUTPUT_FOLDER = Path(output_dir)
    tahmini_skor.TEMPLATE_PATH = tahmini_skor.LOGO_FOLDER / "tahmini_skor.png"
    
    try:
        # 1. Run Markov Models
        print("Running Markov Models...")
        markov_home = gol_oncesi_combined.run_markov_for_team(team1)
        markov_away = gol_oncesi_combined.run_markov_for_team(team2)
        
        # 2. Run Simulations (Home & Away Perspectives) with adjustments
        print("Running Simulations...")
        home_sim = gol_oncesi_combined.run_simulation_perspective(
            team1, team2, 
            team1_adj_pct=team1_adj, 
            team2_adj_pct=team2_adj
        )
        away_sim = gol_oncesi_combined.run_simulation_perspective(
            team2, team1,
            team1_adj_pct=team2_adj,
            team2_adj_pct=team1_adj
        )
        
        # 3. Combine Results
        combined = gol_oncesi_combined.combine_perspectives(home_sim, away_sim)
        
        # 4. Generate Images
        gol_oncesi_combined.generate_images(team1, team2, combined)
        
        # Construct expected filenames based on how KimKazanır and TahminiSkor actually name them
        prob_image_name = f"KimKazanir_{team1}vs{team2}.png" 
        score_image_name = f"{team1}vs{team2}_tahmini_skor.png"
        
        # 5. Structure Output with NaN Sanitization
        def clean_val(x):
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return 0.0
            return x

        win_val = clean_val(gol_oncesi_combined.percent(combined['home_win']))
        draw_val = clean_val(gol_oncesi_combined.percent(combined['draw']))
        lose_val = clean_val(gol_oncesi_combined.percent(combined['home_loss']))
        exp_home = clean_val(combined['exp_home_goals'])
        exp_away = clean_val(combined['exp_away_goals'])
        
        import time
        ts = int(time.time())

        # Extract top 5 scores from home_sim
        top5_list = []
        if 'top5_scores' in home_sim and not home_sim['top5_scores'].empty:
            total_sims = home_sim['top5_scores']['Count'].sum()
            for _, row in home_sim['top5_scores'].iterrows():
                pct = round(100 * row['Count'] / total_sims, 1) if total_sims > 0 else 0
                top5_list.append({
                    "score": row['Score'],
                    "count": int(row['Count']),
                    "percentage": pct
                })

        # Extract Markov form data with full state profiles
        def get_form_label(win_prob):
            if win_prob >= 0.55:
                return "Hot 🔥"
            elif win_prob >= 0.40:
                return "Neutral ⚖️"
            else:
                return "Cold ❄️"

        def get_state_label(state_profile):
            """Assign a descriptive label based on state's win probability."""
            win = state_profile.get('P_win', 0)
            if win >= 0.55:
                return "Peak Form"
            elif win >= 0.45:
                return "Good Form"
            elif win >= 0.35:
                return "Average"
            elif win >= 0.25:
                return "Struggling"
            else:
                return "Crisis"

        def format_state_profiles(profiles):
            """Format state profiles for frontend display."""
            formatted = []
            for profile in profiles:
                formatted.append({
                    "state": profile['state'],
                    "label": get_state_label(profile),
                    "count": profile['count'],
                    "win_prob": round(100 * profile['P_win'], 1),
                    "draw_prob": round(100 * profile['P_draw'], 1),
                    "loss_prob": round(100 * profile['P_loss'], 1)
                })
            return formatted

        markov_data = {
            "team1": {
                "name": team1,
                "next_win_prob": round(100 * markov_home['next_match_probs']['P_win'], 1),
                "next_draw_prob": round(100 * markov_home['next_match_probs']['P_draw'], 1),
                "next_loss_prob": round(100 * markov_home['next_match_probs']['P_loss'], 1),
                "form_label": get_form_label(markov_home['next_match_probs']['P_win']),
                "matches_analyzed": markov_home['matches_used'],
                "hidden_states": markov_home['hidden_states'],
                "state_profiles": format_state_profiles(markov_home['state_profiles'])
            },
            "team2": {
                "name": team2,
                "next_win_prob": round(100 * markov_away['next_match_probs']['P_win'], 1),
                "next_draw_prob": round(100 * markov_away['next_match_probs']['P_draw'], 1),
                "next_loss_prob": round(100 * markov_away['next_match_probs']['P_loss'], 1),
                "form_label": get_form_label(markov_away['next_match_probs']['P_win']),
                "matches_analyzed": markov_away['matches_used'],
                "hidden_states": markov_away['hidden_states'],
                "state_profiles": format_state_profiles(markov_away['state_profiles'])
            }
        }

        # Extract average ratings
        avg_ratings = {
            "team1": round(clean_val(home_sim['avg_ratings']['team1']), 2),
            "team2": round(clean_val(home_sim['avg_ratings']['team2']), 2)
        }

        result = {
            "team1": team1,
            "team2": team2,
            "team1_logo_url": f"/logos/{team1}.png",
            "team2_logo_url": f"/logos/{team2}.png",
            "win_prob": win_val,
            "draw_prob": draw_val,
            "lose_prob": lose_val,
            "predicted_score": combined['headline_score'],
            "exp_home_goals": round(exp_home, 2),
            "exp_away_goals": round(exp_away, 2),
            "prob_image_url": f"/outputs/{prob_image_name}?v={ts}",
            "score_image_url": f"/outputs/{score_image_name}?v={ts}",
            "image_url": f"/outputs/{prob_image_name}?v={ts}", 
            "secondary_image_url": f"/outputs/{score_image_name}?v={ts}",
            # New insights
            "top5_scores": top5_list,
            "markov_form": markov_data,
            "avg_ratings": avg_ratings,
            "simulated_matches": home_sim.get('simulated_matches', 0),
            "adjustments": {
                "team1": team1_adj,
                "team2": team2_adj
            }
        }
        
        return result

    except Exception as e:
        print(f"Error in combined simulation: {e}")
        import traceback
        traceback.print_exc()
        raise e

