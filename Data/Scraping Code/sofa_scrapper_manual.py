#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import json
import os
import pandas as pd
import unicodedata

# --------- GLOBAL JSON DIRECTORY (set at runtime in run_loop) ----------
JSON_DIR = "/Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/game_jsons"

# ----------------------------------------------------------------------
# Helper: load local JSON files named event.json / lineups.json / statistics.json
# ----------------------------------------------------------------------
def load_local_json(kind):
    """
    Load local JSON for a given kind:
      kind = 'event' | 'lineups' | 'statistics'
    Expects files named: <kind>.json under JSON_DIR.
    Example:
        event.json
        lineups.json
        statistics.json
    """
    if not JSON_DIR:
        raise RuntimeError("JSON directory not set. JSON_DIR is None.")

    fname = os.path.join(JSON_DIR, f"{kind}.json")
    if not os.path.isfile(fname):
        raise FileNotFoundError(f"Local JSON not found: {fname}")
    with open(fname, "r", encoding="utf-8") as f:
        return json.load(f)

# ----------------------------------------------------------------------
# OFFLINE fetch functions (no HTTP)
# ----------------------------------------------------------------------
def fetch_event():
    return load_local_json("event")

def fetch_lineups():
    return load_local_json("lineups")

def fetch_stats():
    # statistics are optional – if missing, we continue without them
    try:
        return load_local_json("statistics")
    except FileNotFoundError:
        print("… no local statistics.json found — continuing without stats.")
        return {}

# ----------------------------------------------------------------------
# Normalization helpers
# ----------------------------------------------------------------------
STAT_ALIASES = {
    "big chances": "Big chances",
    "total shots": "Total shots",
    "corner kicks": "Corner kicks",
    "passes": "Passes",
    "tackles": "Tackles",
    "free kicks": "Free kicks",
    "ball possession": "Ball possession",
    "corners": "Corner kicks",
    "possession": "Ball possession",
}
WANTED_KEYS = set(STAT_ALIASES.keys())

def norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def canonical(s):
    return STAT_ALIASES.get(norm(s), s)

def classify_position(val):
    if val is None:
        return "OTH"
    v = str(val).upper()
    if v in {"G", "GK", "GOALKEEPER", "1"}:
        return "GK"
    if v in {"D", "DEF", "DEFENDER", "2"}:
        return "DEF"
    if v in {"M", "MID", "MIDFIELDER", "3"}:
        return "MID"
    if v in {"F", "FW", "FORWARD", "4"}:
        return "FWD"
    return "OTH"

# ----------------------------------------------------------------------
# Parse team stats (from statistics JSON)
# ----------------------------------------------------------------------
def parse_team_stats(js):
    rows = []

    def maybe_add(d):
        if not isinstance(d, dict):
            return
        name = d.get("name") or d.get("title") or d.get("key")
        if not name or norm(name) not in WANTED_KEYS:
            return
        hv = (
            d.get("home") or d.get("homeValue") or d.get("valueHome")
            or d.get("homeTotal") or d.get("homeTotalValue")
        )
        av = (
            d.get("away") or d.get("awayValue") or d.get("valueAway")
            or d.get("awayTotal") or d.get("awayTotalValue")
        )
        if hv is None and av is None:
            return
        rows.append((canonical(name), hv, av))

    stack = [js]
    seen = set()
    while stack:
        o = stack.pop()
        if id(o) in seen:
            continue
        seen.add(id(o))
        if isinstance(o, dict):
            maybe_add(o)
            for v in o.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v, (dict, list)):
                    stack.append(v)

    return {name: (hv, av) for name, hv, av in rows}

# ----------------------------------------------------------------------
# Lineups / starters
# ----------------------------------------------------------------------
def starters_for_side(side):
    if isinstance(side.get("startingLineups"), list) and side["startingLineups"]:
        return side["startingLineups"][:11]
    out = []
    for p in side.get("players", []):
        if p.get("substitute") in (False, None, 0, "false", "False"):
            out.append(p)
    return out[:11]

def unwrap_player(p):
    if isinstance(p, dict) and isinstance(p.get("player"), dict):
        return p["player"], p
    return p, p

def ordered_names_and_ratings(lineups_json, side_key):
    side = lineups_json.get(side_key, {})
    starters = starters_for_side(side)
    rec = []
    for p in starters:
        player, cont = unwrap_player(p)
        pos = cont.get("position") or (player or {}).get("position")
        rt = (
            cont.get("rating")
            or cont.get("sofifaRating")
            or (cont.get("statistics") or {}).get("rating")
            or (player or {}).get("rating")
        )
        if isinstance(rt, dict):
            rt = rt.get("rating")
        if isinstance(rt, str):
            try:
                rt = float(rt)
            except Exception:
                pass
        rec.append(
            {
                "name": (player or {}).get("name"),
                "rating": rt,
                "pos": classify_position(pos),
            }
        )

    order = ["GK", "DEF", "MID", "FWD"]
    names, rates = [], []
    for o in order:
        for r in rec:
            if r["pos"] == o:
                names.append(r["name"])
                rates.append(r["rating"])
    for r in rec:
        if r["pos"] not in order:
            names.append(r["name"])
            rates.append(r["rating"])
    while len(names) < 11:
        names.append(None)
        rates.append(None)
    return names[:11], rates[:11]

# ----------------------------------------------------------------------
# Build one row for Excel
# ----------------------------------------------------------------------
def build_row(event, lineups, stats_dict, team1_name):
    evt = event["event"]
    home = evt["homeTeam"]["name"]
    away = evt["awayTeam"]["name"]

    if team1_name == home:
        t1_side, t2_side, team2_name, t1_HA = "home", "away", away, "H"
    elif team1_name == away:
        t1_side, t2_side, team2_name, t1_HA = "away", "home", home, "A"
    else:
        raise ValueError(f"Team1 '{team1_name}' not in match ({home} vs {away})")

    t1_form = lineups.get(t1_side, {}).get("formation")
    t2_form = lineups.get(t2_side, {}).get("formation")

    t1_names, t1_rates = ordered_names_and_ratings(lineups, t1_side)
    t2_names, t2_rates = ordered_names_and_ratings(lineups, t2_side)

    def score(side):
        sc = evt.get(f"{side}Score") or {}
        return sc.get("current", sc.get("display"))

    t1g, t2g = score(t1_side), score(t2_side)
    points = 3 if t1g > t2g else (1 if t1g == t2g else 0)

    def stat(label, side):
        hv, av = stats_dict.get(label, (None, None))
        return hv if side == "home" else av

    row = {
        "Team1": team1_name,
        "Team2": team2_name,
        "Team1H_A": t1_HA,
        "Team1Formation": t1_form,
        "Team2Formation": t2_form,
        "Win(3)_Draw(1)_Lose(0)": points,
    }

    # Names
    for i in range(1, 12):
        row[f"Team1Player{i}Name"] = t1_names[i - 1]
    for i in range(1, 12):
        row[f"Team2Player{i}Name"] = t2_names[i - 1]

    # Ratings
    for i in range(1, 12):
        row[f"Team1Player{i}"] = t1_rates[i - 1]
    for i in range(1, 12):
        row[f"Team2Player{i}"] = t2_rates[i - 1]

    row["Team1_Goals"] = t1g
    row["Team2_Goals"] = t2g

    labels = [
        ("Big chances", "BigChances"),
        ("Total shots", "TotalShots"),
        ("Corner kicks", "Corners"),
        ("Passes", "Passes"),
        ("Tackles", "Tackels"),
        ("Free kicks", "FreeKicks"),
        ("Ball possession", "BallPosses"),
    ]
    for api, suf in labels:
        row[f"Team1_{suf}"] = stat(api, t1_side)
        row[f"Team2_{suf}"] = stat(api, t2_side)

    return row

# ----------------------------------------------------------------------
def run_loop():
    global JSON_DIR

    print("SofaScore → Offline JSON Scraper (single match)")
    print("Uses event.json, lineups.json, statistics.json from a folder.\n")

    # ---- ask for PATH to existing master file ----
    infile = input("Path to your existing TEAM_Games_Input.xlsx file: ").strip()

    # PATH CLEANING for Excel file
    infile = infile.strip().strip("'").strip('"')
    infile = os.path.expanduser(infile)
    infile = unicodedata.normalize("NFC", infile)
    infile = os.path.normpath(infile)

    if not os.path.isfile(infile):
        print(f"\n❌ File not found:\n{infile}")
        return

    # ---- ask for PATH to JSON folder ----
    #json_dir = input(
    #    "\nPath to folder containing event.json / lineups.json / statistics.json\n"
    #    "(e.g. /Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/game_jsons): "
    #).strip()
    
    json_dir = "/Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/game_jsons"
    json_dir = json_dir.strip().strip("'").strip('"')
    json_dir = os.path.expanduser(json_dir)
    json_dir = unicodedata.normalize("NFC", json_dir)
    json_dir = os.path.normpath(json_dir)

    if not os.path.isdir(json_dir):
        print(f"\n❌ JSON folder not found:\n{json_dir}")
        return

    JSON_DIR = json_dir

    # quick existence check
    for kind in ["event", "lineups"]:
        f = os.path.join(JSON_DIR, f"{kind}.json")
        if not os.path.isfile(f):
            print(f"\n❌ Required file missing: {f}")
            return

    print(
        "\nJSON folder set to:\n"
        f"  {JSON_DIR}\n"
        "Files used:\n"
        "  event.json\n"
        "  lineups.json\n"
        "  statistics.json (optional)\n"
    )

    # ---- read existing master file (for Team1 + future merge) ----
    df_old = None
    try:
        df_old = pd.read_excel(infile)
    except Exception as e:
        print("[WARN] Could not read existing Excel, will treat as new file:", e)

    # ---- auto-detect Team1 ----
    team1_auto = None
    if df_old is not None and "Team1" in df_old.columns:
        non_null = df_old["Team1"].dropna()
        if not non_null.empty:
            team1_auto = non_null.mode().iloc[0]

    if team1_auto is None:
        base_name = os.path.splitext(os.path.basename(infile))[0]
        m = re.match(r"(.+)_Games_Input$", base_name)
        if m:
            team1_auto = m.group(1)
        else:
            team1_auto = base_name

    print(f"\nAuto-detected Team1: {team1_auto}")

    rows = []

    # ---- process the single match from local JSON ----
    try:
        event = fetch_event()
        lineups = fetch_lineups()
        stats = fetch_stats()
        stats_d = parse_team_stats(stats)

        evt = event["event"]
        h = evt["homeTeam"]["name"]
        a = evt["awayTeam"]["name"]
        print(f"\nDetected match: {h} vs {a}")

        if team1_auto not in {h, a}:
            print(
                f"\n[WARN] Auto Team1 '{team1_auto}' is not in this match "
                f"({h} vs {a}). No row will be added."
            )
        else:
            row = build_row(event, lineups, stats_d, team1_auto)
            rows.append(row)
            print("→ Row added.")

    except FileNotFoundError as e:
        print(f"[ERROR] Missing JSON file: {e}")
    except Exception as e:
        print("[ERROR]", e)

    if not rows:
        print("\nNo new rows. Exiting.")
        return

    # ---- NEW rows DataFrame ----
    base = [
        "Team1", "Team2", "Team1H_A",
        "Team1Formation", "Team2Formation",
        "Win(3)_Draw(1)_Lose(0)"
    ]
    t1_names = [f"Team1Player{i}Name" for i in range(1, 12)]
    t2_names = [f"Team2Player{i}Name" for i in range(1, 12)]
    t1_rates = [f"Team1Player{i}" for i in range(1, 12)]
    t2_rates = [f"Team2Player{i}" for i in range(1, 12)]
    goals = ["Team1_Goals", "Team2_Goals"]
    stats_cols = [
        "Team1_BigChances", "Team1_TotalShots", "Team1_Corners",
        "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks",
        "Team1_BallPosses",
        "Team2_BigChances", "Team2_TotalShots", "Team2_Corners",
        "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks",
        "Team2_BallPosses",
    ]
    col_order = base + t1_names + t2_names + t1_rates + t2_rates + goals + stats_cols

    df_new = pd.DataFrame(rows)
    for c in col_order:
        if c not in df_new.columns:
            df_new[c] = None
    df_new = df_new[col_order]

    # type fix on new rows
    for c in t1_rates + t2_rates:
        df_new[c] = pd.to_numeric(df_new[c], errors="coerce")

    int_cols = [
        "Team1_Goals", "Team2_Goals",
        "Team1_BigChances", "Team1_TotalShots", "Team1_Corners",
        "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks",
        "Team2_BigChances", "Team2_TotalShots", "Team2_Corners",
        "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks",
    ]
    for c in int_cols:
        df_new[c] = pd.to_numeric(df_new[c], errors="coerce").astype("Int64")

    for c in ["Team1_BallPosses", "Team2_BallPosses"]:
        df_new[c] = df_new[c].astype(str).str.replace("%", "", regex=False)
        df_new[c] = df_new[c].str.replace(",", ".", regex=False)
        df_new[c] = pd.to_numeric(df_new[c], errors="coerce") / 100

    # ---- merge with existing (prepend new rows) ----
    if df_old is not None:
        # align columns
        for c in df_new.columns:
            if c not in df_old.columns:
                df_old[c] = None
        for c in df_old.columns:
            if c not in df_new.columns:
                df_new[c] = None

        df_old = df_old[df_new.columns]
        df_combined = pd.concat([df_new, df_old], ignore_index=True)
        print("\nExisting file found → prepending new row.")
    else:
        df_combined = df_new
        print("\nNo readable existing file, creating fresh file.")

    # ---- Save back to same Excel + CSV ----
    xlsx_path = infile
    if xlsx_path.lower().endswith(".xlsx"):
        csv_path = xlsx_path[:-5] + ".csv"
    else:
        csv_path = xlsx_path + ".csv"

    df_combined.to_excel(xlsx_path, index=False)
    df_combined.to_csv(csv_path, index=False)

    print("\n✅ Updated master file saved:")
    print(xlsx_path)
    print(csv_path)

if __name__ == "__main__":
    run_loop()
