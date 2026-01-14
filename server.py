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

@app.route('/logos/<path:filename>')
def serve_logo(filename):
    logo_dir = os.path.join(ASSETS_DIR, "Logos")
    return send_from_directory(logo_dir, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"Starting Flask Backend on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
