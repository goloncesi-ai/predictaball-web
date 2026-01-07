#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import json
import time
import os
import pandas as pd
import requests
import unicodedata
from datetime import datetime, timezone

API_BASE = "https://api.sofascore.com/api/v1"
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/"
})

# ---------------- HTTP / API ----------------
def get_json(url, retries=3, backoff=1.3):
    last = None
    for i in range(retries):
        r = SESSION.get(url, timeout=25)
        if r.ok:
            return r.json()
        last = (r.status_code, r.text[:800])
        time.sleep(backoff**i)
    code, body = last or ("?", "?")
    raise RuntimeError(f"API error {url} [{code}]: {body}")

def parse_event_id(s):
    s = str(s).strip()
    m = re.search(r"(?:#id:|/event/)(\d{6,})", s)
    if m: return int(m.group(1))
    m = re.search(r"(\d{6,})", s)
    if m: return int(m.group(1))
    raise ValueError(f"Could not detect event ID in: {s}")

def fetch_event(eid):   return get_json(f"{API_BASE}/event/{eid}")
def fetch_lineups(eid): return get_json(f"{API_BASE}/event/{eid}/lineups")

def fetch_stats(eid):
    url = f"{API_BASE}/event/{eid}/statistics"
    try:
        return get_json(url)
    except RuntimeError as e:
        msg = str(e)
        if "/statistics" in msg and "[404]" in msg:
            print("… no statistics available (404) — continuing without team stats.")
            return {}  # proceed without stats
        raise

# --------------- Normalization ---------------
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
def norm(s): return re.sub(r"\s+", " ", (s or "").strip().lower())
def canonical(s): return STAT_ALIASES.get(norm(s), s)

def classify_position(val):
    if val is None: return "OTH"
    v = str(val).upper()
    if v in {"G","GK","GOALKEEPER","1"}: return "GK"
    if v in {"D","DEF","DEFENDER","2"}:  return "DEF"
    if v in {"M","MID","MIDFIELDER","3"}:return "MID"
    if v in {"F","FW","FORWARD","4"}:     return "FWD"
    return "OTH"

# --------------- Parse stats ---------------
def parse_team_stats(js):
    rows=[]
    def maybe_add(d):
        if not isinstance(d, dict): return
        name = d.get("name") or d.get("title") or d.get("key")
        if not name or norm(name) not in WANTED_KEYS: return
        hv = d.get("home") or d.get("homeValue") or d.get("valueHome") or d.get("homeTotal") or d.get("homeTotalValue")
        av = d.get("away") or d.get("awayValue") or d.get("valueAway") or d.get("awayTotal") or d.get("awayTotalValue")
        if hv is None and av is None: return
        rows.append((canonical(name), hv, av))

    stack=[js]; seen=set()
    while stack:
        o = stack.pop()
        if id(o) in seen: continue
        seen.add(id(o))
        if isinstance(o, dict):
            maybe_add(o)
            for v in o.values():
                if isinstance(v,(dict,list)): stack.append(v)
        elif isinstance(o, list):
            for v in o:
                if isinstance(v,(dict,list)): stack.append(v)

    return {name:(hv,av) for name,hv,av in rows}

# --------------- Starters extraction ---------------
def starters_for_side(side):
    if isinstance(side.get("startingLineups"), list) and side["startingLineups"]:
        return side["startingLineups"][:11]
    out=[]
    for p in side.get("players", []):
        if p.get("substitute") in (False, None, 0, "false", "False"):
            out.append(p)
    return out[:11]

def unwrap_player(p):
    if isinstance(p, dict) and isinstance(p.get("player"), dict):
        return p["player"], p
    return p, p

def ordered_names_and_ratings(lineups_json, side_key):
    side=lineups_json.get(side_key,{})
    starters=starters_for_side(side)
    rec=[]
    for p in starters:
        player,cont=unwrap_player(p)
        pos = cont.get("position") or (player or {}).get("position")
        rt  = (cont.get("rating")
               or cont.get("sofifaRating")
               or (cont.get("statistics") or {}).get("rating")
               or (player or {}).get("rating"))
        if isinstance(rt, dict): rt = rt.get("rating")
        if isinstance(rt,str):
            try: rt=float(rt)
            except: pass
        rec.append({"name":(player or {}).get("name"),"rating":rt,"pos":classify_position(pos)})

    order=["GK","DEF","MID","FWD"]
    names,rates=[],[]
    for o in order:
        for r in rec:
            if r["pos"]==o:
                names.append(r["name"]); rates.append(r["rating"])
    for r in rec:
        if r["pos"] not in order:
            names.append(r["name"]); rates.append(r["rating"])
    while len(names)<11:
        names.append(None); rates.append(None)
    return names[:11], rates[:11]

# --------------- Season helper ---------------
def season_from_timestamp(ts):
    """
    Soccer season label from UTC timestamp (seconds).
    If month >= July -> season 'YYYY-YYYY+1', else previous season 'YYYY-1-YYYY'.
    """
    dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
    y = dt.year
    if dt.month >= 7:
        return f"{y}-{y+1}"
    else:
        return f"{y-1}-{y}"

# --------------- Build one row ---------------
def build_row(event, lineups, stats_dict, team1_name):
    evt = event["event"]
    home = evt["homeTeam"]["name"]
    away = evt["awayTeam"]["name"]

    if team1_name == home:
        t1_side, t2_side, team2_name, t1_HA = "home","away",away,"H"
    elif team1_name == away:
        t1_side, t2_side, team2_name, t1_HA = "away","home",home,"A"
    else:
        raise ValueError(f"Team1 '{team1_name}' not in {home} vs {away}")

    t1_form = lineups.get(t1_side,{}).get("formation")
    t2_form = lineups.get(t2_side,{}).get("formation")

    t1_names, t1_rates = ordered_names_and_ratings(lineups, t1_side)
    t2_names, t2_rates = ordered_names_and_ratings(lineups, t2_side)

    def score(side):
        sc = evt.get(f"{side}Score") or {}
        return sc.get("current", sc.get("display"))

    t1g, t2g = score(t1_side), score(t2_side)
    points = 3 if t1g>t2g else (1 if t1g==t2g else 0)

    def stat(label, side):
        hv,av = stats_dict.get(label,(None,None))
        return hv if side=="home" else av

    row={
        "Team1": team1_name,
        "Team2": team2_name,
        "Team1H_A": t1_HA,
        "Team1Formation": t1_form,
        "Team2Formation": t2_form,
        "Win(3)_Draw(1)_Lose(0)": points,
    }

    # Names (with Name suffix)
    for i in range(1,12):
        row[f"Team1Player{i}Name"] = t1_names[i-1]
    for i in range(1,12):
        row[f"Team2Player{i}Name"] = t2_names[i-1]

    # Ratings (without Name suffix)
    for i in range(1,12):
        row[f"Team1Player{i}"] = t1_rates[i-1]
    for i in range(1,12):
        row[f"Team2Player{i}"] = t2_rates[i-1]

    row["Team1_Goals"]=t1g
    row["Team2_Goals"]=t2g

    labels=[
        ("Big chances","BigChances"),
        ("Total shots","TotalShots"),
        ("Corner kicks","Corners"),
        ("Passes","Passes"),
        ("Tackles","Tackels"),
        ("Free kicks","FreeKicks"),
        ("Ball possession","BallPosses"),
    ]
    for api,suf in labels:
        row[f"Team1_{suf}"]=stat(api,t1_side)
        row[f"Team2_{suf}"]=stat(api,t2_side)

    # return row + the event timestamp (for season pathing)
    return row, evt.get("startTimestamp")

# ---------------------- BULK MODE ------------------------
def safe_filename(name: str) -> str:
    """Allow Unicode (Türkçe OK) but remove path separators and control chars."""
    name = unicodedata.normalize("NFC", str(name)).strip()
    name = name.replace("/", "_").replace("\\", "_").replace(":", "_")
    name = "".join(ch for ch in name if ch not in {'\0', '\n', '\r', '\t'})
    return name

def main():
    print("Bulk SofaScore scraper — Excel input, auto season folder + <TEAM>_Games_Input")

    # ---- Ask for path ----
    infile = input("Path to Excel file containing the 'Link' column: ").strip()

    # ---- PATH CLEANING (safe) ----
    infile = infile.strip().strip("'").strip('"')          # remove wrapping quotes
    infile = os.path.expanduser(infile)                    # expand ~
    infile = re.sub(r"\\([ \(\)\[\]\{\}])", r"\1", infile) # unescape common drag&drop backslashes
    infile = unicodedata.normalize("NFC", infile)          # keep Turkish letters intact
    infile = os.path.normpath(infile)

    # ---- Validate file existence ----
    if not os.path.isfile(infile):
        print(f"\n❌ ERROR: File not found:\n{infile}\n")
        print("Tip: drag & drop the file into Terminal (no quotes), or remove quotes if you pasted with quotes.")
        sys.exit(1)

    # ---- Read Excel ----
    df_links = pd.read_excel(infile)
    if "Link" not in df_links.columns:
        raise ValueError("Your Excel must contain a column named 'Link'.")

    TEAM1 = input("Which team is always Team1 in these matches? ").strip()

    out_rows = []
    seasons_seen = set()

    # ---- Process each link ----
    for idx, row in df_links.iterrows():
        link = row["Link"]
        print(f"\nProcessing row {idx+1}: {link}")

        try:
            event_id = parse_event_id(link)
            event   = fetch_event(event_id)
            lineups = fetch_lineups(event_id)
            stats   = fetch_stats(event_id)
            stats_d = parse_team_stats(stats)
            if not stats_d:
                print("   (info) Team stats missing for this match.")

            out_row, start_ts = build_row(event, lineups, stats_d, TEAM1)
            out_rows.append(out_row)

            if start_ts:
                seasons_seen.add(season_from_timestamp(start_ts))

            print("✓ OK")

        except Exception as e:
            print("✗ ERROR:", e)

    if not out_rows:
        print("No valid matches processed.")
        return

    # ----- Column order identical to your format -----
    base = ["Team1","Team2","Team1H_A","Team1Formation","Team2Formation","Win(3)_Draw(1)_Lose(0)"]
    t1_names=[f"Team1Player{i}Name" for i in range(1,12)]
    t2_names=[f"Team2Player{i}Name" for i in range(1,12)]
    t1_rates=[f"Team1Player{i}"     for i in range(1,12)]
    t2_rates=[f"Team2Player{i}"     for i in range(1,12)]
    goals=["Team1_Goals","Team2_Goals"]
    stats_cols=[
        "Team1_BigChances","Team1_TotalShots","Team1_Corners","Team1_Passes","Team1_Tackels","Team1_FreeKicks","Team1_BallPosses",
        "Team2_BigChances","Team2_TotalShots","Team2_Corners","Team2_Passes","Team2_Tackels","Team2_FreeKicks","Team2_BallPosses"
    ]
    col_order = base + t1_names + t2_names + t1_rates + t2_rates + goals + stats_cols

    df = pd.DataFrame(out_rows)
    for c in col_order:
        if c not in df.columns: df[c]=None
    df = df[col_order]

    # ---- Clean types ----
    # Ratings → float
    for c in t1_rates + t2_rates:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # Integer stats
    int_cols = [
        "Team1_Goals","Team2_Goals",
        "Team1_BigChances","Team1_TotalShots","Team1_Corners","Team1_Passes","Team1_Tackels","Team1_FreeKicks",
        "Team2_BigChances","Team2_TotalShots","Team2_Corners","Team2_Passes","Team2_Tackels","Team2_FreeKicks",
    ]
    for c in int_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")

    # Possession "%xx" or "xx,yy" → 0.xx
    for c in ["Team1_BallPosses","Team2_BallPosses"]:
        df[c] = df[c].astype(str).str.replace("%","",regex=False)
        df[c] = df[c].str.replace(",",".",regex=False)
        df[c] = pd.to_numeric(df[c], errors="coerce")/100

    # ---- Smart output path (Option C + season subfolder + TEAM_Games_Input) ----
    input_dir = os.path.dirname(os.path.abspath(infile))

    if len(seasons_seen) == 1:
        season_folder = list(seasons_seen)[0]
    else:
        season_folder = "mixed-seasons"

    output_dir = os.path.join(input_dir, season_folder)
    os.makedirs(output_dir, exist_ok=True)

    team_for_filename = safe_filename(TEAM1)
    fname_base = f"{team_for_filename}_Games_Input"

    xlsx_path  = os.path.join(output_dir, fname_base + ".xlsx")
    csv_path   = os.path.join(output_dir, fname_base + ".csv")

    df.to_excel(xlsx_path, index=False)
    df.to_csv(csv_path, index=False)

    print("\n✅ Bulk scrape complete!")
    print("Saved:")
    print(xlsx_path)
    print(csv_path)

if __name__ == "__main__":
    main()