from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import math
import os
import sys
from pathlib import Path
import unicodedata

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

_PLAYER_ANALYSIS_CACHE = {
    "signature": None,
    "payload": None
}


def _slugify(value):
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("utf-8")
    return normalized.lower().replace(" ", "").replace("-", "")


def _json_safe(value):
    if value is None:
        return None

    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass

    if isinstance(value, float):
        if math.isnan(value):
            return None
        if math.isinf(value):
            return None

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else None

    return value


def _row_to_dict(row_dict):
    return {str(k): _json_safe(v) for k, v in row_dict.items()}


def _discover_player_detail_files():
    sources = []
    if not os.path.exists(BASE_DATA_DIR):
        return sources

    for team_folder in sorted(os.listdir(BASE_DATA_DIR)):
        team_path = os.path.join(BASE_DATA_DIR, team_folder)
        if not os.path.isdir(team_path):
            continue

        players_path = os.path.join(team_path, "Players")
        if not os.path.isdir(players_path):
            continue

        xlsx_files = sorted(
            f for f in os.listdir(players_path)
            if f.endswith(".xlsx") and "PlayerDetail" in f
        )
        if not xlsx_files:
            continue

        # Use the first matching workbook for this team folder.
        sources.append({
            "team_folder": team_folder,
            "file_path": os.path.join(players_path, xlsx_files[0]),
            "file_name": xlsx_files[0]
        })

    return sources


def _load_player_analysis_payload(limit=None, force_refresh=False):
    import pandas as pd

    sources = _discover_player_detail_files()
    if limit:
        sources = sources[:max(limit, 0)]

    signature = []
    for source in sources:
        mtime = os.path.getmtime(source["file_path"])
        signature.append((source["file_path"], mtime))

    signature = tuple(signature)
    if (not force_refresh and
            _PLAYER_ANALYSIS_CACHE["payload"] is not None and
            _PLAYER_ANALYSIS_CACHE["signature"] == signature):
        return _PLAYER_ANALYSIS_CACHE["payload"]

    players = []
    teams = []

    for source in sources:
        file_path = source["file_path"]
        team_folder = source["team_folder"]

        df_profile = pd.read_excel(file_path, sheet_name="Profile")
        df_summary = pd.read_excel(file_path, sheet_name="Season_Summary")
        df_stats = pd.read_excel(file_path, sheet_name="Stats")

        summary_map = {
            _json_safe(row.get("Name")): _row_to_dict(row.to_dict())
            for _, row in df_summary.iterrows()
            if _json_safe(row.get("Name"))
        }
        stats_map = {
            _json_safe(row.get("Name")): _row_to_dict(row.to_dict())
            for _, row in df_stats.iterrows()
            if _json_safe(row.get("Name"))
        }

        team_players = 0
        team_label = None

        for _, row in df_profile.iterrows():
            row_dict = _row_to_dict(row.to_dict())
            name = row_dict.get("Name")
            if not name:
                continue

            team_players += 1
            team_name = row_dict.get("Team") or team_folder
            if team_label is None:
                team_label = team_name

            summary_row = summary_map.get(name, {})
            stats_row = stats_map.get(name, {})

            summary_metrics = {}
            monthly_ratings = {}
            for key, value in summary_row.items():
                if key in ("Name", "HasTournamentStats"):
                    continue
                if key.startswith("AvgRating_"):
                    monthly_key = key.replace("AvgRating_", "")
                    monthly_ratings[monthly_key] = value
                else:
                    summary_metrics[key] = value

            detailed_stats = {
                key: value
                for key, value in stats_row.items()
                if key not in ("Name", "HasTournamentStats")
            }

            players.append({
                "id": f"{_slugify(team_name)}_{_slugify(name)}",
                "name": name,
                "team": team_name,
                "teamFolder": team_folder,
                "profile": {
                    key: value for key, value in row_dict.items() if key != "Name"
                },
                "seasonSummary": {
                    "hasTournamentStats": summary_row.get("HasTournamentStats"),
                    "metrics": summary_metrics,
                    "monthlyRatings": monthly_ratings
                },
                "detailedStats": {
                    "hasTournamentStats": stats_row.get("HasTournamentStats"),
                    "metrics": detailed_stats
                }
            })

        teams.append({
            "id": _slugify(team_folder),
            "name": team_label or team_folder,
            "folder": team_folder,
            "playerCount": team_players,
            "fileName": source["file_name"]
        })

    players.sort(key=lambda p: (p["team"], p["name"]))

    payload = {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "teamCount": len(teams),
        "playerCount": len(players),
        "sourceCount": len(sources),
        "teams": teams,
        "players": players
    }

    _PLAYER_ANALYSIS_CACHE["signature"] = signature
    _PLAYER_ANALYSIS_CACHE["payload"] = payload
    return payload

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
        team1_formation = data.get('team1_formation')
        team2_formation = data.get('team2_formation')
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
            team2_adj,
            team1_formation=team1_formation,
            team2_formation=team2_formation
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


@app.route('/api/player-analysis', methods=['GET'])
def get_player_analysis():
    """Return merged player data from PlayerDetail Excel files."""
    try:
        limit = request.args.get('limit', type=int)
        refresh = request.args.get('refresh', '0') == '1'
        payload = _load_player_analysis_payload(limit=limit, force_refresh=refresh)
        return jsonify(payload)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/logos/<path:filename>')
def serve_logo(filename):
    logo_dir = os.path.join(ASSETS_DIR, "Logos")
    return send_from_directory(logo_dir, filename)

@app.route('/Data/<path:filepath>')
def serve_data_files(filepath):
    """Serve CSV and other data files from the Data directory."""
    data_dir = os.path.join(BASE_DIR, "Data")
    return send_from_directory(data_dir, filepath)

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
