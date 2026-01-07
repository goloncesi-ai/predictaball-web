#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re
import sys
import time
import json
import os
import random
import pandas as pd
import requests
import unicodedata

API_BASE = "https://api.sofascore.com/api/v1"

# Reusable HTTP session
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/"
})

# Reusable HTTP session
SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/"
})

class SofaScoreChallengeError(RuntimeError):
    """Raised when SofaScore returns a Cloudflare/anti-bot challenge (HTTP 403)."""


def _is_challenge(resp):
    try:
        if resp is None:
            return False
        if int(getattr(resp, "status_code", 0)) != 403:
            return False
        txt = (getattr(resp, "text", "") or "")
        return '"reason": "challenge"' in txt or "challenge" in txt.lower() or "cloudflare" in txt.lower()
    except Exception:
        return False


MIN_DELAY_SEC = 0.8
JITTER_SEC = 0.8


def _polite_sleep():
    time.sleep(MIN_DELAY_SEC + random.random() * JITTER_SEC)

# ---------------- HTTP / API ----------------
def get_json(url, retries=3, backoff=1.3):
    last = None
    for i in range(retries):
        _polite_sleep()
        r = SESSION.get(url, timeout=25)
        print("DEBUG:", url, "→", r.status_code)
        if not r.ok:
            print("DEBUG body:", r.text[:300])

        # Cloudflare / anti-bot challenge: do NOT retry (it will just keep failing)
        if _is_challenge(r):
            raise SofaScoreChallengeError(
                "SofaScore returned a 403 'challenge' (Cloudflare anti-bot). "
                "This is temporary and cannot be fixed by retries. "
                "Wait 15–60+ minutes, open sofascore.com in a normal browser on the same network, "
                "or switch network (e.g., phone hotspot), then rerun."
            )

        if r.ok:
            return r.json()

        last = (r.status_code, r.text[:800])
        time.sleep(backoff**i)

    code, body = last or ("?", "?")
    raise RuntimeError(f"Request failed {url} [{code}]: {body}")

def parse_event_id(s):
    s = s.strip()
    m = re.search(r"(?:#id:|/event/)(\d{6,})", s)
    if m: return int(m.group(1))
    m = re.search(r"(\d{6,})", s)
    if m: return int(m.group(1))
    raise ValueError("Could not detect SofaScore event ID")

def fetch_event(eid):   return get_json(f"{API_BASE}/event/{eid}")
def fetch_lineups(eid): return get_json(f"{API_BASE}/event/{eid}/lineups")

def fetch_stats(eid):
    url = f"{API_BASE}/event/{eid}/statistics"
    try:
        return get_json(url)
    except RuntimeError as e:
        msg = str(e)
        if "/statistics" in msg and "[404]" in msg:
            print("… no statistics available (404) — continuing without stats.")
            return {}
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

# --------------- Parse team stats ---------------
def parse_team_stats(js):
    rows=[]
    def maybe_add(d):
        if not isinstance(d, dict): return
        name = d.get("name") or d.get("title") or d.get("key")
        if not name or norm(name) not in WANTED_KEYS: return
        hv = d.get("home") or d.get("homeValue") or d.get("valueHome") \
             or d.get("homeTotal") or d.get("homeTotalValue")
        av = d.get("away") or d.get("awayValue") or d.get("valueAway") \
             or d.get("awayTotal") or d.get("awayTotalValue")
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
        if p.get("substitute") in (False, None,0, "false","False"):
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
        raise ValueError(f"Team1 '{team1_name}' not in match ({home} vs {away})")

    t1_form = lineups.get(t1_side,{}).get("formation")
    t2_form = lineups.get(t2_side,{}).get("formation")

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
    for i in range(1,12): row[f"Team1Player{i}Name"]=t1_names[i-1]
    for i in range(1,12): row[f"Team2Player{i}Name"]=t2_names[i-1]

    # Ratings
    for i in range(1,12): row[f"Team1Player{i}"]=t1_rates[i-1]
    for i in range(1,12): row[f"Team2Player{i}"]=t2_rates[i-1]

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

    return row

# helper
def safe_filename(s):
    s=str(s).strip()
    s=s.replace("/","_").replace("\\","_").replace(":","_")
    return "".join(ch for ch in s if ch not in {"\0","\n","\r","\t"})

# --------------- Main loop ---------------
def run_loop():
    print("SofaScore → Single-Game Scraper (append to existing master file at TOP, auto Team1)")

    # ---- ask for PATH to existing master file ----
    infile = input("\nPath to your existing TEAM_Games_Input.xlsx file: ").strip()

    # PATH CLEANING
    infile = infile.strip().strip("'").strip('"')
    infile = os.path.expanduser(infile)
    infile = unicodedata.normalize("NFC", infile)
    infile = os.path.normpath(infile)

    if not os.path.isfile(infile):
        print(f"\n❌ File not found:\n{infile}")
        return

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
            # most frequent value in Team1 column
            team1_auto = non_null.mode().iloc[0]

    if team1_auto is None:
        base_name = os.path.splitext(os.path.basename(infile))[0]
        m = re.match(r"(.+)_Games_Input$", base_name)
        if m:
            team1_auto = m.group(1)
        else:
            team1_auto = base_name

    print(f"\nAuto-detected Team1: {team1_auto}")

    rows=[]

    # ---- scrape loop ----
    while True:
        s = input("\nPaste SofaScore URL/ID (or 'done'): ").strip()
        if s.lower() in {"done","exit","quit"}:
            break

        try:
            eid=parse_event_id(s)
            event   = fetch_event(eid)
            lineups = fetch_lineups(eid)
            stats   = fetch_stats(eid)
            stats_d = parse_team_stats(stats)

            h=event["event"]["homeTeam"]["name"]
            a=event["event"]["awayTeam"]["name"]
            print(f"Detected: {h} vs {a}")

            if team1_auto not in {h,a}:
                print(f"[WARN] Auto Team1 '{team1_auto}' is not in this match ({h} vs {a}). Skipping.")
                continue

            row = build_row(event, lineups, stats_d, team1_auto)
            rows.append(row)
            print("→ Row added.")

        except SofaScoreChallengeError as e:
            print("\n✗ BLOCKED:", e)
            print("\nTip: Stop the script and retry later after the challenge clears.")
            return
        except Exception as e:
            print("[ERROR]", e)

    if not rows:
        print("No new rows. Exiting.")
        return

    # ---- NEW rows DataFrame ----
    base = ["Team1","Team2","Team1H_A","Team1Formation","Team2Formation","Win(3)_Draw(1)_Lose(0)"]
    t1_names=[f"Team1Player{i}Name" for i in range(1,12)]
    t2_names=[f"Team2Player{i}Name" for i in range(1,12)]
    t1_rates=[f"Team1Player{i}" for i in range(1,12)]
    t2_rates=[f"Team2Player{i}" for i in range(1,12)]
    goals=["Team1_Goals","Team2_Goals"]
    stats_cols=[
        "Team1_BigChances","Team1_TotalShots","Team1_Corners","Team1_Passes","Team1_Tackels",
        "Team1_FreeKicks","Team1_BallPosses",
        "Team2_BigChances","Team2_TotalShots","Team2_Corners","Team2_Passes","Team2_Tackels",
        "Team2_FreeKicks","Team2_BallPosses"
    ]
    col_order = base + t1_names + t2_names + t1_rates + t2_rates + goals + stats_cols

    df_new=pd.DataFrame(rows)
    for c in col_order:
        if c not in df_new.columns:
            df_new[c]=None
    df_new=df_new[col_order]

    # type fix on new rows
    for c in t1_rates + t2_rates:
        df_new[c]=pd.to_numeric(df_new[c], errors="coerce")

    int_cols=[
        "Team1_Goals","Team2_Goals",
        "Team1_BigChances","Team1_TotalShots","Team1_Corners","Team1_Passes",
        "Team1_Tackels","Team1_FreeKicks",
        "Team2_BigChances","Team2_TotalShots","Team2_Corners","Team2_Passes",
        "Team2_Tackels","Team2_FreeKicks",
    ]
    for c in int_cols:
        df_new[c]=pd.to_numeric(df_new[c], errors="coerce").astype("Int64")

    for c in ["Team1_BallPosses","Team2_BallPosses"]:
        df_new[c]=df_new[c].astype(str).str.replace("%","",regex=False)
        df_new[c]=df_new[c].str.replace(",",".",regex=False)
        df_new[c]=pd.to_numeric(df_new[c], errors="coerce")/100

    # ---- merge with existing (prepend new rows) ----
    if df_old is not None:
        # align columns
        for c in df_new.columns:
            if c not in df_old.columns:
                df_old[c]=None
        for c in df_old.columns:
            if c not in df_new.columns:
                df_new[c]=None

        df_old=df_old[df_new.columns]
        df_combined=pd.concat([df_new, df_old], ignore_index=True)
        print("\nExisting file found → prepending new rows.")
    else:
        df_combined=df_new
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