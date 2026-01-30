#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Weekly Scraper for Turkish Super League
Scrapes completed matches from the current round and updates team Excel files.
Self-contained version with all scraping functions included.
"""

import os
import re
import sys
import json
import time
import random
import logging
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/tmp/auto_scraper.log'),
        logging.StreamHandler()
    ]
)

# Base paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "Data" / "Turkish Super League"
SCHEDULE_FILE = BASE_DIR / "Data" / "schedule" / "season_schedule.json"

# Sofascore API
API_BASE = "https://api.sofascore.com/api/v1"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/"
})

# Team name to Excel file path mapping
TEAM_PATHS = {
    "Fenerbahçe": DATA_DIR / "Fenerbahçe" / "mixed-seasons" / "Fenerbahçe_Games_Input.xlsx",
    "Galatasaray": DATA_DIR / "Galatasaray" / "mixed-seasons" / "Galatasaray_Games_Input.xlsx",
    "Beşiktaş JK": DATA_DIR / "Beşiktaş" / "mixed-seasons" / "Beşiktaş_Games_Input.xlsx",
    "Trabzonspor": DATA_DIR / "Trabzonspor" / "mixed-seasons" / "Trabzonspor_Games_Input.xlsx",
    "Alanyaspor": DATA_DIR / "Alanyaspor" / "mixed-seasons" / "Alanyaspor_Games_Input.xlsx",
    "Antalyaspor": DATA_DIR / "Antalyaspor" / "mixed-seasons" / "Antalyaspor_Games_Input.xlsx",
    "Başakşehir FK": DATA_DIR / "Başakşehir" / "mixed-seasons" / "Başakşehir_Games_Input.xlsx",
    "Çaykur Rizespor": DATA_DIR / "Çaykur Rizespor" / "mixed-seasons" / "Çaykur Rizespor_Games_Input.xlsx",
    "Eyüpspor": DATA_DIR / "Eyüpspor" / "mixed-seasons" / "Eyüpspor_Games_Input.xlsx",
    "Fatih Karagümrük": DATA_DIR / "Fatih Karagümrük" / "mixed-seasons" / "Fatih Karagümrük_Games_Input.xlsx",
    "Gaziantep FK": DATA_DIR / "Gaziantep FK" / "mixed-seasons" / "Gaziantep FK_Games_Input.xlsx",
    "Gençlerbirliği": DATA_DIR / "Gençlerbirliği" / "mixed-seasons" / "Gençlerbirliği_Games_Input.xlsx",
    "Göztepe": DATA_DIR / "Göztepe" / "mixed-seasons" / "Göztepe_Games_Input.xlsx",
    "Kasımpaşa": DATA_DIR / "Kasımpaşa" / "mixed-seasons" / "Kasımpaşa_Games_Input.xlsx",
    "Kayserispor": DATA_DIR / "Kayserispor" / "mixed-seasons" / "Kayserispor_Games_Input.xlsx",
    "Kocaelispor": DATA_DIR / "Kocaelispor" / "mixed-seasons" / "Kocaelispor_Games_Input.xlsx",
    "Konyaspor": DATA_DIR / "Konyaspor" / "mixed-seasons" / "Konyaspor_Games_Input.xlsx",
    "Samsunspor": DATA_DIR / "Samsunspor" / "mixed-seasons" / "Samsunspor_Games_Input.xlsx",
}


# ============================================================================
# Sofascore Scraping Functions (copied from original scraper)
# ============================================================================

class SofaScoreChallengeError(RuntimeError):
    """Raised when SofaScore returns a Cloudflare/anti-bot challenge (HTTP 403)."""


def _polite_sleep():
    time.sleep(0.8 + random.random() * 0.8)


def get_json(url, retries=3, backoff=1.3):
    last = None
    for i in range(retries):
        _polite_sleep()
        r = SESSION.get(url, timeout=25)
        
        if r.ok:
            return r.json()
        
        # Check for Cloudflare challenge
        if r.status_code == 403:
            txt = r.text or ""
            if 'challenge' in txt.lower() or 'cloudflare' in txt.lower():
                raise SofaScoreChallengeError(
                    "SofaScore returned a 403 'challenge' (Cloudflare anti-bot). "
                    "Wait 15-60 minutes and try again."
                )
        
        last = (r.status_code, r.text[:800])
        time.sleep(backoff**i)
    
    code, body = last or ("?", "?")
    raise RuntimeError(f"Request failed {url} [{code}]: {body}")


def fetch_event(eid):
    return get_json(f"{API_BASE}/event/{eid}")


def fetch_lineups(eid):
    return get_json(f"{API_BASE}/event/{eid}/lineups")


def fetch_stats(eid):
    url = f"{API_BASE}/event/{eid}/statistics"
    try:
        return get_json(url)
    except RuntimeError as e:
        if "/statistics" in str(e) and "[404]" in str(e):
            logging.warning("No statistics available (404) — continuing without stats.")
            return {}
        raise


# Stat normalization
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


def parse_team_stats(js):
    """Extract team statistics from Sofascore stats JSON."""
    rows = []
    wanted_keys = set(STAT_ALIASES.keys())
    
    def maybe_add(d):
        if not isinstance(d, dict):
            return
        name = d.get("name") or d.get("title") or d.get("key")
        if not name or norm(name) not in wanted_keys:
            return
        hv = d.get("home") or d.get("homeValue") or d.get("valueHome") or d.get("homeTotal")
        av = d.get("away") or d.get("awayValue") or d.get("valueAway") or d.get("awayTotal")
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


def starters_for_side(side):
    """Extract starting 11 players from lineups."""
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
    """Extract player names and ratings in positional order."""
    side = lineups_json.get(side_key, {})
    starters = starters_for_side(side)
    rec = []
    for p in starters:
        player, cont = unwrap_player(p)
        pos = cont.get("position") or (player or {}).get("position")
        rt = (cont.get("rating")
              or cont.get("sofifaRating")
              or (cont.get("statistics") or {}).get("rating")
              or (player or {}).get("rating"))
        if isinstance(rt, dict):
            rt = rt.get("rating")
        if isinstance(rt, str):
            try:
                rt = float(rt)
            except:
                pass
        rec.append({"name": (player or {}).get("name"), "rating": rt, "pos": classify_position(pos)})
    
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


def build_row(event, lineups, stats_dict, team1_name):
    """Build a single row of data for the Excel file."""
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


# ============================================================================
# Automation Logic
# ============================================================================

def load_schedule():
    """Load the season schedule JSON."""
    with open(SCHEDULE_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_current_round_matches(schedule):
    """Get all finished matches from the current round."""
    current_round = schedule.get('current_round', 19)
    logging.info(f"Current round: {current_round}")
    
    for round_data in schedule.get('rounds', []):
        if round_data['round'] == current_round:
            finished_matches = [
                m for m in round_data['matches']
                if m.get('status') == 'finished' and m.get('match_id')
            ]
            logging.info(f"Found {len(finished_matches)} finished matches in round {current_round}")
            return finished_matches
    
    logging.warning(f"No data found for round {current_round}")
    return []


def scrape_and_append(match_id, team_name, team_path):
    """Scrape match data and append to team's Excel file."""
    try:
        # Fetch data from Sofascore
        logging.info(f"Fetching match data for ID {match_id}, team: {team_name}")
        event = fetch_event(match_id)
        lineups = fetch_lineups(match_id)
        stats = fetch_stats(match_id)
        stats_dict = parse_team_stats(stats)
        
        home = event["event"]["homeTeam"]["name"]
        away = event["event"]["awayTeam"]["name"]
        logging.info(f"Match: {home} vs {away}")
        
        # Build row
        row = build_row(event, lineups, stats_dict, team_name)
        
        # Load existing Excel or create new
        if team_path.exists():
            df_old = pd.read_excel(team_path)
        else:
            logging.warning(f"File not found: {team_path}, creating new")
            df_old = None
        
        # Define column order
        base = ["Team1", "Team2", "Team1H_A", "Team1Formation", "Team2Formation", "Win(3)_Draw(1)_Lose(0)"]
        t1_names = [f"Team1Player{i}Name" for i in range(1, 12)]
        t2_names = [f"Team2Player{i}Name" for i in range(1, 12)]
        t1_rates = [f"Team1Player{i}" for i in range(1, 12)]
        t2_rates = [f"Team2Player{i}" for i in range(1, 12)]
        goals = ["Team1_Goals", "Team2_Goals"]
        stats_cols = [
            "Team1_BigChances", "Team1_TotalShots", "Team1_Corners", "Team1_Passes", "Team1_Tackels",
            "Team1_FreeKicks", "Team1_BallPosses",
            "Team2_BigChances", "Team2_TotalShots", "Team2_Corners", "Team2_Passes", "Team2_Tackels",
            "Team2_FreeKicks", "Team2_BallPosses"
        ]
        col_order = base + t1_names + t2_names + t1_rates + t2_rates + goals + stats_cols
        
        # Create new dataframe
        df_new = pd.DataFrame([row])
        for c in col_order:
            if c not in df_new.columns:
                df_new[c] = None
        df_new = df_new[col_order]
        
        # Type conversions
        for c in t1_rates + t2_rates:
            df_new[c] = pd.to_numeric(df_new[c], errors="coerce")
        
        int_cols = [
            "Team1_Goals", "Team2_Goals",
            "Team1_BigChances", "Team1_TotalShots", "Team1_Corners", "Team1_Passes", "Team1_Tackels", "Team1_FreeKicks",
            "Team2_BigChances", "Team2_TotalShots", "Team2_Corners", "Team2_Passes", "Team2_Tackels", "Team2_FreeKicks",
        ]
        for c in int_cols:
            df_new[c] = pd.to_numeric(df_new[c], errors="coerce").astype("Int64")
        
        for c in ["Team1_BallPosses", "Team2_BallPosses"]:
            df_new[c] = df_new[c].astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False)
            df_new[c] = pd.to_numeric(df_new[c], errors="coerce") / 100
        
        # Merge with existing
        if df_old is not None:
            for c in df_new.columns:
                if c not in df_old.columns:
                    df_old[c] = None
            for c in df_old.columns:
                if c not in df_new.columns:
                    df_new[c] = None
            df_old = df_old[df_new.columns]
            df_combined = pd.concat([df_new, df_old], ignore_index=True)
        else:
            df_combined = df_new
        
        # Save
        df_combined.to_excel(team_path, index=False)
        csv_path = team_path.with_suffix('.csv')
        df_combined.to_csv(csv_path, index=False)
        
        logging.info(f"✅ Updated {team_path.name}")
        return True
        
    except SofaScoreChallengeError as e:
        logging.error(f"❌ Cloudflare challenge detected: {e}")
        return False
    except Exception as e:
        logging.error(f"❌ Error processing {team_name}: {e}", exc_info=True)
        return False


def main():
    """Main automation logic."""
    logging.info("=" * 60)
    logging.info("Starting Automated Weekly Scraper")
    logging.info("=" * 60)
    
    # Load schedule
    schedule = load_schedule()
    matches = get_current_round_matches(schedule)
    
    if not matches:
        logging.warning("No matches to process. Exiting.")
        return
    
    # Track processed matches to avoid duplicates
    processed = set()
    success_count = 0
    fail_count = 0
    
    for match in matches:
        match_id = match['match_id']
        home_team = match['home_team']
        away_team = match['away_team']
        
        # Process both teams
        for team_name in [home_team, away_team]:
            if team_name not in TEAM_PATHS:
                logging.warning(f"⚠️  No path mapping for team: {team_name}")
                continue
            
            # Create unique key to avoid processing same match+team twice
            key = f"{match_id}_{team_name}"
            if key in processed:
                continue
            
            team_path = TEAM_PATHS[team_name]
            
            # Scrape and append
            success = scrape_and_append(match_id, team_name, team_path)
            processed.add(key)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # Polite delay between requests
            time.sleep(1.5)
    
    logging.info("=" * 60)
    logging.info(f"Scraping complete!")
    logging.info(f"✅ Success: {success_count}")
    logging.info(f"❌ Failed: {fail_count}")
    logging.info("=" * 60)


if __name__ == "__main__":
    main()
