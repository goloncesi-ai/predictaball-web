from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime
import math
import json
import os
import re
import shutil
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
DATA_ROOT_DIR = os.path.join(BASE_DIR, "Data")
BASE_DATA_DIR = os.path.join(DATA_ROOT_DIR, "Turkish Super League")
ASSETS_DIR = os.path.join(BASE_DIR, "Data", "Algorithm", "PredictaBall")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

SIMULATION_LEAGUE_FOLDERS = [
    "Turkish Super League",
    "Premier League",
    "Bundesliga",
    "Ligue 1",
    "Serie A",
    "LaLiga",
]

# Ensure output dir exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

_PLAYER_ANALYSIS_CACHE = {
    "signature": None,
    "payload": None
}

_ANALYSIS_TEAMS_CACHE = {
    "signature": None,
    "payload": None
}

_PRECOMPUTED_HMM_CACHE = {
    "file_path": None,
    "mtime": None,
    "round": None,
    "team_values": {},
    "team_names": {},
}


def _get_schedule_current_round(default_round=19):
    schedule_file = os.path.join(BASE_DIR, 'Data', 'schedule', 'season_schedule.json')
    if not os.path.exists(schedule_file):
        return default_round

    try:
        with open(schedule_file, 'r', encoding='utf-8') as f:
            schedule = json.load(f)
        round_num = schedule.get('current_round', default_round)
        return int(round_num) if round_num is not None else default_round
    except Exception:
        return default_round


def _extract_round_from_filename(file_path):
    match = re.search(r'round_(\d+)', os.path.basename(str(file_path or '')))
    if not match:
        return None
    try:
        return int(match.group(1))
    except Exception:
        return None


def _resolve_predictions_file(round_num=None):
    predictions_dir = os.path.join(BASE_DIR, 'Data', 'predictions')
    if not os.path.isdir(predictions_dir):
        return None, None

    candidates = []
    seen = set()

    def _add_candidate(file_path, round_hint=None):
        if not file_path:
            return
        normalized = os.path.normpath(file_path)
        if normalized in seen:
            return
        seen.add(normalized)
        candidates.append((normalized, round_hint))

    if isinstance(round_num, int):
        _add_candidate(os.path.join(predictions_dir, f'round_{round_num:02d}.json'), round_num)
        _add_candidate(os.path.join(predictions_dir, f'round_{round_num:02d}_sample.json'), round_num)
    else:
        schedule_round = _get_schedule_current_round()
        _add_candidate(os.path.join(predictions_dir, f'round_{schedule_round:02d}.json'), schedule_round)
        _add_candidate(os.path.join(predictions_dir, f'round_{schedule_round:02d}_sample.json'), schedule_round)

        discovered = []
        for fname in os.listdir(predictions_dir):
            if not fname.startswith('round_') or not fname.endswith('.json'):
                continue
            if '_sample' in fname:
                continue
            fpath = os.path.join(predictions_dir, fname)
            if not os.path.isfile(fpath):
                continue
            try:
                mtime = os.path.getmtime(fpath)
            except Exception:
                mtime = 0
            discovered.append((mtime, fpath, _extract_round_from_filename(fname)))

        discovered.sort(key=lambda row: row[0], reverse=True)
        for _, fpath, round_hint in discovered:
            _add_candidate(fpath, round_hint)

    for file_path, round_hint in candidates:
        if os.path.exists(file_path):
            return file_path, round_hint
    return None, None


def _list_prediction_files_by_mtime(include_sample=False):
    predictions_dir = os.path.join(BASE_DIR, 'Data', 'predictions')
    if not os.path.isdir(predictions_dir):
        return []

    rows = []
    for fname in os.listdir(predictions_dir):
        if not fname.startswith('round_') or not fname.endswith('.json'):
            continue
        if not include_sample and '_sample' in fname:
            continue
        fpath = os.path.join(predictions_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            mtime = os.path.getmtime(fpath)
        except Exception:
            mtime = 0
        rows.append((mtime, fpath, _extract_round_from_filename(fname)))

    rows.sort(key=lambda row: row[0], reverse=True)
    return rows


def _extract_hmm_team_maps(predictions):
    team_values = {}
    team_names = {}

    for match in predictions.get('matches', []):
        adjustments = match.get('adjustments') or {}
        rows = [
            (match.get('home_team'), adjustments.get('hmm_team1')),
            (match.get('away_team'), adjustments.get('hmm_team2')),
        ]
        for team_name_raw, hmm_raw in rows:
            team_name = _normalize_text(team_name_raw)
            if not team_name or hmm_raw is None:
                continue
            team_key = _team_key(team_name)
            if not team_key:
                continue
            team_values[team_key] = round(_to_float(hmm_raw, 0.0), 2)
            team_names[team_key] = team_name

    return team_values, team_names


def _load_precomputed_hmm_values(round_num=None):
    predictions_file, round_hint = _resolve_predictions_file(round_num)
    if not predictions_file:
        return {
            "round": round_hint,
            "source_file": None,
            "team_values": {},
            "team_names": {},
        }

    try:
        mtime = os.path.getmtime(predictions_file)
    except Exception:
        mtime = 0

    cache_eligible = round_num is None
    if (
        cache_eligible and
        _PRECOMPUTED_HMM_CACHE["file_path"] == predictions_file and
        _PRECOMPUTED_HMM_CACHE["mtime"] == mtime and
        bool(_PRECOMPUTED_HMM_CACHE["team_values"])
    ):
        return {
            "round": _PRECOMPUTED_HMM_CACHE["round"],
            "source_file": predictions_file,
            "team_values": dict(_PRECOMPUTED_HMM_CACHE["team_values"]),
            "team_names": dict(_PRECOMPUTED_HMM_CACHE["team_names"]),
        }

    with open(predictions_file, 'r', encoding='utf-8') as f:
        predictions = json.load(f)

    resolved_round = predictions.get('round')
    if resolved_round is None:
        resolved_round = round_hint if round_hint is not None else _extract_round_from_filename(predictions_file)

    team_values, team_names = _extract_hmm_team_maps(predictions)

    # Some rounds may not have adjustments yet. In that case, use the newest
    # generated predictions file that includes precomputed HMM adjustments.
    if round_num is None and not team_values:
        for _, fallback_file, fallback_round in _list_prediction_files_by_mtime(include_sample=False):
            if os.path.normpath(fallback_file) == os.path.normpath(predictions_file):
                continue
            try:
                with open(fallback_file, 'r', encoding='utf-8') as f:
                    fallback_predictions = json.load(f)
            except Exception:
                continue

            fallback_values, fallback_names = _extract_hmm_team_maps(fallback_predictions)
            if not fallback_values:
                continue

            predictions_file = fallback_file
            team_values = fallback_values
            team_names = fallback_names
            resolved_round = fallback_predictions.get('round')
            if resolved_round is None:
                resolved_round = fallback_round if fallback_round is not None else _extract_round_from_filename(fallback_file)
            try:
                mtime = os.path.getmtime(predictions_file)
            except Exception:
                mtime = 0
            break

    if cache_eligible:
        _PRECOMPUTED_HMM_CACHE["file_path"] = predictions_file
        _PRECOMPUTED_HMM_CACHE["mtime"] = mtime
        _PRECOMPUTED_HMM_CACHE["round"] = resolved_round
        _PRECOMPUTED_HMM_CACHE["team_values"] = dict(team_values)
        _PRECOMPUTED_HMM_CACHE["team_names"] = dict(team_names)

    return {
        "round": resolved_round,
        "source_file": predictions_file,
        "team_values": team_values,
        "team_names": team_names,
    }


def _lookup_precomputed_hmm(team_name, team_values, team_names):
    name = _normalize_text(team_name)
    if not name:
        return 0.0, None

    target_key = _team_key(name)
    if target_key in team_values:
        return team_values[target_key], team_names.get(target_key) or name

    for key, value in team_values.items():
        if target_key in key or key in target_key:
            return value, team_names.get(key) or name

    return 0.0, None


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


def _normalize_text(value):
    return unicodedata.normalize("NFC", str(value or "")).strip()


def _team_key(value):
    text = _normalize_text(value)
    text = text.translate(str.maketrans({
        "ı": "i", "İ": "i",
        "ş": "s", "Ş": "s",
        "ğ": "g", "Ğ": "g",
        "ç": "c", "Ç": "c",
        "ö": "o", "Ö": "o",
        "ü": "u", "Ü": "u",
    }))
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return re.sub(r"[\W_]+", "", text.lower())


def _fuzzy_team_match(target, candidate):
    t = _team_key(target)
    c = _team_key(candidate)
    if not t or not c:
        return False
    return t in c or c in t


def _resolve_simulation_league_folder(value):
    requested_key = _team_key(value)
    if not requested_key:
        return SIMULATION_LEAGUE_FOLDERS[0]

    for league_folder in SIMULATION_LEAGUE_FOLDERS:
        if _team_key(league_folder) == requested_key:
            return league_folder

    for league_folder in SIMULATION_LEAGUE_FOLDERS:
        league_key = _team_key(league_folder)
        if requested_key in league_key or league_key in requested_key:
            return league_folder

    return SIMULATION_LEAGUE_FOLDERS[0]


def _get_simulation_league_dir(league_folder):
    return os.path.join(DATA_ROOT_DIR, league_folder)


def _relative_data_path(abs_path):
    if not abs_path:
        return None
    try:
        rel_path = os.path.relpath(abs_path, DATA_ROOT_DIR)
    except Exception:
        return None
    return rel_path.replace(os.sep, "/")


def _find_team_games_input_paths(league_folder, team_folder):
    team_dir = os.path.join(_get_simulation_league_dir(league_folder), team_folder)
    if not os.path.isdir(team_dir):
        return {
            "csv_abs": None,
            "xlsx_abs": None,
            "csv_rel": None,
            "xlsx_rel": None,
        }

    team_key = _team_key(team_folder)
    buckets = {"csv": [], "xlsx": []}
    for root, _, files in os.walk(team_dir):
        for file_name in files:
            lower = file_name.lower()
            if "_games_input" not in lower:
                continue
            ext = "csv" if lower.endswith(".csv") else ("xlsx" if lower.endswith(".xlsx") else None)
            if not ext:
                continue

            abs_path = os.path.join(root, file_name)
            stem = os.path.splitext(file_name)[0]
            stem = re.sub(r"_games_input$", "", stem, flags=re.IGNORECASE)
            stem_key = _team_key(stem)
            score = 0
            if os.path.basename(root) == "mixed-seasons":
                score += 100
            if stem_key and stem_key == team_key:
                score += 80
            elif stem_key and team_key and (stem_key in team_key or team_key in stem_key):
                score += 40
            try:
                mtime = os.path.getmtime(abs_path)
            except Exception:
                mtime = 0
            buckets[ext].append((score, mtime, abs_path))

    def _pick_best(ext):
        rows = buckets.get(ext) or []
        if not rows:
            return None
        rows.sort(key=lambda row: (row[0], row[1]), reverse=True)
        return rows[0][2]

    csv_abs = _pick_best("csv")
    xlsx_abs = _pick_best("xlsx")
    return {
        "csv_abs": csv_abs,
        "xlsx_abs": xlsx_abs,
        "csv_rel": _relative_data_path(csv_abs),
        "xlsx_rel": _relative_data_path(xlsx_abs),
    }


def _ensure_team_mixed_seasons_layout(league_folder, team_folder):
    paths = _find_team_games_input_paths(league_folder, team_folder)
    team_dir = os.path.join(_get_simulation_league_dir(league_folder), team_folder)
    mixed_dir = os.path.join(team_dir, "mixed-seasons")
    os.makedirs(mixed_dir, exist_ok=True)

    for ext in ("csv", "xlsx"):
        src_abs = paths.get(f"{ext}_abs")
        if not src_abs:
            continue
        target_abs = os.path.join(mixed_dir, f"{team_folder}_Games_Input.{ext}")
        if os.path.normpath(src_abs) != os.path.normpath(target_abs) and not os.path.exists(target_abs):
            shutil.copy2(src_abs, target_abs)
        paths[f"{ext}_resolved_abs"] = target_abs if os.path.exists(target_abs) else src_abs
        paths[f"{ext}_resolved_rel"] = _relative_data_path(paths[f"{ext}_resolved_abs"])

    return paths


def _paths_have_games_input(paths):
    if not isinstance(paths, dict):
        return False
    return bool(
        paths.get("csv_resolved_abs")
        or paths.get("xlsx_resolved_abs")
        or paths.get("csv_abs")
        or paths.get("xlsx_abs")
    )


def _discover_simulation_teams(league_folder):
    league_dir = _get_simulation_league_dir(league_folder)
    if not os.path.isdir(league_dir):
        return []

    teams = []
    for team_folder in sorted(os.listdir(league_dir)):
        team_dir = os.path.join(league_dir, team_folder)
        if not os.path.isdir(team_dir):
            continue

        paths = _find_team_games_input_paths(league_folder, team_folder)

        teams.append({
            "name": _normalize_text(team_folder),
            "folder": team_folder,
            "has_games_input": _paths_have_games_input(paths),
            "lineup_csv_path": f"/Data/{paths['csv_rel']}" if paths.get("csv_rel") else None,
            "lineup_xlsx_path": f"/Data/{paths['xlsx_rel']}" if paths.get("xlsx_rel") else None,
        })

    return teams


def _logo_match_keys(value):
    base = _team_key(value)
    keys = {base}
    for suffix in ("fk", "jk"):
        if base.endswith(suffix) and len(base) > len(suffix):
            keys.add(base[:-len(suffix)])
    return {k for k in keys if k}


def _resolve_logo_filename(logo_dir, requested_name):
    requested = os.path.basename(str(requested_name or "")).strip()
    if not requested:
        return None

    direct_path = os.path.join(logo_dir, requested)
    if os.path.exists(direct_path):
        return requested

    stem, ext = os.path.splitext(requested)
    ext = (ext or ".png").lower()
    request_keys = _logo_match_keys(stem)

    candidates = []
    try:
        for fname in os.listdir(logo_dir):
            fpath = os.path.join(logo_dir, fname)
            if not os.path.isfile(fpath):
                continue
            fstem, fext = os.path.splitext(fname)
            if fext.lower() != ext:
                continue
            fkey = _team_key(fstem)
            candidates.append((fname, fkey))
            if fkey in request_keys:
                return fname

        for fname, fkey in candidates:
            if any(rk in fkey or fkey in rk for rk in request_keys):
                return fname
    except Exception:
        return None

    return None


def _ensure_team_logo_asset(team_name):
    team = _normalize_text(team_name)
    if not team:
        return

    logo_dir = os.path.join(ASSETS_DIR, "Logos")
    if not os.path.isdir(logo_dir):
        return

    target_name = f"{team}.png"
    target_path = os.path.join(logo_dir, target_name)
    if os.path.exists(target_path):
        return

    source_name = _resolve_logo_filename(logo_dir, target_name)
    source_path = os.path.join(logo_dir, source_name) if source_name else None

    if not source_path or not os.path.exists(source_path):
        fallback_public_logo = os.path.join(BASE_DIR, "public", "logo.png")
        if os.path.exists(fallback_public_logo):
            source_path = fallback_public_logo
        else:
            return

    try:
        shutil.copy2(source_path, target_path)
    except Exception:
        return


def _to_float(value, default=0.0):
    if value is None:
        return default
    if hasattr(value, "item"):
        try:
            value = value.item()
        except Exception:
            pass
    try:
        if isinstance(value, str):
            value = value.strip().replace("%", "")
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except Exception:
        return default


def _to_int(value, default=0):
    return int(round(_to_float(value, default)))


def _discover_analysis_sources():
    sources = []
    if not os.path.exists(BASE_DATA_DIR):
        return sources

    for team_folder in sorted(os.listdir(BASE_DATA_DIR)):
        team_path = os.path.join(BASE_DATA_DIR, team_folder)
        if not os.path.isdir(team_path):
            continue

        mixed_path = os.path.join(team_path, "mixed-seasons")
        if not os.path.isdir(mixed_path):
            continue

        entries = sorted(os.listdir(mixed_path))
        csv_candidates = [f for f in entries if f.endswith(".csv") and "_Games_Input" in f]
        xlsx_candidates = [f for f in entries if f.endswith(".xlsx") and "_Games_Input" in f]

        file_name = csv_candidates[0] if csv_candidates else (xlsx_candidates[0] if xlsx_candidates else None)
        if not file_name:
            continue

        file_path = os.path.join(mixed_path, file_name)
        try:
            stat = os.stat(file_path)
            mtime = stat.st_mtime
            size = stat.st_size
        except Exception:
            mtime = 0
            size = 0

        sources.append({
            "team_folder": team_folder,
            "team_name": _normalize_text(team_folder),
            "file_name": file_name,
            "file_path": file_path,
            "mtime": mtime,
            "size": size,
        })

    return sources


def _read_analysis_df(file_path):
    import pandas as pd

    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path)
    else:
        try:
            df = pd.read_excel(file_path, sheet_name="Sheet1")
        except Exception:
            df = pd.read_excel(file_path)
    return df.drop_duplicates()


def _build_team_analysis_entry(df, team_name):
    numeric_cols = [
        "Team1_Goals", "Team2_Goals",
        "Team1_TotalShots", "Team2_TotalShots",
        "Team1_BallPosses", "Team2_BallPosses",
        "Team1_Corners", "Team2_Corners",
        "Team1_Passes", "Team2_Passes",
        "Team1_BigChances", "Team2_BigChances",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(_to_float)

    acc = {
        "games": 0,
        "goals_scored": 0.0,
        "goals_conceded": 0.0,
        "shots": 0.0,
        "possession_sum": 0.0,
        "corners": 0.0,
        "wins": 0,
        "draws": 0,
        "losses": 0,
    }
    history = []
    h2h = {}

    for _, row in df.iterrows():
        t1 = _normalize_text(row.get("Team1"))
        t2 = _normalize_text(row.get("Team2"))

        is_team1 = _fuzzy_team_match(team_name, t1)
        is_team2 = _fuzzy_team_match(team_name, t2)
        if not is_team1 and not is_team2:
            continue

        acc["games"] += 1

        if is_team1:
            my_goals = _to_float(row.get("Team1_Goals"))
            op_goals = _to_float(row.get("Team2_Goals"))
            my_shots = _to_float(row.get("Team1_TotalShots"))
            my_poss = _to_float(row.get("Team1_BallPosses"))
            my_corners = _to_float(row.get("Team1_Corners"))
            my_passes = _to_float(row.get("Team1_Passes"))
            my_big = _to_float(row.get("Team1_BigChances"))
            opponent = t2
            home_away = _normalize_text(row.get("Team1H_A")) or "H"
        else:
            my_goals = _to_float(row.get("Team2_Goals"))
            op_goals = _to_float(row.get("Team1_Goals"))
            my_shots = _to_float(row.get("Team2_TotalShots"))
            my_poss = _to_float(row.get("Team2_BallPosses"))
            my_corners = _to_float(row.get("Team2_Corners"))
            my_passes = _to_float(row.get("Team2_Passes"))
            my_big = _to_float(row.get("Team2_BigChances"))
            opponent = t1
            original_ha = _normalize_text(row.get("Team1H_A")) or "H"
            home_away = "A" if original_ha == "H" else "H"

        acc["goals_scored"] += my_goals
        acc["goals_conceded"] += op_goals
        acc["shots"] += my_shots
        acc["possession_sum"] += my_poss
        acc["corners"] += my_corners

        if my_goals > op_goals:
            acc["wins"] += 1
            result = "W"
        elif my_goals == op_goals:
            acc["draws"] += 1
            result = "D"
        else:
            acc["losses"] += 1
            result = "L"

        history.append({
            "opponent": opponent,
            "home_away": home_away,
            "goals_for": _to_int(my_goals),
            "goals_against": _to_int(op_goals),
            "shots": _to_int(my_shots),
            "possession": round(_to_float(my_poss), 2),
            "corners": _to_int(my_corners),
            "passes": _to_int(my_passes),
            "big_chances": _to_int(my_big),
            "result": result,
        })

        if opponent not in h2h:
            h2h[opponent] = {
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
            }

        h2h[opponent]["goals_for"] += _to_int(my_goals)
        h2h[opponent]["goals_against"] += _to_int(op_goals)
        if result == "W":
            h2h[opponent]["wins"] += 1
        elif result == "D":
            h2h[opponent]["draws"] += 1
        else:
            h2h[opponent]["losses"] += 1

    if acc["games"] == 0:
        return None

    g = acc["games"]
    return {
        "name": team_name,
        "stats": {
            "win_rate": acc["wins"] / g,
            "avg_goals_scored": acc["goals_scored"] / g,
            "avg_goals_conceded": acc["goals_conceded"] / g,
            "avg_shots": acc["shots"] / g,
            "avg_possession": acc["possession_sum"] / g,
            "avg_corners": acc["corners"] / g,
            "total_games": g,
            "wins": acc["wins"],
            "draws": acc["draws"],
            "losses": acc["losses"],
        },
        "match_history": history[:20],
        "head_to_head": h2h,
    }


def _load_analysis_teams_payload(limit=None, force_refresh=False):
    sources = _discover_analysis_sources()
    if limit:
        sources = sources[:max(limit, 0)]

    signature = tuple((s["file_path"], s["mtime"], s["size"]) for s in sources)
    if (not force_refresh and
            _ANALYSIS_TEAMS_CACHE["payload"] is not None and
            _ANALYSIS_TEAMS_CACHE["signature"] == signature):
        return _ANALYSIS_TEAMS_CACHE["payload"]

    teams = []
    for source in sources:
        try:
            df = _read_analysis_df(source["file_path"])
            team_entry = _build_team_analysis_entry(df, source["team_name"])
            if team_entry:
                teams.append(team_entry)
        except Exception as exc:
            print(f"Analysis source failed for {source['team_name']}: {exc}")

    teams.sort(key=lambda t: t["name"])

    payload = {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "teamCount": len(teams),
        "sourceCount": len(sources),
        "teams": teams,
    }
    _ANALYSIS_TEAMS_CACHE["signature"] = signature
    _ANALYSIS_TEAMS_CACHE["payload"] = payload
    return payload


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
        league = data.get('league')
        sim_type = data.get('type')
        team1_formation = data.get('team1_formation')
        team2_formation = data.get('team2_formation')
        team1_adj = data.get('team1_adj', 0)
        team2_adj = data.get('team2_adj', 0)

        if not team1 or not team2:
            return jsonify({"error": "Missing teams"}), 400

        results = {}
        league_folder = _resolve_simulation_league_folder(league)
        base_data_dir = _get_simulation_league_dir(league_folder)
        if not os.path.isdir(base_data_dir):
            return jsonify({"error": f"League data folder not found: {league_folder}"}), 400

        team1_paths = _ensure_team_mixed_seasons_layout(league_folder, team1)
        team2_paths = _ensure_team_mixed_seasons_layout(league_folder, team2)
        if not _paths_have_games_input(team1_paths):
            return jsonify({"error": f"No *_Games_Input file found for {team1} in {league_folder}"}), 400
        if not _paths_have_games_input(team2_paths):
            return jsonify({"error": f"No *_Games_Input file found for {team2} in {league_folder}"}), 400
        _ensure_team_logo_asset(team1)
        _ensure_team_logo_asset(team2)

        # Import combined adapter (it should be found via sys.path)
        import combined_adapter
    
        # Run the Combined Simulation
        results = combined_adapter.simulate_match(
            team1, 
            team2, 
            ASSETS_DIR, 
            base_data_dir,
            OUTPUT_DIR,
            sim_type,
            team1_adj,
            team2_adj,
            team1_formation=team1_formation,
            team2_formation=team2_formation,
            apply_hmm_adjustments=False
        )

        if isinstance(results, dict):
            results["league"] = league_folder
        
        return jsonify(results)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/hmm-adjustment', methods=['GET'])
def get_hmm_adjustment():
    try:
        team = request.args.get('team', '').strip()
        league = request.args.get('league', '')
        round_num = request.args.get('round', type=int)
        if not team:
            return jsonify({"error": "Team parameter required"}), 400

        league_folder = _resolve_simulation_league_folder(league)
        if league_folder == SIMULATION_LEAGUE_FOLDERS[0]:
            hmm_payload = _load_precomputed_hmm_values(round_num=round_num)
            value, matched_team = _lookup_precomputed_hmm(
                team,
                hmm_payload["team_values"],
                hmm_payload["team_names"],
            )
            return jsonify({
                "team": team,
                "league": league_folder,
                "matched_team": matched_team,
                "hmm_adjustment": round(float(value), 2),
                "round": hmm_payload.get("round"),
                "source": "predictions_precomputed",
                "source_file": os.path.basename(hmm_payload["source_file"]) if hmm_payload.get("source_file") else None
            })

        import combined_adapter
        team_paths = _ensure_team_mixed_seasons_layout(league_folder, team)
        if not _paths_have_games_input(team_paths):
            return jsonify({
                "team": team,
                "league": league_folder,
                "matched_team": None,
                "hmm_adjustment": 0.0,
                "round": None,
                "source": "missing_games_input",
                "source_file": None
            })
        runtime = combined_adapter.get_hmm_adjustment(
            team_name=team,
            assets_path=ASSETS_DIR,
            base_data_dir=_get_simulation_league_dir(league_folder),
            output_dir=OUTPUT_DIR,
        )
        return jsonify({
            "team": team,
            "league": league_folder,
            "matched_team": runtime.get("team"),
            "hmm_adjustment": round(float(runtime.get("hmm_adjustment", 0.0)), 2),
            "round": None,
            "source": "engine_runtime",
            "source_file": None
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/hmm-adjustments', methods=['GET'])
def get_hmm_adjustments():
    try:
        home_team = request.args.get('home_team', '').strip()
        away_team = request.args.get('away_team', '').strip()
        league = request.args.get('league', '')
        round_num = request.args.get('round', type=int)
        if not home_team and not away_team:
            return jsonify({"error": "At least one of home_team or away_team is required"}), 400

        league_folder = _resolve_simulation_league_folder(league)

        if league_folder == SIMULATION_LEAGUE_FOLDERS[0]:
            hmm_payload = _load_precomputed_hmm_values(round_num=round_num)
            home_value, home_matched = _lookup_precomputed_hmm(
                home_team,
                hmm_payload["team_values"],
                hmm_payload["team_names"],
            ) if home_team else (0.0, None)
            away_value, away_matched = _lookup_precomputed_hmm(
                away_team,
                hmm_payload["team_values"],
                hmm_payload["team_names"],
            ) if away_team else (0.0, None)

            return jsonify({
                "home_team": home_team,
                "away_team": away_team,
                "league": league_folder,
                "home_hmm_adjustment": round(float(home_value), 2),
                "away_hmm_adjustment": round(float(away_value), 2),
                "home_matched_team": home_matched,
                "away_matched_team": away_matched,
                "source": "predictions_precomputed",
                "round": hmm_payload.get("round"),
                "source_file": os.path.basename(hmm_payload["source_file"]) if hmm_payload.get("source_file") else None
            })

        import combined_adapter
        base_data_dir = _get_simulation_league_dir(league_folder)
        home_missing = False
        away_missing = False
        if home_team:
            home_missing = not _paths_have_games_input(_ensure_team_mixed_seasons_layout(league_folder, home_team))
        if away_team:
            away_missing = not _paths_have_games_input(_ensure_team_mixed_seasons_layout(league_folder, away_team))
        home_runtime = combined_adapter.get_hmm_adjustment(
            team_name=home_team,
            assets_path=ASSETS_DIR,
            base_data_dir=base_data_dir,
            output_dir=OUTPUT_DIR,
        ) if home_team and not home_missing else {"team": None, "hmm_adjustment": 0.0}
        away_runtime = combined_adapter.get_hmm_adjustment(
            team_name=away_team,
            assets_path=ASSETS_DIR,
            base_data_dir=base_data_dir,
            output_dir=OUTPUT_DIR,
        ) if away_team and not away_missing else {"team": None, "hmm_adjustment": 0.0}
        source_label = "engine_runtime"
        if home_missing or away_missing:
            has_runtime = (home_team and not home_missing) or (away_team and not away_missing)
            source_label = "engine_runtime_partial" if has_runtime else "missing_games_input"

        return jsonify({
            "home_team": home_team,
            "away_team": away_team,
            "league": league_folder,
            "home_hmm_adjustment": round(float(home_runtime.get("hmm_adjustment", 0.0)), 2),
            "away_hmm_adjustment": round(float(away_runtime.get("hmm_adjustment", 0.0)), 2),
            "home_matched_team": home_runtime.get("team"),
            "away_matched_team": away_runtime.get("team"),
            "source": source_label,
            "round": None,
            "source_file": None
        })
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

@app.route('/api/analysis-data', methods=['GET'])
def get_analysis_data():
    """Return live team analysis data built from mixed-seasons game files."""
    try:
        limit = request.args.get('limit', type=int)
        refresh = request.args.get('refresh', '0') == '1'
        payload = _load_analysis_teams_payload(limit=limit, force_refresh=refresh)
        return jsonify(payload)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route('/api/simulation-options', methods=['GET'])
def get_simulation_options():
    """Return supported leagues and available teams for simulation."""
    try:
        leagues = []
        for league_folder in SIMULATION_LEAGUE_FOLDERS:
            teams = _discover_simulation_teams(league_folder)
            if not teams:
                continue
            leagues.append({
                "name": league_folder,
                "folder": league_folder,
                "team_count": len(teams),
                "teams": teams,
            })

        return jsonify({
            "default_league": SIMULATION_LEAGUE_FOLDERS[0],
            "league_count": len(leagues),
            "leagues": leagues,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/logos/<path:filename>')
def serve_logo(filename):
    logo_dir = os.path.join(ASSETS_DIR, "Logos")
    resolved = _resolve_logo_filename(logo_dir, filename) or filename
    return send_from_directory(logo_dir, resolved)

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
                        "heatmaps": pred_match.get('heatmaps', {}),
                        "player_heatmap_url": pred_match.get('player_heatmap_url'),
                        "main_cluster_heatmap_url": pred_match.get('main_cluster_heatmap_url'),
                        "strip_cluster_heatmap_url": pred_match.get('strip_cluster_heatmap_url'),
                        "top5_scores": pred_match.get('top5_scores', []),
                        "top5_scores_home_perspective": pred_match.get('top5_scores_home_perspective', pred_match.get('top5_scores', [])),
                        "top5_scores_away_perspective": pred_match.get('top5_scores_away_perspective', []),
                        "markov_form": pred_match.get('markov_form'),
                        "adjustments": pred_match.get('adjustments'),
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
