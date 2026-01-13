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

def simulate_match(team1, team2, assets_path, base_data_dir, output_dir, sim_type=None):
    """
    Runs the combined simulation for team1 vs team2.
    Overrides the output folder to save images to assets_path.
    Returns a dictionary with results and image URLs.
    """
    print(f"Starting Combined Simulation: {team1} vs {team2}")
    
    # Override paths in the module
    gol_oncesi_combined.OUTPUT_FOLDER = Path(assets_path)
    gol_oncesi_combined.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    gol_oncesi_combined.MAIN_FOLDER = Path(base_data_dir)

    # Override paths for KimKazanır
    KimKazanır.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    KimKazanır.OUTPUT_FOLDER = Path(assets_path)
    KimKazanır.TEMPLATE_PATH = KimKazanır.LOGO_FOLDER / "kim_kazanır.png"
    
    # Override paths for tahmini_skor
    tahmini_skor.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    tahmini_skor.OUTPUT_FOLDER = Path(assets_path)
    tahmini_skor.TEMPLATE_PATH = tahmini_skor.LOGO_FOLDER / "tahmini_skor.png"
    
    try:
        # 1. Run Markov Models
        print("Running Markov Models...")
        markov_home = gol_oncesi_combined.run_markov_for_team(team1)
        markov_away = gol_oncesi_combined.run_markov_for_team(team2)
        
        # 2. Run Simulations (Home & Away Perspectives)
        print("Running Simulations...")
        home_sim = gol_oncesi_combined.run_simulation_perspective(team1, team2)
        away_sim = gol_oncesi_combined.run_simulation_perspective(team2, team1)
        
        # 3. Combine Results
        combined = gol_oncesi_combined.combine_perspectives(home_sim, away_sim)
        
        # 4. Generate Images
        # The script generates two images:
        # - Probability image (KimKazanır) -> saved as "KimKazanır_{Team1}_{Team2}.png" usually?
        # - Score image (TahminiSkor) -> saved as "TahminiSkor_{Team1}_{Team2}.png"?
        # Let's check generate_images implementation details via the module if possible, 
        # but for now we assume it uses standard naming in the OUTPUT_FOLDER.
        
        gol_oncesi_combined.generate_images(team1, team2, combined)
        
        # Construct expected filenames based on how KimKazanır and TahminiSkor usually name them
        # Note: We might need to verify the exact naming convention in those modules.
        # usually: f"KimKazanır_{home_team}_{away_team}.png"
        prob_image_name = f"KimKazanır_{team1}_{team2}.png"
        score_image_name = f"TahminiSkor_{team1}_{team2}.png"
        
        # 5. Structure Output

        # Helper to clean NaNs
        def clean_val(x):
            if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
                return 0.0
            return x

        win_val = clean_val(gol_oncesi_combined.percent(combined['home_win']))
        draw_val = clean_val(gol_oncesi_combined.percent(combined['draw']))
        lose_val = clean_val(gol_oncesi_combined.percent(combined['home_loss']))
        exp_home = clean_val(combined['exp_home_goals'])
        exp_away = clean_val(combined['exp_away_goals'])

        result = {
            "team1": team1,
            "team2": team2,
            "win_prob": win_val,
            "draw_prob": draw_val,
            "lose_prob": lose_val,
            "predicted_score": combined['headline_score'],
            "exp_home_goals": round(exp_home, 2),
            "exp_away_goals": round(exp_away, 2),
            "prob_image_url": f"/static/assets/{prob_image_name}",
            "score_image_url": f"/static/assets/{score_image_name}",
            # Pass both images to frontend? For now server usually returns `image_url`. 
            # We can return `images` array or deciding which one to show. 
            # The prompt implies showing "the result", likely the comprehensive one. 
            # Let's return both URLs.
            "image_url": f"/static/assets/{prob_image_name}", # Default to Probability one for now
            "secondary_image_url": f"/static/assets/{score_image_name}"
        }
        
        return result

    except Exception as e:
        print(f"Error in combined simulation: {e}")
        import traceback
        traceback.print_exc()
        raise e

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

def simulate_match(team1, team2, assets_path, base_data_dir, output_dir, sim_type=None):
    """
    Runs the combined simulation for team1 vs team2.
    Overrides the output folder to save images to assets_path.
    Returns a dictionary with results and image URLs.
    """
    print(f"Starting Combined Simulation (patched): {team1} vs {team2}")
    
    # Resolve team names to match disk (fixes NFC/NFD issues on Linux)
    real_team1 = resolve_team_name(base_data_dir, team1)
    real_team2 = resolve_team_name(base_data_dir, team2)
    
    if real_team1 != team1:
        print(f"Resolved Team1 '{team1}' -> '{real_team1}'")
        team1 = real_team1
        
    if real_team2 != team2:
        print(f"Resolved Team2 '{team2}' -> '{real_team2}'")
        team2 = real_team2
    
    # Override paths in the module
    gol_oncesi_combined.OUTPUT_FOLDER = Path(assets_path)
    gol_oncesi_combined.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    gol_oncesi_combined.MAIN_FOLDER = Path(base_data_dir)

    # 1. Performance Patch: Reduce simulation count for server environment
    gol_oncesi_combined.SIMS_PER_COMBO = 50 # Default was 200, reduce to avoid Timeout/OOM

    # 2. Font Patch: Ensure fonts don't crash on Linux
    # Check if we are on Linux (Render) and patch ImageFont if necessary
    # Or just robustly patch it always? 
    # Let's monkeypatch PIL.ImageFont.truetype to fallback gracefully if path is absolute and missing
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
    KimKazanır.OUTPUT_FOLDER = Path(assets_path)
    KimKazanır.TEMPLATE_PATH = KimKazanır.LOGO_FOLDER / "kim_kazanir.png" 
    
    # Override paths for tahmini_skor
    tahmini_skor.LOGO_FOLDER = Path(ALGO_DIR) / "Logos"
    tahmini_skor.OUTPUT_FOLDER = Path(assets_path)
    tahmini_skor.TEMPLATE_PATH = tahmini_skor.LOGO_FOLDER / "tahmini_skor.png"
    
    try:
        # 1. Run Markov Models
        print("Running Markov Models...")
        markov_home = gol_oncesi_combined.run_markov_for_team(team1)
        markov_away = gol_oncesi_combined.run_markov_for_team(team2)
        
        # 2. Run Simulations (Home & Away Perspectives)
        print("Running Simulations...")
        home_sim = gol_oncesi_combined.run_simulation_perspective(team1, team2)
        away_sim = gol_oncesi_combined.run_simulation_perspective(team2, team1)
        
        # 3. Combine Results
        combined = gol_oncesi_combined.combine_perspectives(home_sim, away_sim)
        
        # 4. Generate Images
        gol_oncesi_combined.generate_images(team1, team2, combined)
        
        # Construct expected filenames based on how KimKazanır and TahminiSkor actually name them
        # KimKazanır.py: out_name = f"KimKazanir_{home_team}vs{away_team}.png"
        # tahmini_skor.py: post_name = f"{first_team_name}vs{second_team_name}_tahmini_skor.png"
        
        prob_image_name = f"KimKazanir_{team1}vs{team2}.png" 
        score_image_name = f"{team1}vs{team2}_tahmini_skor.png"
        
        # 5. Structure Output
        result = {
            "team1": team1,
            "team2": team2,
            "win_prob": gol_oncesi_combined.percent(combined['home_win']),
            "draw_prob": gol_oncesi_combined.percent(combined['draw']),
            "lose_prob": gol_oncesi_combined.percent(combined['home_loss']),
            "predicted_score": combined['headline_score'],
            "exp_home_goals": round(combined['exp_home_goals'], 2),
            "exp_away_goals": round(combined['exp_away_goals'], 2),
            "prob_image_url": f"/static/assets/{prob_image_name}",
            "score_image_url": f"/static/assets/{score_image_name}",
            "image_url": f"/static/assets/{prob_image_name}", 
            "secondary_image_url": f"/static/assets/{score_image_name}"
        }
        
        return result

    except Exception as e:
        print(f"Error in combined simulation: {e}")
        import traceback
        traceback.print_exc()
        raise e
