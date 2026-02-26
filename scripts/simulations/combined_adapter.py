import importlib
import logging
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
LOGGER = logging.getLogger(__name__)


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


def _get_engine(base_data_dir, output_dir, logo_dir, n_sims_home, n_sims_away):
    key = (str(base_data_dir), str(output_dir), str(logo_dir), int(n_sims_home), int(n_sims_away))
    if key in _ENGINE_CACHE:
        return _ENGINE_CACHE[key]

    paths = PathsConfig(
        main_folder=Path(base_data_dir),
        output_folder=Path(output_dir),
        logo_folder=Path(logo_dir),
    )
    cfg = SimulationConfig(
        n_sims_home_perspective=int(n_sims_home),
        n_sims_away_perspective=int(n_sims_away),
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
        LOGGER.warning("Image module setup failed: %s", e)
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
        LOGGER.warning("Markov form generation failed: %s", e)
        return None


def _safe_hmm_adjustment(engine, team_name):
    """Return HMM-suggested adjustment pct for a team, defaulting to 0 on failure."""
    try:
        suggestion = engine.suggest_adjustments_hmm(team_name) or {}
        return float(suggestion.get("suggested_adj_pct", 0.0))
    except Exception as e:
        LOGGER.warning("HMM adjustment fallback for %s: %s", team_name, e)
        return 0.0


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


def get_hmm_adjustment(
    team_name,
    assets_path,
    base_data_dir,
    output_dir,
):
    """Return resolved team name and HMM-suggested adjustment percentage."""
    logo_dir = Path(assets_path) / "Logos"
    engine = _get_engine(base_data_dir, output_dir, logo_dir, n_sims_home=25, n_sims_away=25)
    team_resolved = _resolve_team_for_disk(base_data_dir, team_name)
    hmm_adj = _safe_hmm_adjustment(engine, team_resolved)
    return {
        "team": team_resolved,
        "hmm_adjustment": round(float(hmm_adj), 2),
    }


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
    apply_hmm_adjustments=True,
    n_sims_home=30,
    n_sims_away=30,
    include_heatmaps=False,
    include_markov=True,
    include_images=False,
):
    LOGGER.info("Starting Combined Simulation: %s vs %s", team1, team2)

    team1_resolved = _resolve_team_for_disk(base_data_dir, team1)
    team2_resolved = _resolve_team_for_disk(base_data_dir, team2)
    if team1_resolved != team1:
        LOGGER.info("Resolved Team1 '%s' -> '%s'", team1, team1_resolved)
    if team2_resolved != team2:
        LOGGER.info("Resolved Team2 '%s' -> '%s'", team2, team2_resolved)

    home_form = parse_formation(team1_formation) if team1_formation else _detect_team_formation(base_data_dir, team1_resolved)
    away_form = parse_formation(team2_formation) if team2_formation else _detect_team_formation(base_data_dir, team2_resolved)

    logo_dir = Path(assets_path) / "Logos"
    engine = _get_engine(base_data_dir, output_dir, logo_dir, n_sims_home=n_sims_home, n_sims_away=n_sims_away)

    can_generate_images = include_images and _configure_image_modules(output_dir, logo_dir)

    manual_team1_adj = float(team1_adj)
    manual_team2_adj = float(team2_adj)
    hmm_team1_adj = _safe_hmm_adjustment(engine, team1_resolved) if apply_hmm_adjustments else 0.0
    hmm_team2_adj = _safe_hmm_adjustment(engine, team2_resolved) if apply_hmm_adjustments else 0.0
    final_team1_adj = manual_team1_adj + hmm_team1_adj
    final_team2_adj = manual_team2_adj + hmm_team2_adj

    LOGGER.info(
        "Applied adjustments: %s manual=%+.2f%% hmm=%+.2f%% final=%+.2f%% | %s manual=%+.2f%% hmm=%+.2f%% final=%+.2f%%",
        team1_resolved, manual_team1_adj, hmm_team1_adj, final_team1_adj,
        team2_resolved, manual_team2_adj, hmm_team2_adj, final_team2_adj,
    )

    match_cfg = MatchConfig(
        home_team=team1_resolved,
        away_team=team2_resolved,
        home_formation=home_form,
        away_formation=away_form,
        home_adj_pct=final_team1_adj,
        away_adj_pct=final_team2_adj,
    )

    result = engine.run_match(
        match_cfg,
        draw_heatmaps=bool(include_heatmaps),
        generate_images=can_generate_images,
    )

    combined = result.combined
    top5_home_list = _build_top5_scores(result.home_sim.top5_scores)
    top5_away_list = _build_top5_scores(result.away_sim.top5_scores)
    markov_data = _build_markov_form(base_data_dir, team1_resolved, team2_resolved, engine.cfg.random_seed) if include_markov else None

    avg_ratings = {
        "team1": round(clean_val(result.home_sim.avg_team_ratings.get("team1", 0.0)), 2),
        "team2": round(clean_val(result.home_sim.avg_team_ratings.get("team2", 0.0)), 2),
    }

    prob_image_name = f"KimKazanir_{team1_resolved}vs{team2_resolved}.png"
    score_image_name = f"{team1_resolved}vs{team2_resolved}_tahmini_skor.png"

    import time
    ts = int(time.time())
    heatmap_urls = {}
    for k, p in (result.heatmaps or {}).items():
        try:
            heatmap_urls[k] = f"/outputs/{Path(p).name}?v={ts}"
        except Exception:
            continue

    prob_image_url = f"/outputs/{prob_image_name}?v={ts}" if can_generate_images else None
    score_image_url = f"/outputs/{score_image_name}?v={ts}" if can_generate_images else None

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
        "prob_image_url": prob_image_url,
        "score_image_url": score_image_url,
        "image_url": prob_image_url,
        "secondary_image_url": score_image_url,
        "heatmaps": heatmap_urls,
        "player_heatmap_url": heatmap_urls.get("player"),
        "main_cluster_heatmap_url": heatmap_urls.get("main_clusters"),
        "strip_cluster_heatmap_url": heatmap_urls.get("strip_clusters"),
        # Backward compatible field (home perspective).
        "top5_scores": top5_home_list,
        # Explicit perspective fields for dual scoreline views.
        "top5_scores_home_perspective": top5_home_list,
        "top5_scores_away_perspective": top5_away_list,
        "markov_form": markov_data,
        "avg_ratings": avg_ratings,
        "simulated_matches": int(result.home_sim.simulated_matches + result.away_sim.simulated_matches),
        "adjustments": {
            "team1": final_team1_adj,
            "team2": final_team2_adj,
            "manual_team1": manual_team1_adj,
            "manual_team2": manual_team2_adj,
            "hmm_team1": hmm_team1_adj,
            "hmm_team2": hmm_team2_adj,
            "hmm_applied": bool(apply_hmm_adjustments),
        },
    }
