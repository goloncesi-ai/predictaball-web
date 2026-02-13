import importlib
import math
import os
import sys
import unicodedata
from pathlib import Path

import pandas as pd


# Path setup
CURRENT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = CURRENT_DIR.parent.parent
ALGO_DIR = PROJECT_ROOT / "Data" / "Algorithm" / "PredictaBall"
ENGINE_ROOT = ALGO_DIR / "Gol_Oncesi_Engine"

for p in (str(ALGO_DIR), str(ENGINE_ROOT)):
    if p not in sys.path:
        sys.path.append(p)

from gol_oncesi_engine import GolOncesiEngine, MatchConfig, PathsConfig, SimulationConfig
from gol_oncesi_engine.formations import parse_formation
from gol_oncesi_engine.hmm_trend import run_markov_drop_recent


TEAM_MAPPINGS = {
    "Fatih Karagumruk": "Karagümrük",
    "Fatih Karagümrük": "Karagümrük",
    "Basaksehir FK": "Başakşehir",
    "Başakşehir FK": "Başakşehir",
    "Besiktas JK": "Beşiktaş",
    "Beşiktaş JK": "Beşiktaş",
    "Gaziantep FK": "Gaziantep",
}

_ENGINE_CACHE = {}
_FORMATION_CACHE = {}


def normalize_to_ascii(text):
    if not isinstance(text, str):
        return str(text)
    normalized = unicodedata.normalize("NFD", text)
    return "".join(c for c in normalized if unicodedata.category(c) != "Mn").lower()


def resolve_team_name(base_dir, input_name):
    target_norm = unicodedata.normalize("NFC", input_name).lower()
    if not os.path.exists(base_dir):
        return input_name

    items = os.listdir(base_dir)

    for item in items:
        if not os.path.isdir(os.path.join(base_dir, item)):
            continue
        item_norm = unicodedata.normalize("NFC", item).lower()
        if item_norm == target_norm:
            return item

    target_ascii = normalize_to_ascii(input_name)
    for item in items:
        if not os.path.isdir(os.path.join(base_dir, item)):
            continue
        if normalize_to_ascii(item) == target_ascii:
            return item

    return input_name


def percent(x):
    return round(100.0 * float(x), 1)


def clean_val(x):
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return 0.0
    return x


def get_form_label(win_prob):
    if win_prob >= 0.55:
        return "Hot 🔥"
    if win_prob >= 0.40:
        return "Neutral ⚖️"
    return "Cold ❄️"


def _resolve_team_for_disk(base_data_dir, team_name):
    mapped = TEAM_MAPPINGS.get(team_name, team_name)
    return resolve_team_name(base_data_dir, mapped)


def _detect_team_formation(base_data_dir, team_name):
    cache_key = (str(base_data_dir), team_name)
    if cache_key in _FORMATION_CACHE:
        return _FORMATION_CACHE[cache_key]

    f = Path(base_data_dir) / team_name / "mixed-seasons" / f"{team_name}_Games_Input.xlsx"
    formation = "4-2-3-1"

    try:
        if f.exists():
            df = pd.read_excel(f)
            if "Team1Formation" in df.columns:
                mode = df["Team1Formation"].dropna().astype(str).value_counts()
                if not mode.empty:
                    formation = mode.index[0]
    except Exception:
        formation = "4-2-3-1"

    parsed = parse_formation(formation)
    _FORMATION_CACHE[cache_key] = parsed
    return parsed


def _get_engine(base_data_dir, output_dir, logo_dir):
    key = (str(base_data_dir), str(output_dir), str(logo_dir))
    if key in _ENGINE_CACHE:
        return _ENGINE_CACHE[key]

    paths = PathsConfig(
        main_folder=Path(base_data_dir),
        output_folder=Path(output_dir),
        logo_folder=Path(logo_dir),
    )
    cfg = SimulationConfig(
        n_sims_home_perspective=50,
        n_sims_away_perspective=50,
    )
    engine = GolOncesiEngine(paths, cfg, verbose=False)
    _ENGINE_CACHE[key] = engine
    return engine


def _configure_image_modules(output_dir, logo_dir):
    try:
        kimkazanir = importlib.import_module("KimKazan\u0131r")
        tahmini_skor = importlib.import_module("tahmini_skor")

        kimkazanir.LOGO_FOLDER = Path(logo_dir)
        kimkazanir.OUTPUT_FOLDER = Path(output_dir)
        kimkazanir.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        kimkazanir.TEMPLATE_PATH = Path(logo_dir) / "kim_kazanir.png"

        tahmini_skor.LOGO_FOLDER = Path(logo_dir)
        tahmini_skor.OUTPUT_FOLDER = Path(output_dir)
        tahmini_skor.OUTPUT_FOLDER.mkdir(parents=True, exist_ok=True)
        tahmini_skor.TEMPLATE_PATH = Path(logo_dir) / "tahmini_skor.png"
        return True
    except Exception as e:
        print(f"Image module setup failed: {e}")
        return False


def _build_markov_form(base_data_dir, team1, team2, random_state):
    try:
        m1 = run_markov_drop_recent(Path(base_data_dir), team1, drop_recent=0, random_state=random_state)
        m2 = run_markov_drop_recent(Path(base_data_dir), team2, drop_recent=0, random_state=random_state)

        return {
            "team1": {
                "name": team1,
                "next_win_prob": round(100 * m1["P_win"], 1),
                "next_draw_prob": round(100 * m1["P_draw"], 1),
                "next_loss_prob": round(100 * m1["P_loss"], 1),
                "form_label": get_form_label(m1["P_win"]),
                "matches_analyzed": int(m1.get("matches_used", 0)),
                "hidden_states": 0,
                "state_profiles": [],
            },
            "team2": {
                "name": team2,
                "next_win_prob": round(100 * m2["P_win"], 1),
                "next_draw_prob": round(100 * m2["P_draw"], 1),
                "next_loss_prob": round(100 * m2["P_loss"], 1),
                "form_label": get_form_label(m2["P_win"]),
                "matches_analyzed": int(m2.get("matches_used", 0)),
                "hidden_states": 0,
                "state_profiles": [],
            },
        }
    except Exception as e:
        print(f"Markov form generation failed: {e}")
        return None


def _build_top5_scores(top5_df):
    top5_list = []
    if top5_df is None or top5_df.empty:
        return top5_list

    total_sims = int(top5_df["Count"].sum()) if "Count" in top5_df.columns else 0
    for _, row in top5_df.iterrows():
        score = str(row.get("Score", "0-0"))
        count = int(row.get("Count", 0))
        pct = round((100.0 * count / total_sims), 1) if total_sims > 0 else 0.0
        top5_list.append({
            "score": score,
            "count": count,
            "percentage": pct,
        })
    return top5_list


def simulate_match(
    team1,
    team2,
    assets_path,
    base_data_dir,
    output_dir,
    sim_type=None,
    team1_adj=0,
    team2_adj=0,
    team1_formation=None,
    team2_formation=None,
):
    print(f"Starting Combined Simulation (new engine): {team1} vs {team2}")
    print(f"Adjustments: {team1}={team1_adj:+.1f}%, {team2}={team2_adj:+.1f}%")

    team1_resolved = _resolve_team_for_disk(base_data_dir, team1)
    team2_resolved = _resolve_team_for_disk(base_data_dir, team2)
    if team1_resolved != team1:
        print(f"Resolved Team1 '{team1}' -> '{team1_resolved}'")
    if team2_resolved != team2:
        print(f"Resolved Team2 '{team2}' -> '{team2_resolved}'")

    home_form = parse_formation(team1_formation) if team1_formation else _detect_team_formation(base_data_dir, team1_resolved)
    away_form = parse_formation(team2_formation) if team2_formation else _detect_team_formation(base_data_dir, team2_resolved)

    logo_dir = Path(assets_path) / "Logos"
    engine = _get_engine(base_data_dir, output_dir, logo_dir)

    can_generate_images = _configure_image_modules(output_dir, logo_dir)

    match_cfg = MatchConfig(
        home_team=team1_resolved,
        away_team=team2_resolved,
        home_formation=home_form,
        away_formation=away_form,
        home_adj_pct=float(team1_adj),
        away_adj_pct=float(team2_adj),
    )

    result = engine.run_match(
        match_cfg,
        draw_heatmaps=False,
        generate_images=can_generate_images,
    )

    combined = result.combined
    top5_list = _build_top5_scores(result.home_sim.top5_scores)
    markov_data = _build_markov_form(base_data_dir, team1_resolved, team2_resolved, engine.cfg.random_seed)

    avg_ratings = {
        "team1": round(clean_val(result.home_sim.avg_team_ratings.get("team1", 0.0)), 2),
        "team2": round(clean_val(result.home_sim.avg_team_ratings.get("team2", 0.0)), 2),
    }

    prob_image_name = f"KimKazanir_{team1_resolved}vs{team2_resolved}.png"
    score_image_name = f"{team1_resolved}vs{team2_resolved}_tahmini_skor.png"

    import time
    ts = int(time.time())

    return {
        "team1": team1_resolved,
        "team2": team2_resolved,
        "team1_logo_url": f"/logos/{team1_resolved}.png",
        "team2_logo_url": f"/logos/{team2_resolved}.png",
        "team1_formation": home_form,
        "team2_formation": away_form,
        "win_prob": percent(clean_val(combined["home_win"])),
        "draw_prob": percent(clean_val(combined["draw"])),
        "lose_prob": percent(clean_val(combined["home_loss"])),
        "predicted_score": combined["headline_score"],
        "exp_home_goals": round(clean_val(combined["exp_home_goals"]), 2),
        "exp_away_goals": round(clean_val(combined["exp_away_goals"]), 2),
        "prob_image_url": f"/outputs/{prob_image_name}?v={ts}",
        "score_image_url": f"/outputs/{score_image_name}?v={ts}",
        "image_url": f"/outputs/{prob_image_name}?v={ts}",
        "secondary_image_url": f"/outputs/{score_image_name}?v={ts}",
        "top5_scores": top5_list,
        "markov_form": markov_data,
        "avg_ratings": avg_ratings,
        "simulated_matches": int(result.home_sim.simulated_matches + result.away_sim.simulated_matches),
        "adjustments": {
            "team1": float(team1_adj),
            "team2": float(team2_adj),
        },
    }
