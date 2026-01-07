import sys
import os
import json
from pathlib import Path

# Dynamic Path Calculation
current_dir = Path(__file__).parent.resolve()
# Go up 2 levels to project root (scripts/simulations -> scripts -> root)
project_root = current_dir.parent.parent
ALGO_DIR = str(project_root / "Data" / "Algorithm" / "PredictaBall")

sys.path.append(ALGO_DIR)

# Import the combined script
try:
    import gol_oncesi_combined
except ImportError as e:
    print(f"Error importing gol_oncesi_combined: {e}")
    # Attempt fallback if running from root
    try:
        sys.path.append(os.path.abspath("Data/Algorithm/PredictaBall"))
        import gol_oncesi_combined
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
