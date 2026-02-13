#!/usr/bin/env python3
"""
Weekly Predictions Generator for Turkish Super League
Runs simulations for all matches in an upcoming round and saves predictions
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add project paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.append(os.path.join(PROJECT_ROOT, 'scripts', 'simulations'))

# Import simulation adapter
import combined_adapter

# Paths
BASE_DATA_DIR = os.path.join(PROJECT_ROOT, "Data", "Turkish Super League")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "Data", "Algorithm", "PredictaBall")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
SCHEDULE_FILE = os.path.join(PROJECT_ROOT, "Data", "schedule", "season_schedule.json")
PREDICTIONS_DIR = os.path.join(PROJECT_ROOT, "Data", "predictions")

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(PREDICTIONS_DIR, exist_ok=True)


def calculate_confidence(home_win, draw, away_win):
    """
    Calculate prediction confidence based on probability distribution
    
    Args:
        home_win: Home win probability (%)
        draw: Draw probability (%)
        away_win: Away win probability (%)
    
    Returns:
        str: Confidence level ('high', 'medium', or 'low')
    """
    max_prob = max(home_win, draw, away_win)
    spread = max_prob - min(home_win, draw, away_win)
    
    # High confidence: Clear favorite (>60%) with large spread (>40%)
    if max_prob >= 60 and spread >= 40:
        return "high"
    # Medium confidence: Moderate favorite (>45%) or decent spread (>25%)
    elif max_prob >= 45 or spread >= 25:
        return "medium"
    # Low confidence: Close probabilities
    else:
        return "low"


def normalize_team_name(team_name):
    """
    Normalize team names from Sofascore to match local folder names
    
    Args:
        team_name: Team name from Sofascore API
    
    Returns:
        str: Normalized team name
    """
    # Sofascore uses "FK" and "JK" suffixes that our local folders don't have
    team_mappings = {
        "Fatih Karagümrük": "Karagümrük",
        "Başakşehir FK": "Başakşehir",
        "Beşiktaş JK": "Beşiktaş",
        "Gaziantep FK": "Gaziantep"
    }
    
    return team_mappings.get(team_name, team_name)


def get_predicted_score(score_distribution):
    """
    Extract the most likely score from the distribution
    
    Args:
        score_distribution: List of score tuples with probabilities
    
    Returns:
        str: Predicted score like "2-1"
    """
    if not score_distribution:
        return "0-0"
    
    # Sort by probability
    sorted_scores = sorted(score_distribution, key=lambda x: x[2], reverse=True)
    
    # Get most likely score
    home_goals, away_goals, _ = sorted_scores[0]
    
    return f"{home_goals}-{away_goals}"


def load_schedule():
    """Load the season schedule from JSON"""
    if not os.path.exists(SCHEDULE_FILE):
        raise FileNotFoundError(
            f"Schedule file not found at {SCHEDULE_FILE}. "
            "Run scripts/schedule_scraper.py first."
        )
    
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_round_predictions(round_number, team1_adj=0, team2_adj=0):
    """
    Generate predictions for all matches in a round
    
    Args:
        round_number: Round number (1-34)
        team1_adj: Default adjustment for team 1 (default: 0)
        team2_adj: Default adjustment for team 2 (default: 0)
    
    Returns:
        dict: Predictions data for the round
    """
    print(f"\n{'='*70}")
    print(f"  GENERATING PREDICTIONS FOR ROUND {round_number}")
    print(f"{'='*70}\n")
    
    # Load schedule
    schedule = load_schedule()
    
    # Find the requested round
    round_data = next(
        (r for r in schedule['rounds'] if r['round'] == round_number),
        None
    )
    
    if not round_data:
        raise ValueError(f"Round {round_number} not found in schedule")
    
    matches = round_data['matches']
    predictions = {
        'round': round_number,
        'generated_at': datetime.now().isoformat(),
        'matches': []
    }
    
    print(f"Found {len(matches)} matches in Round {round_number}\n")
    
    for idx, match in enumerate(matches, 1):
        home_team = match['home_team']
        away_team = match['away_team']
        match_id = match['match_id']
        
        # Normalize team names to match local folder structure
        home_team_normalized = normalize_team_name(home_team)
        away_team_normalized = normalize_team_name(away_team)
        
        print(f"[{idx}/{len(matches)}] {home_team} vs {away_team}")
        if home_team != home_team_normalized or away_team != away_team_normalized:
            print(f"  Normalized: {home_team_normalized} vs {away_team_normalized}")
        print(f"  Match ID: {match_id}")
        print(f"  Date/Time: {match['date']} {match['time']}")
        
        try:
            # Run simulation with normalized team names
            sim_results = combined_adapter.simulate_match(
                home_team_normalized,
                away_team_normalized,
                ASSETS_DIR,
                BASE_DATA_DIR,
                OUTPUT_DIR,
                sim_type='combined',  # Use combined simulation
                team1_adj=team1_adj,
                team2_adj=team2_adj
            )
            
            # Extract probabilities - fix field names to match combined_adapter output
            home_win_pct = sim_results.get('win_prob', 0)  # Changed from 'win_probability_home'
            draw_pct = sim_results.get('draw_prob', 0)     # Changed from 'draw_probability'
            away_win_pct = sim_results.get('lose_prob', 0)  # Changed from 'win_probability_away' (it's lose from home perspective)
            
            # Calculate confidence
            confidence = calculate_confidence(home_win_pct, draw_pct, away_win_pct)
            
            # Get predicted score - use the headline score from combined results
            predicted_score = sim_results.get('predicted_score', '0-0')
            
            # Get expected goals
            expected_goals_home = sim_results.get('exp_home_goals', 0)
            expected_goals_away = sim_results.get('exp_away_goals', 0)
            
            # Get score distribution from top5_scores
            score_dist = []
            top5_scores = sim_results.get('top5_scores', [])
            for score_data in top5_scores:
                # Parse score string like "2-1"
                score_str = score_data.get('score', '0-0')
                if '-' in score_str:
                    home_goals_str, away_goals_str = score_str.split('-')
                    score_dist.append(
                        (int(home_goals_str), int(away_goals_str), score_data.get('percentage', 0))
                    )
            
            # Prepare prediction data
            prediction = {
                'match_id': match_id,
                'date': match['date'],
                'time': match['time'],
                'datetime_iso': match['datetime_iso'],
                'home_team': home_team,
                'away_team': away_team,
                'predicted_score': predicted_score,
                'probabilities': {
                    'home_win': round(home_win_pct, 1),
                    'draw': round(draw_pct, 1),
                    'away_win': round(away_win_pct, 1)
                },
                'confidence': confidence,
                'expected_goals': {
                    'home': round(expected_goals_home, 2),
                    'away': round(expected_goals_away, 2)
                },
                'score_distribution': score_dist,
                'heatmap_data': sim_results.get('heatmap_data', []),
                'heatmaps': sim_results.get('heatmaps', {}),
                'player_heatmap_url': sim_results.get('player_heatmap_url'),
                'main_cluster_heatmap_url': sim_results.get('main_cluster_heatmap_url'),
                'strip_cluster_heatmap_url': sim_results.get('strip_cluster_heatmap_url'),
                # Pass through advanced fields for expanded UI
                'top5_scores': top5_scores,
                'markov_form': sim_results.get('markov_form'),
                'avg_ratings': sim_results.get('avg_ratings'),
                'team1_logo_url': sim_results.get('team1_logo_url'),
                'team2_logo_url': sim_results.get('team2_logo_url')
            }
            
            predictions['matches'].append(prediction)
            
            # Print results
            confidence_emoji = {
                'high': '🟢',
                'medium': '🟡',
                'low': '🔴'
            }
            print(f"  ✓ Prediction: {predicted_score}")
            print(f"    Probabilities: Home {home_win_pct:.1f}% | Draw {draw_pct:.1f}% | Away {away_win_pct:.1f}%")
            print(f"    Confidence: {confidence_emoji.get(confidence, '')} {confidence.upper()}")
            print(f"    Expected Goals: {expected_goals_home:.2f} - {expected_goals_away:.2f}\n")
        
        except Exception as e:
            print(f"  ✗ Error running simulation: {e}\n")
            import traceback
            traceback.print_exc()
            continue
    
    return predictions


def save_predictions(predictions):
    """Save predictions to JSON file"""
    round_num = predictions['round']
    output_file = os.path.join(PREDICTIONS_DIR, f"round_{round_num:02d}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(predictions, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*70}")
    print(f"✓ Predictions saved to: {output_file}")
    print(f"  Round: {round_num}")
    print(f"  Matches predicted: {len(predictions['matches'])}")
    print(f"  Generated at: {predictions['generated_at']}")
    print(f"{'='*70}\n")
    
    return output_file


def main():
    parser = argparse.ArgumentParser(
        description='Generate match predictions for a Turkish Super League round'
    )
    parser.add_argument(
        '--round',
        type=int,
        required=True,
        help='Round number to generate predictions for (1-34)'
    )
    parser.add_argument(
        '--team1-adj',
        type=float,
        default=0.0,
        help='Default adjustment percentage for home teams (default: 0)'
    )
    parser.add_argument(
        '--team2-adj',
        type=float,
        default=0.0,
        help='Default adjustment percentage for away teams (default: 0)'
    )
    
    args = parser.parse_args()
    
    # Validate round number
    if not 1 <= args.round <= 34:
        print(f"Error: Round must be between 1 and 34 (got {args.round})")
        sys.exit(1)
    
    # Generate predictions
    try:
        predictions = generate_round_predictions(
            args.round,
            team1_adj=args.team1_adj,
            team2_adj=args.team2_adj
        )
        
        # Save to file
        save_predictions(predictions)
        
        print("Success! Predictions are ready to be used by the web app.")
        print("\nNext steps:")
        print("1. Review the generated JSON file")
        print("2. Commit and push to GitHub to deploy")
        print(f"3. The 'Recent Games' tab will display these predictions for Round {args.round}")
    
    except Exception as e:
        print(f"\nError generating predictions: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
