from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
from pathlib import Path

# Dynamic Base Path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Add scripts/simulations to python path
sys.path.append(os.path.join(BASE_DIR, 'scripts', 'simulations'))

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app)

# Dynamic Paths for Data
BASE_DATA_DIR = os.path.join(BASE_DIR, "Data", "Turkish Super League")
ASSETS_DIR = os.path.join(BASE_DIR, "Data", "Algorithm", "PredictaBall")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

# Ensure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

@app.route('/')
def serve_index():
    return send_from_directory('public', 'index.html')

@app.route('/api/simulate', methods=['POST'])
def run_simulation():
    try:
        data = request.json
        team1 = data.get('team1')
        team2 = data.get('team2')
        sim_type = data.get('type')
        team1_adj = data.get('team1_adj', 0)
        team2_adj = data.get('team2_adj', 0)

        if not team1 or not team2:
            return jsonify({"error": "Missing teams"}), 400

        results = {}
        
        # Import combined adapter (it should be found via sys.path)
        import combined_adapter
    
        # Run the Combined Simulation
        results = combined_adapter.simulate_match(
            team1, 
            team2, 
            ASSETS_DIR, 
            BASE_DATA_DIR,
            OUTPUT_DIR,
            sim_type,
            team1_adj,
            team2_adj
        )
        
        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/outputs/<path:filename>')
def serve_output(filename):
    return send_from_directory(OUTPUT_DIR, filename)

@app.route('/api/players', methods=['GET'])
def get_players():
    """Get all players for a specific team."""
    try:
        import json
        
        team = request.args.get('team')
        if not team:
            return jsonify({"error": "Team parameter required"}), 400
        
        # Read players data
        players_file = os.path.join(BASE_DIR, 'public', 'players_data.js')
        if not os.path.exists(players_file):
            return jsonify({"error": "Player data not found. Run process_players.py first."}), 404
        
        # Parse the JS file to extract JSON data
        with open(players_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract JSON from "const playersData = {...};"
            start = content.find('{')
            end = content.rfind('}', 0, content.find('// Get all team names')) + 1
            players_data = json.loads(content[start:end])
        
        if team not in players_data:
            return jsonify({"error": f"Team '{team}' not found"}), 404
        
        return jsonify({"team": team, "players": players_data[team]})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/player/<int:player_id>', methods=['GET'])
def get_player(player_id):
    """Get detailed stats for a specific player."""
    try:
        import json
        
        # Read players data
        players_file = os.path.join(BASE_DIR, 'public', 'players_data.js')
        if not os.path.exists(players_file):
            return jsonify({"error": "Player data not found. Run process_players.py first."}), 404
        
        # Parse the JS file to extract JSON data
        with open(players_file, 'r', encoding='utf-8') as f:
            content = f.read()
            start = content.find('{')
            end = content.rfind('}', 0, content.find('// Get all team names')) + 1
            players_data = json.loads(content[start:end])
        
        # Search for player by ID across all teams
        for team, players in players_data.items():
            for player in players:
                if player['id'] == player_id:
                    return jsonify(player)
        
        return jsonify({"error": f"Player with ID {player_id} not found"}), 404
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/logos/<path:filename>')
def serve_logo(filename):
    logo_dir = os.path.join(ASSETS_DIR, "Logos")
    return send_from_directory(logo_dir, filename)

@app.route('/api/current-round', methods=['GET'])
def get_current_round():
    """Get the current round number based on today's date."""
    try:
        import json
        from datetime import datetime
        
        schedule_file = os.path.join(BASE_DIR, 'Data', 'schedule', 'season_schedule.json')
        
        if not os.path.exists(schedule_file):
            return jsonify({"error": "Schedule not found"}), 404
        
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
        
        # Use current_round from schedule if available
        if 'current_round' in schedule:
            return jsonify({
                "current_round": schedule['current_round'],
                "season": schedule.get('season', '2024-25')
            })
        
        # Fallback: find round based on today's date
        today = datetime.now()
        
        for round_data in schedule.get('rounds', []):
            for match in round_data.get('matches', []):
                match_date_str = match.get('date')
                if match_date_str:
                    match_date = datetime.fromisoformat(match_date_str.replace('Z', '+00:00'))
                    # If match is in the future, this is likely the current round
                    if match_date >= today:
                        return jsonify({
                            "current_round": round_data['round'],
                            "season": schedule.get('season', '2024-25')
                        })
        
        # Default to round 1 if can't determine
        return jsonify({"current_round": 1, "season": schedule.get('season', '2024-25')})
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/recent-games', methods=['GET'])
def get_recent_games():
    """Get predictions and results for a specific round."""
    try:
        import json
        
        # Get round number from query params (default to current round)
        round_num = request.args.get('round', type=int)
        
        # Load schedule
        schedule_file = os.path.join(BASE_DIR, 'Data', 'schedule', 'season_schedule.json')
        if not os.path.exists(schedule_file):
            return jsonify({"error": "Schedule not found"}), 404
        
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
        
        # If no round specified, use current round
        if round_num is None:
            round_num = schedule.get('current_round', 19)
        
        # Find the round in schedule
        round_data = None
        for r in schedule.get('rounds', []):
            if r['round'] == round_num:
                round_data = r
                break
        
        if not round_data:
            return jsonify({"error": f"Round {round_num} not found"}), 404
        
        # Load predictions if available
        predictions_file = os.path.join(BASE_DIR, 'Data', 'predictions', f'round_{round_num:02d}.json')
        
        # Try sample file if main predictions don't exist (for development)
        if not os.path.exists(predictions_file):
            predictions_file = os.path.join(BASE_DIR, 'Data', 'predictions', f'round_{round_num:02d}_sample.json')
        
        predictions_data = None
        if os.path.exists(predictions_file):
            with open(predictions_file, 'r', encoding='utf-8') as f:
                predictions_data = json.load(f)
        
        # Import combined_adapter to get enriched match analysis
        import combined_adapter
        
        # Merge schedule matches with predictions
        matches = []
        for match in round_data.get('matches', []):
            match_info = {
                "match_id": match['match_id'],
                "date": match['date'],
                "time": match['time'],
                "datetime_iso": match.get('datetime_iso'),
                "home_team": match['home_team'],
                "away_team": match['away_team'],
                "status": match['status'],
                "actual_score": match.get('actual_score')
            }
            
            # Add prediction data if available
            if predictions_data:
                pred_match = next(
                    (p for p in predictions_data.get('matches', []) 
                     if p['match_id'] == match['match_id']),
                    None
                )
                if pred_match:
                    # Map prediction data directly from JSON
                    # These fields are pre-populated by weekly_predictions.py
                    match_info['prediction'] = {
                        "predicted_score": pred_match.get('predicted_score'),
                        "probabilities": pred_match.get('probabilities'),
                        "confidence": pred_match.get('confidence'),
                        "expected_goals": pred_match.get('expected_goals'),
                        "score_distribution": pred_match.get('score_distribution', []),
                        "heatmap_data": pred_match.get('heatmap_data', []),
                        "top5_scores": pred_match.get('top5_scores', []),
                        "markov_form": pred_match.get('markov_form'),
                        "avg_ratings": pred_match.get('avg_ratings'),
                        "team1_logo_url": pred_match.get('team1_logo_url'),
                        "team2_logo_url": pred_match.get('team2_logo_url')
                    }
                    
                    # Backwards compatibility for score distribution
                    if not match_info['prediction']['top5_scores'] and pred_match.get('score_distribution'):
                        top5_scores = []
                        for score_data in pred_match['score_distribution'][:5]:
                            if len(score_data) >= 3:
                                top5_scores.append({
                                    "score": f"{int(score_data[0])}-{int(score_data[1])}",
                                    "percentage": round(score_data[2], 1)
                                })
                        match_info['prediction']['top5_scores'] = top5_scores
            
            matches.append(match_info)
        
        result = {
            "round": round_num,
            "season": schedule.get('season', '2024-25'),
            "current_round": schedule.get('current_round'),
            "matches": matches,
            "predictions_available": predictions_data is not None,
            "generated_at": predictions_data.get('generated_at') if predictions_data else None
        }
        
        return jsonify(result)
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting Flask Backend on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
