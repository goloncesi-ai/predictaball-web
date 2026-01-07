#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
SofaScore — Player Detail (Stable Season Stats Only)

Modes:
1) Single player:
   - Input: SofaScore player URL or numeric player id
   - Output: ONE Excel file with sheets:
       • Profile (1 row)
       • Season_Summary (1 row)
       • Stats (1 row, wide)

2) Team bulk (team → all players):
   - Input: SofaScore team URL (e.g., /team/.../3052) or team id
   - Automatically fetches the team's current squad list
   - Runs the same per-player scraping pipeline for every player
   - Output: ONE Excel file for the team with sheets:
       • Profile (N rows)
       • Season_Summary (N rows)
       • Stats (N rows, wide)
"""
class ChallengeBlocked(RuntimeError):
    """Raised when SofaScore API returns a Cloudflare/anti-bot challenge (HTTP 403)."""
    pass

def _is_cf_challenge(status_code, body_text):
    try:
        if int(status_code) != 403:
            return False
    except Exception:
        return False
    bt = (body_text or "").lower()
    return "challenge" in bt or "cloudflare" in bt

# -------------------- TEAM ID parsing and fetchers --------------------
def parse_team_id(s):
    s = str(s).strip()
    m = re.search(r"/team/[^/]+/(\d+)", s)
    if m:
        return int(m.group(1))
    # if user pastes just a numeric id
    if s.isdigit():
        return int(s)
    raise ValueError("Could not detect team id")

def fetch_team(team_id):
    return get_json(f"{API_BASE}/team/{team_id}")

def fetch_team_players(team_id):
    """
    Fetch team squad list.
    Primary endpoint: /team/{id}/players
    Returns a list of player dicts (best-effort normalized).
    """
    candidates = [
        f"{API_BASE}/team/{team_id}/players",
        f"{API_BASE}/team/{team_id}/squad",
        f"{API_BASE}/team/{team_id}",
    ]
    last_err = None
    for url in candidates:
        try:
            js = get_json_optional(url)
            if not js:
                continue

            # common shapes:
            # { "players": [ ... ] }
            # { "team": {...}, "players": [...] }
            # { "squad": { "players": [...] } }
            # { "teamPlayers": [...] }
            for key in ("players", "teamPlayers"):
                if isinstance(js.get(key), list) and js.get(key):
                    return js.get(key)

            squad = js.get("squad")
            if isinstance(squad, dict) and isinstance(squad.get("players"), list) and squad.get("players"):
                return squad.get("players")

            # sometimes /team/{id} returns { "team": {...}, "players": [...] }
            team = js.get("team")
            if isinstance(team, dict):
                for key in ("players", "teamPlayers"):
                    if isinstance(team.get(key), list) and team.get(key):
                        return team.get(key)

        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise RuntimeError(f"Could not fetch team players: {last_err}")
    raise RuntimeError("Could not fetch team players (no usable payload).")

def normalize_team_player_entry(x):
    """
    Normalize a team players list entry to a (player_id, player_name) pair.
    Entries can look like:
      - { "player": { "id": ..., "name": ... }, ... }
      - { "id": ..., "name": ... }
    """
    if not isinstance(x, dict):
        return None, None

    if isinstance(x.get("player"), dict):
        p = x["player"]
        return p.get("id"), p.get("name")

    return x.get("id"), x.get("name")
def parse_unique_tournament_id(s):
    s = str(s).strip()
    # supports:
    #  - /unique-tournament/<slug>/<id>
    #  - /tournament/<sport>/<country>/<slug>/<id>
    m = re.search(r"/unique-tournament/[^/]+/(\d+)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"/tournament/.+/(\d+)(?:[#/?]|$)", s)
    if m:
        return int(m.group(1))
    # if user pastes just a numeric id
    if s.isdigit():
        return int(s)
    raise ValueError("Could not detect unique tournament id")

def parse_season_id_from_url(s):
    """Extract season id from a SofaScore URL fragment like '#id:77805'."""
    s = str(s)
    m = re.search(r"#id:(\d+)", s)
    if m:
        return int(m.group(1))
    return None

def fetch_unique_tournament(tournament_uid):
    return get_json(f"{API_BASE}/unique-tournament/{tournament_uid}")

def fetch_standings_team_ids(unique_tournament_id, season_id):
    """
    Return [(team_id, team_name), ...] in standings order (best-effort).
    Tries multiple endpoints because SofaScore can vary by competition.
    """
    urls = [
        f"{API_BASE}/unique-tournament/{unique_tournament_id}/season/{season_id}/standings/total",
        f"{API_BASE}/unique-tournament/{unique_tournament_id}/season/{season_id}/standings",
        f"{API_BASE}/unique-tournament/{unique_tournament_id}/standings/total",
        f"{API_BASE}/unique-tournament/{unique_tournament_id}/standings",
    ]

    def extract(js):
        teams = []
        if not isinstance(js, dict):
            return teams

        standings = js.get("standings")
        if isinstance(standings, list):
            for st in standings:
                rows = st.get("rows")
                if isinstance(rows, list):
                    for r in rows:
                        team = r.get("team")
                        if isinstance(team, dict) and team.get("id"):
                            teams.append((int(team["id"]), team.get("name")))
        return teams

    last_err = None
    for url in urls:
        try:
            js = get_json_optional(url)
            if not js:
                continue
            teams = extract(js)
            if teams:
                # de-dup preserve order
                seen = set()
                out = []
                for tid, name in teams:
                    if tid not in seen:
                        seen.add(tid)
                        out.append((tid, name))
                return out
        except Exception as e:
            last_err = e
            continue

    if last_err:
        raise RuntimeError(f"Could not fetch standings: {last_err}")
    raise RuntimeError("Could not fetch standings teams (no usable payload).")
# -------------------- Per-player scraping helper --------------------
def scrape_one_player(player_id, tournament_id, season_id):
    """
    Run the existing pipeline for ONE player and return:
      (profile_row_df, summary_row_df, stats_row_df, player_name)
    Any per-player exceptions should be raised to caller.
    """
    profile_json = fetch_player_profile(player_id)
    stats_payload = fetch_season_stats(player_id, tournament_id, season_id)

    avg12, month_map = last_12_month_avg_ratings(player_id)

    p = profile_json.get("player", {})

    dob_iso = ts_to_date_str(p.get("dateOfBirthTimestamp"))
    age_val = p.get("age")
    if age_val is None or age_val == "":
        age_val = age_from_date_str(dob_iso)

    # Position can be generic ("M") in some payloads. Prefer any non-generic set like "ST, RW, AM".
    pos_candidates = [
        extract_positions((stats_payload.get("overall") or {}).get("statistics", {})),
        extract_positions(stats_payload.get("overall") or {}),
        extract_positions(p),
    ]

    def _is_generic_pos(s):
        if not s:
            return True
        toks = [t.strip().upper() for t in str(s).split(",") if t.strip()]
        return bool(toks) and all(t in {"D", "M", "F"} for t in toks)

    positions_str = None
    for cand in pos_candidates:
        if cand and not _is_generic_pos(cand):
            positions_str = cand
            break
    if positions_str is None:
        for cand in pos_candidates:
            if cand:
                positions_str = cand
                break

    profile_row = {
        "Name": p.get("name"),
        "Age": age_val,
        "DateOfBirth": dob_iso,
        "Height_cm": p.get("height"),
        "PreferredFoot": p.get("preferredFoot"),
        "Position": positions_str,
        "ShirtNumber": p.get("shirtNumber"),
        "Nationality": (p.get("country") or {}).get("name"),
        "Team": (p.get("team") or {}).get("name"),
    }
    df_profile = pd.DataFrame([profile_row])

    overall_stats = (stats_payload.get("overall") or {})
    summary = overall_stats.get("statistics", {})
    if not isinstance(summary, dict):
        summary = {}

    summary_row = {
        "Name": p.get("name"),
        "Appearances": summary.get("appearances", summary.get("matches")),
        "MinutesPlayed": summary.get("minutesPlayed"),
        "Rating": summary.get("rating"),
        "Goals": summary.get("goals"),
        "Assists": summary.get("assists"),
        "YellowCards": summary.get("yellowCards"),
        "RedCards": summary.get("redCards"),
        "AvgRating_Last12Months": avg12,
    }
    for mk, val in month_map.items():
        summary_row[f"AvgRating_{mk}"] = val

    df_summary = pd.DataFrame([summary_row])

    df_stats = build_stats_tab(stats_payload)
    df_stats["Name"] = p.get("name")

    return df_profile, df_summary, df_stats, p.get("name")

import re
import os
import time
import requests
import pandas as pd
from datetime import datetime, timezone, date


API_BASE = "https://api.sofascore.com/api/v1"

# Fast default season ids (avoid calling /seasons which can trigger/require challenge)
DEFAULT_SEASON_BY_TOURNAMENT = {
    52: 77805,  # Trendyol Süper Lig 2025/26 (update if SofaScore changes)
}

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/",
})

# -------------------- HTTP --------------------
def get_json(url, retries=3, backoff=1.3):
    last = None
    for i in range(retries):
        r = SESSION.get(url, timeout=25)
        if r.ok:
            return r.json()
        last = (r.status_code, r.text[:500])
        time.sleep(backoff ** i)
    code, body = last or ("?", "?")
    if _is_cf_challenge(code, body):
        raise ChallengeBlocked(f"API blocked by challenge at {url} [{code}]: {body}")
    raise RuntimeError(f"API error {url} [{code}]: {body}")

def get_json_optional(url, retries=2, backoff=1.3):
    """
    Fetch JSON but return None on 404. Raise on other errors.
    """
    last = None
    for i in range(retries):
        r = SESSION.get(url, timeout=25)
        if r.ok:
            return r.json()
        last = (r.status_code, r.text[:500])
        # treat 404 as optional-missing endpoint
        if r.status_code == 404:
            return None
        time.sleep(backoff ** i)
    code, body = last or ("?", "?")
    if _is_cf_challenge(code, body):
        raise ChallengeBlocked(f"API blocked by challenge at {url} [{code}]: {body}")
    raise RuntimeError(f"API error {url} [{code}]: {body}")

def month_key_from_ts(ts):
    s = ts_to_date_str(ts)
    if not s:
        return None
    # YYYY-MM from YYYY-MM-DD
    return s[:7]

# -------------------- ID parsing --------------------
def parse_player_id(s):
    s = str(s).strip()
    m = re.search(r"/player/[^/]+/(\d+)", s)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)$", s)
    if m:
        return int(m.group(1))
    raise ValueError("Could not detect player id")

# -------------------- Season resolver --------------------
def resolve_season_id(tournament_id, sid_raw):
    sid_raw = sid_raw.strip()
    if sid_raw.isdigit():
        return int(sid_raw)

    wanted = sid_raw.replace(" ", "").replace("-", "/")

    seasons_url = f"{API_BASE}/unique-tournament/{tournament_id}/seasons"
    data = get_json(seasons_url)
    seasons = data.get("seasons", [])

    for s in seasons:
        text = " ".join(str(s.get(k)) for k in ["name", "year", "slug"] if s.get(k))
        norm = text.replace(" ", "").replace("-", "/")
        if wanted in norm:
            return int(s["id"])

    raise ValueError(
        f"Could not resolve season '{sid_raw}'. "
        "Please copy numeric season id from Sofascore URL."
    )

# -------------------- Fetchers --------------------
def fetch_player_profile(pid):
    return get_json(f"{API_BASE}/player/{pid}")

def fetch_season_stats(pid, tid, sid):
    """
    Fetch season statistics for a player.

    SofaScore exposes player season stats in multiple shapes. Some competitions
    return a compact 'overall' JSON, while the UI sections (Attacking/Passing/...)
    may come from `?group=` endpoints. We try multiple endpoints and merge them.

    Returns a single dict that contains any successful payloads under keys:
      - overall
      - groups (dict keyed by group name)
    and also keeps a top-level 'statistics' if present (for backward compat).
    """
    out = {"overall": None, "groups": {}}

    # 1) Primary overall endpoint (what we used before)
    url_overall = f"{API_BASE}/player/{pid}/unique-tournament/{tid}/season/{sid}/statistics/overall"
    js_overall = get_json_optional(url_overall)
    if js_overall:
        out["overall"] = js_overall
        # keep compatibility: expose statistics at top-level when present
        if isinstance(js_overall, dict) and "statistics" in js_overall:
            out["statistics"] = js_overall.get("statistics")

    # 2) Try group endpoints used by SofaScore tables (pattern used on tournament tables too)
    # We include extra groups; build_stats_tab will only pick what it needs.
    group_names = [
        "summary",
        "attack",
        "passing",
        "defending",
        "duels",
        "other",
        "cards",
    ]
    for g in group_names:
        url_g = (
            f"{API_BASE}/player/{pid}/unique-tournament/{tid}/season/{sid}/statistics"
            f"?accumulation=total&group={g}"
        )
        js_g = get_json_optional(url_g)
        if js_g:
            out["groups"][g] = js_g

    # 3) Some regions expose /statistics (no params) as a grouped payload
    url_plain = f"{API_BASE}/player/{pid}/unique-tournament/{tid}/season/{sid}/statistics"
    js_plain = get_json_optional(url_plain)
    if js_plain:
        out["groups"]["plain"] = js_plain

    # If nothing worked, raise a clearer error
    if out["overall"] is None and not out["groups"]:
        raise RuntimeError("No stats returned. Check tournament/season ids.")
    return out

def fetch_player_last_events_page(pid, page=0):
    """
    Try to fetch a page of the player's recent events.
    SofaScore commonly exposes: /player/{pid}/events/last/{page}
    Returns None if the endpoint is missing.
    """
    url = f"{API_BASE}/player/{pid}/events/last/{page}"
    return get_json_optional(url)



# ---- Per-event player statistics for fallback rating lookup ----
def fetch_event_player_stats(pid, event_id):
    """
    Fetch player stats for a specific event. Returns JSON or None if not found.
    SofaScore commonly exposes:
      /event/{event_id}/player/{player_id}/statistics
    """
    url_candidates = [
        f"{API_BASE}/event/{event_id}/player/{pid}/statistics",
        f"{API_BASE}/event/{event_id}/player/{pid}/statistics/overall",
    ]
    for url in url_candidates:
        js = get_json_optional(url)
        if js:
            return js
    return None

def extract_rating_from_player_stats(js):
    """
    Extract rating from an event-player statistics payload.
    Returns float or None.
    """
    if not js:
        return None
    # common shapes:
    # { "statistics": { "rating": 7.2, ... } }
    # { "player": {...}, "statistics": {...} }
    # { "rating": 7.2, ... }
    for root in (js, js.get("statistics") if isinstance(js, dict) else None):
        if not isinstance(root, dict):
            continue
        r = root.get("rating")
        if isinstance(r, dict):
            r = r.get("rating")
        try:
            if r is not None:
                rf = float(r)
                if 0.0 <= rf <= 10.0:
                    return rf
        except Exception:
            pass
    # fallback: recursive scan
    return extract_first_plausible_rating(js)

def extract_first_plausible_rating(obj):
    """
    Recursively scan a dict/list for a plausible player rating (0..10).
    We prefer rating fields under keys that look like player statistics.
    Returns float or None.
    """
    best = None

    def looks_like_rating(v):
        try:
            fv = float(v)
        except Exception:
            return None
        if 0.0 <= fv <= 10.0:
            return fv
        return None

    def walk(x, path=""):
        nonlocal best
        if best is not None:
            return
        if isinstance(x, dict):
            for k, v in x.items():
                lk = str(k).lower()
                new_path = f"{path}.{k}" if path else str(k)

                # prioritize obvious keys
                if lk in {"rating", "sofascore_rating", "sofascoreRating"}:
                    fv = looks_like_rating(v)
                    if fv is not None:
                        best = fv
                        return

                # if nested dict, continue
                if isinstance(v, (dict, list)):
                    walk(v, new_path)
                else:
                    # also accept numeric rating under statistic-like keys
                    if "rating" in lk:
                        fv = looks_like_rating(v)
                        if fv is not None:
                            best = fv
                            return

        elif isinstance(x, list):
            for it in x:
                walk(it, path)

    walk(obj)
    return best

def last_12_month_avg_ratings(player_id):
    """
    Fetch player's recent match events and compute:
    - overall average rating over last 12 months
    - monthly averages for the last 12 calendar months (including current month)
    Returns: (overall_avg, month_map) where month_map is { 'YYYY-MM': avg_float_or_None }
    """
    # build the last 12 months keys
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(12):
        months.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months = list(reversed(months))  # oldest -> newest

    cutoff_dt = datetime.now(tz=timezone.utc) - pd.Timedelta(days=365)
    cutoff_ts = int(cutoff_dt.timestamp())

    # collect ratings by month
    buckets = {mk: [] for mk in months}
    rating_cache = {}  # event_id -> rating or None

    # page through recent events until we go older than cutoff or no more data
    page = 0
    while True:
        data = fetch_player_last_events_page(player_id, page)
        if not data:
            break
        events = data.get("events") or data.get("results") or []
        if not isinstance(events, list) or not events:
            break

        stop = False
        for ev in events:
            ts = ev.get("startTimestamp") or ev.get("timestamp") or (ev.get("event") or {}).get("startTimestamp")
            if ts is None:
                continue
            try:
                ts_int = int(ts)
            except Exception:
                continue

            if ts_int < cutoff_ts:
                stop = True
                continue

            mk = month_key_from_ts(ts_int)
            if mk not in buckets:
                continue

            # 1) Try to find a rating inside the event payload (fast path)
            r = extract_first_plausible_rating(ev)

            # 2) If missing, fetch per-event player statistics (slower but reliable)
            if r is None:
                event_id = ev.get("id") or (ev.get("event") or {}).get("id")
                if event_id:
                    if event_id in rating_cache:
                        r = rating_cache[event_id]
                    else:
                        ps = fetch_event_player_stats(player_id, int(event_id))
                        r = extract_rating_from_player_stats(ps)
                        rating_cache[event_id] = r

            if r is not None:
                buckets[mk].append(float(r))

        if stop:
            break
        page += 1
        if page > 20:  # hard stop to avoid infinite loops
            break

    month_map = {}
    all_ratings = []
    for mk in months:
        vals = buckets.get(mk, [])
        if vals:
            avg = sum(vals) / len(vals)
            month_map[mk] = round(avg, 2)
            all_ratings.extend(vals)
        else:
            month_map[mk] = None

    # If everything is empty, the endpoints may not expose ratings for this player.
    # (We keep returning None values; caller will write blanks in Excel.)
    overall_avg = round(sum(all_ratings) / len(all_ratings), 2) if all_ratings else None
    return overall_avg, month_map




def ts_to_date_str(ts):
    """
    Convert SofaScore timestamps (seconds or milliseconds) to 'YYYY-MM-DD'.
    Returns None if ts is missing/invalid.
    """
    if ts is None:
        return None
    try:
        ts_int = int(ts)
    except (TypeError, ValueError):
        return None
    # heuristics: if ts looks like milliseconds, convert to seconds
    if ts_int > 10_000_000_000:
        ts_int = ts_int // 1000
    try:
        dt = datetime.fromtimestamp(ts_int, tz=timezone.utc).date()
        return dt.isoformat()
    except Exception:
        return None

def age_from_date_str(dob_iso):
    """
    Compute age in years from 'YYYY-MM-DD' using today's date (local).
    Returns None if dob_iso invalid.
    """
    if not dob_iso:
        return None
    try:
        y, m, d = map(int, dob_iso.split("-"))
        dob = date(y, m, d)
    except Exception:
        return None
    today = date.today()
    years = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return years

def extract_positions(p):
    """
    Extract ALL listed positions for the player from SofaScore player JSON.

    SofaScore payloads are not perfectly consistent across sports/contexts.
    This function:
      1) checks common fields (positions list, position object/string)
      2) scans the player dict recursively for position abbreviations (ST, RW, AM, etc.)

    Returns a comma-separated string like 'ST, RW, AM' when possible.
    Falls back to a single 'position' string if that's all we have.
    """
    # Common football position abbreviations you might see on SofaScore UI
    VALID = {
        "GK",
        "RB","RWB","CB","LB","LWB",
        "DM","CDM","CM","RM","LM",
        "AM","CAM","RW","LW",
        "ST","CF",
        # sometimes SofaScore uses these broader ones
        "D","M","F",
    }

    found = []

    def add_pos(x):
        if not x:
            return
        x = str(x).strip().upper()
        if x in VALID:
            found.append(x)

    # 1) Common pattern: p["positions"] is a list (strings or dicts)
    pos_list = p.get("positions")
    if isinstance(pos_list, list):
        for item in pos_list:
            if isinstance(item, str):
                add_pos(item)
            elif isinstance(item, dict):
                for k in ("shortName", "short", "abbr", "name", "position"):
                    v = item.get(k)
                    if isinstance(v, str):
                        add_pos(v)
                        break

    # 2) Another pattern: p["position"] may be dict or string
    pos_obj = p.get("position")
    if isinstance(pos_obj, dict):
        for k in ("shortName", "short", "abbr", "name"):
            v = pos_obj.get(k)
            if isinstance(v, str):
                add_pos(v)
                break
    else:
        add_pos(pos_obj)

    # 3) Recursive scan (handles cases like preferredPositions, playerPositions, etc.)
    def walk(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                # some keys are strong hints, so check their immediate values first
                if k.lower() in {"preferredpositions", "preferredposition", "playerpositions", "secondarypositions", "secondaryposition"}:
                    if isinstance(v, list):
                        for it in v:
                            if isinstance(it, str):
                                add_pos(it)
                            elif isinstance(it, dict):
                                for kk in ("shortName", "short", "abbr", "name", "position"):
                                    vv = it.get(kk)
                                    if isinstance(vv, str):
                                        add_pos(vv)
                                        break
                    elif isinstance(v, dict):
                        for kk in ("shortName", "short", "abbr", "name", "position"):
                            vv = v.get(kk)
                            if isinstance(vv, str):
                                add_pos(vv)
                                break
                    elif isinstance(v, str):
                        add_pos(v)

                # continue walking
                walk(v)
        elif isinstance(obj, list):
            for it in obj:
                walk(it)
        elif isinstance(obj, str):
            add_pos(obj)

    walk(p)

    # De-duplicate while preserving order
    seen = set()
    out = []
    for x in found:
        if x not in seen:
            seen.add(x)
            out.append(x)

    # If we found only 'M' but there are also specific positions elsewhere,
    # keep the more specific ones and drop the generic D/M/F.
    specific = [x for x in out if x not in {"D","M","F"}]
    if specific:
        out = specific

    # As a final fallback, return whatever we have (possibly "M")
    return ", ".join(out) if out else (str(p.get("position")).strip() if p.get("position") else None)



# -------------------- Stats (UI metrics with guaranteed fallback) --------------------
def build_stats_tab(stats_json):
    """
    Build the Stats sheet for the exact UI metrics requested.

    Strategy:
      1) Try to fill from UI-style grouped payloads (when present).
      2) If that fails for any row, fill from stable season summary fields.
         - Prefer explicit per-game fields when available
         - Else compute per-game from total / appearances
         - Build "X (Y%)" strings properly
    """
    wanted = {
        "Attacking": [
            "Goals",
            "Expected goals (xG)",
            "Scoring frequency (in minutes)",
            "Goals per game",
            "Total shots",
            "Shots on target per game",
            "Big chances missed",
            "Goal conversion",
            "Free kick goals",
            "Goals from inside the box",
            "Goals from outside the box",
            "Headed goals",
            "Left-footed goals",
            "Right-footed goals",
            "Penalty won",
        ],
        "Passing": [
            "Assists",
            "Expected assists (xA)",
            "Touches",
            "Big chances created",
            "Key passes",
            "Accurate passes",
            "Acc. own half",
            "Acc. opposition half",
            "Long balls (accurate)",
            "Accurate chip passes",
            "Acc. crosses",
        ],
        "Defending": [
            "Interceptions",
            "Tackles per game",
            "Possession won (final third)",
            "Balls recovered per game",
            "Dribbled past per game",
            "Clearances per game",
            "Blocked shots per game",
            "Errors leading to shot",
            "Errors leading to goal",
            "Penalties committed",
        ],
        "Other (per game)": [
            "Succ. dribbles",
            "Total duels won",
            "Ground duels won",
            "Aerial duels won",
            "Possession lost",
            "Fouls per game",
            "Was fouled",
            "Offsides",
        ],
    }

    # Build output rows (order guaranteed)
    rows = []
    for cat, metrics in wanted.items():
        for m in metrics:
            rows.append({"Category": cat, "Metric": m, "Value": None})
    row_index = {(r["Category"], r["Metric"]): r for r in rows}

    # -------------------- 1) Try UI-group extraction (best case) --------------------
    def stat_value(stat):
        if not isinstance(stat, dict):
            return None
        v = stat.get("displayValue")
        if v is None:
            v = stat.get("formattedValue")
        if v is None:
            v = stat.get("valueText")
        if v is None:
            v = stat.get("value")
        if isinstance(v, dict):
            v = v.get("displayValue") or v.get("formattedValue") or v.get("valueText") or v.get("value")
        return v

    def stat_name(stat):
        if not isinstance(stat, dict):
            return None
        n = stat.get("name") or stat.get("title") or stat.get("label") or stat.get("key")
        return n.strip() if isinstance(n, str) else None

    def group_name(g):
        if not isinstance(g, dict):
            return None
        n = g.get("name") or g.get("groupName") or g.get("title") or g.get("category")
        if not isinstance(n, str):
            return None
        raw = n.strip()
        low = raw.lower()

        # SofaScore is inconsistent: the same UI section can be called "Attack" vs "Attacking", etc.
        if low in {"attack", "attacking"}:
            return "Attacking"
        if low in {"pass", "passing"}:
            return "Passing"
        if low in {"def", "defending", "defence", "defense"}:
            return "Defending"
        if low in {"other", "other (per game)", "otherpergame"}:
            return "Other (per game)"
        # Many duel/possession loss metrics are grouped under "Duels" in some payloads
        if low in {"duels"}:
            return "Other (per game)"
        return raw

    METRIC_ALIASES = {
        # Some payloads use long names; map them to the exact UI labels we store.
        "accurate crosses": "Acc. crosses",
        "accurate cross": "Acc. crosses",
        "accurate long balls (percentage)": "Long balls (accurate)",
        # In some payloads the name is shortened, but the value is still per-game.
        "blocked shots": "Blocked shots per game",
    }

    STAT_LIST_KEYS = ("statistics", "statisticsItems", "items", "stats", "statisticsData")
    # IMPORTANT:
    # `stats_json` is a merged object that may contain a top-level `statistics` dict
    # (overall summary fields) PLUS `groups` payloads used by the UI tables.
    # Do NOT narrow the traversal to `stats_json['statistics']`, or we will miss
    # group-based metrics like long balls, defensive errors, etc.
    payload = stats_json

    stack = [payload]
    seen = set()
    while stack:
        obj = stack.pop()
        oid = id(obj)
        if oid in seen:
            continue
        seen.add(oid)

        if isinstance(obj, dict):
            gname = group_name(obj)
            if gname in wanted:
                for k in STAT_LIST_KEYS:
                    lst = obj.get(k)
                    if isinstance(lst, list):
                        for st in lst:
                            nm = stat_name(st)
                            if not nm:
                                continue
                            nm_norm = METRIC_ALIASES.get(nm.strip().lower(), nm)
                            if (gname, nm_norm) in row_index:
                                val = stat_value(st)
                                if val is not None and row_index[(gname, nm_norm)]["Value"] is None:
                                    row_index[(gname, nm_norm)]["Value"] = val
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    stack.append(v)
        elif isinstance(obj, list):
            for it in obj:
                if isinstance(it, (dict, list)):
                    stack.append(it)

    # -------------------- 2) Fallback from stable fields --------------------
    def deep_find_key(obj, key_lower):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str) and k.lower() == key_lower:
                    return v
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    got = deep_find_key(v, key_lower)
                    if got is not None:
                        return got
        elif isinstance(obj, list):
            for it in obj:
                got = deep_find_key(it, key_lower)
                if got is not None:
                    return got
        return None

    def deep_find_contains(obj, substr_lowers):
        """
        Recursively search for the first value whose key contains ANY of the given substrings.
        substr_lowers: list[str] already lowercased.
        """
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(k, str):
                    lk = k.lower()
                    for sub in substr_lowers:
                        if sub and sub in lk:
                            return v
            for v in obj.values():
                if isinstance(v, (dict, list)):
                    got = deep_find_contains(v, substr_lowers)
                    if got is not None:
                        return got
        elif isinstance(obj, list):
            for it in obj:
                got = deep_find_contains(it, substr_lowers)
                if got is not None:
                    return got
        return None

    def first_of_contains(substrings):
        """Convenience wrapper: substring search (case-insensitive) across the payload."""
        subs = [str(s).lower() for s in substrings if s]
        if not subs:
            return None
        return deep_find_contains(stats_json, subs)

    def first_of(keys):
        for k in keys:
            v = deep_find_key(stats_json, k.lower())
            if v is not None:
                return v
        return None

    def num(v):
        try:
            if v is None:
                return None
            if isinstance(v, str):
                vv = v.strip().replace("%", "")
                return float(vv)
            return float(v)
        except Exception:
            return None

    def fmt_float(v, decimals=1):
        nv = num(v)
        if nv is None:
            return None
        try:
            from decimal import Decimal, ROUND_HALF_UP
            q = Decimal("1") if decimals == 0 else Decimal("0." + "0" * (decimals - 1) + "1")
            d = Decimal(str(nv)).quantize(q, rounding=ROUND_HALF_UP)
            s = format(d, "f")
        except Exception:
            s = f"{nv:.{decimals}f}"

        if decimals == 1 and s.endswith(".0"):
            s = s[:-2]
        return s

    def fmt_int(v):
        nv = num(v)
        if nv is None:
            return None
        return str(int(round(nv)))

    def fmt_pct(v):
        nv = num(v)
        if nv is None:
            return None
        return f"{int(round(nv))}%"

    def fmt_ratio(a, b):
        av = fmt_int(a)
        bv = fmt_int(b)
        if av is None and bv is None:
            return None
        return f"{av or ''}/{bv or ''}"

    def setv(cat, metric, value):
        if value is None:
            return
        if (cat, metric) in row_index and row_index[(cat, metric)]["Value"] is None:
            row_index[(cat, metric)]["Value"] = value

    def setv_force(cat, metric, value):
        """Set value even if already present (used when UI/group value should win)."""
        if value is None:
            return
        if (cat, metric) in row_index:
            row_index[(cat, metric)]["Value"] = value

    def find_group_metric_value(target_names_lower):
        """Search only inside stats_json['groups'] payloads for a stat name match and return its value."""
        groups = (stats_json or {}).get("groups")
        if not isinstance(groups, dict):
            return None

        def walk(obj):
            if isinstance(obj, dict):
                # check if this dict itself looks like a stat entry
                nm = stat_name(obj)
                if isinstance(nm, str) and nm.strip().lower() in target_names_lower:
                    return stat_value(obj)

                # also check common stat-list containers
                for k in STAT_LIST_KEYS:
                    lst = obj.get(k)
                    if isinstance(lst, list):
                        for st in lst:
                            nm2 = stat_name(st)
                            if isinstance(nm2, str) and nm2.strip().lower() in target_names_lower:
                                v2 = stat_value(st)
                                if v2 is not None:
                                    return v2

                for v in obj.values():
                    if isinstance(v, (dict, list)):
                        got = walk(v)
                        if got is not None:
                            return got
            elif isinstance(obj, list):
                for it in obj:
                    got = walk(it)
                    if got is not None:
                        return got
            return None

        for _, payload in groups.items():
            got = walk(payload)
            if got is not None:
                return got
        return None

    # Prefer the player's own overall season statistics dict when available.
    # This avoids deep-search accidentally picking similarly-named team/aggregate fields.
    overall_stats_dict = {}
    try:
        overall_stats_dict = (stats_json.get("overall") or {}).get("statistics") or {}
        if not isinstance(overall_stats_dict, dict):
            overall_stats_dict = {}
    except Exception:
        overall_stats_dict = {}

    # appearances (needed for per-game conversions)
    appearances_raw = first_of(["appearances", "matches", "games"])
    appearances = None
    try:
        if appearances_raw is not None:
            appearances = int(float(appearances_raw))
            if appearances <= 0:
                appearances = None
    except Exception:
        appearances = None

    def per_game(per_game_keys, total_keys, decimals=1):
        v_pg = first_of(per_game_keys) if per_game_keys else None
        if v_pg is not None:
            return fmt_float(v_pg, decimals=decimals)
        if appearances:
            v_total = first_of(total_keys) if total_keys else None
            nv = num(v_total)
            if nv is not None:
                return fmt_float(nv / appearances, decimals=decimals)
        return None

    def per_game_plus_pct(per_game_keys, total_keys, pct_keys, decimals=1):
        pg = per_game(per_game_keys, total_keys, decimals=decimals)
        pc = fmt_pct(first_of(pct_keys) if pct_keys else None)
        if pg is None and pc is None:
            return None
        if pg is None:
            return pc
        if pc is None:
            return pg
        return f"{pg} ({pc})"

    # -------------------- Fill what’s missing using stable keys --------------------
    # Attacking
    setv("Attacking", "Goals", fmt_int(first_of(["goals"])))
    setv("Attacking", "Expected goals (xG)", fmt_float(first_of(["expectedGoals", "expectedgoals", "xg"]), 2))
    sf = first_of(["scoringFrequency", "scoringfrequency", "minutesPerGoal", "minutespergoal"])
    if sf is not None:
        sfn = num(sf)
        if sfn is not None:
            setv("Attacking", "Scoring frequency (in minutes)", f"{int(round(sfn))}min")
        else:
            setv("Attacking", "Scoring frequency (in minutes)", str(sf))

    setv("Attacking", "Goals per game", per_game(["goalsPerGame", "goalspergame"], ["goals"]))
    setv("Attacking", "Total shots", per_game(
        ["totalShotsPerGame", "shotsPerGame", "shotspergame", "totalshotspergame"],
        ["totalShots", "shots", "shotsTotal", "totalshots"]
    ))
    setv("Attacking", "Shots on target per game", per_game(
        ["shotsOnTargetPerGame", "shotsonTargetpergame", "shotsontargetpergame"],
        ["shotsOnTarget", "shotsonTarget", "shotsOnTargetTotal"]
    ))
    setv("Attacking", "Big chances missed", fmt_int(first_of(["bigChancesMissed", "bigchancesmissed"])))
    setv("Attacking", "Goal conversion", fmt_pct(first_of(["goalConversionPercentage", "goalconversionpercentage", "goalConversion"])))

    fk_g = first_of([
        "freeKickGoals", "freekickgoals",
        "directFreeKickGoals", "directfreekickgoals",
        "freeKickGoalsScored", "freekickgoalsscored",
    ])

    fk_t = first_of([
        "freeKickShots", "freekickshots",
        "freeKickShotsTotal", "freekickshotstotal",
        "freeKickAttempts", "freekickattempts",
        "directFreeKicks", "directfreekicks",
        "directFreeKicksTotal", "directfreekickstotal",
        "directFreeKickAttempts", "directfreekickattempts",
        "directFreeKickShots", "directfreekickshots",
        "directFreeKickShotsTotal", "directfreekickshotstotal",
        "freeKicks", "freekicks",
        "freeKicksTotal", "freekickstotal",
    ])

    # last-resort substring search (some payloads use slightly different names)
    if fk_g is None:
        fk_g = first_of_contains(["freekickgoal"])
    if fk_t is None:
        fk_t = first_of_contains(["freekickattempt", "freekickshot", "directfreekick"])

    setv("Attacking", "Free kick goals", fmt_ratio(fk_g, fk_t) if fk_t is not None else fmt_int(fk_g))

    in_g = first_of(["goalsFromInsideBox", "goalsfrominsidethebox", "goalsInsideBox"])
    in_t = first_of(["shotsFromInsideBox", "shotsfrominsidethebox", "insideBoxShots", "shotsInsideBox"])
    setv("Attacking", "Goals from inside the box", fmt_ratio(in_g, in_t) if in_t is not None else fmt_int(in_g))

    out_g = first_of(["goalsFromOutsideBox", "goalsfromoutsidethebox", "goalsOutsideBox"])
    out_t = first_of(["shotsFromOutsideBox", "shotsfromoutsidethebox", "outsideBoxShots", "shotsOutsideBox"])
    setv("Attacking", "Goals from outside the box", fmt_ratio(out_g, out_t) if out_t is not None else fmt_int(out_g))

    setv("Attacking", "Headed goals", fmt_int(first_of(["headedGoals", "headedgoals"])))
    setv("Attacking", "Left-footed goals", fmt_int(first_of(["leftFootGoals", "leftfootgoals"])))
    setv("Attacking", "Right-footed goals", fmt_int(first_of(["rightFootGoals", "rightfootgoals"])))
    setv("Attacking", "Penalty won", fmt_int(first_of(["penaltiesWon", "penaltyWon", "penaltywon"])))


    # Passing
    setv("Passing", "Assists", fmt_int(first_of(["assists"])))
    setv("Passing", "Expected assists (xA)", fmt_float(first_of(["expectedAssists", "expectedassists", "xa", "xA"]), 2))
    setv("Passing", "Touches", per_game(["touchesPerGame", "touchespergame"], ["touches"]))
    setv("Passing", "Big chances created", fmt_int(first_of(["bigChancesCreated", "bigchancescreated"])))
    setv("Passing", "Key passes", per_game(["keyPassesPerGame", "keypassespergame"], ["keyPasses", "keypasses"]))

    setv("Passing", "Accurate passes", per_game_plus_pct(
        ["accuratePassesPerGame", "accuratepassespergame"],
        ["accuratePasses", "accuratepasses"],
        ["accuratePassesPercentage", "accuratepassespercentage"]
    ))

    setv("Passing", "Acc. own half", per_game_plus_pct(
        [
            "accuratePassesOwnHalfPerGame", "accuratepassesownhalfpergame",
            "accurateOwnHalfPerGame", "accurateownhalfpergame",
            "accuratePassesOwnHalfAvg", "accuratepassesownhalfavg",
        ],
        [
            "accuratePassesOwnHalf", "accuratepassesownhalf",
            "accurateOwnHalf", "accurateownhalf",
            "accuratePassesOwnHalfTotal", "accuratepassesownhalftotal",
        ],
        [
            "accuratePassesOwnHalfPercentage", "accuratepassesownhalfpercentage",
            "accurateOwnHalfPercentage", "accurateownhalfpercentage",
        ]
    ))

    # substring fallback for own half
    if row_index[("Passing", "Acc. own half")]["Value"] is None:
        own_total = first_of_contains(["ownhalf"])
        own_pct = first_of_contains(["ownhalfpercentage", "ownhalfperc", "ownhalf%"])
        v = per_game_plus_pct([], ["accuratePassesOwnHalf"], [], decimals=1)  # no-op to keep signature
        if own_total is not None and appearances:
            pg = fmt_float(num(own_total) / appearances, 1) if num(own_total) is not None else None
            pc = fmt_pct(own_pct)
            if pg or pc:
                setv("Passing", "Acc. own half", f"{pg} ({pc})" if (pg and pc) else (pg or pc))

    setv("Passing", "Acc. opposition half", per_game_plus_pct(
        [
            "accuratePassesOppositionHalfPerGame", "accuratepassesoppositionhalfpergame",
            "accurateOppHalfPerGame", "accurateopphalfpergame",
            "accuratePassesOppHalfPerGame", "accuratepassesopphalfpergame",
        ],
        [
            "accuratePassesOppositionHalf", "accuratepassesoppositionhalf",
            "accurateOppHalf", "accurateopphalf",
            "accuratePassesOppHalf", "accuratepassesopphalf",
            "accuratePassesOppositionHalfTotal", "accuratepassesoppositionhalftotal",
        ],
        [
            "accuratePassesOppositionHalfPercentage", "accuratepassesoppositionhalfpercentage",
            "accurateOppHalfPercentage", "accurateopphalfpercentage",
        ]
    ))

    # substring fallback for opposition half
    if row_index[("Passing", "Acc. opposition half")]["Value"] is None:
        opp_total = first_of_contains(["oppositionhalf", "opphalf"])
        opp_pct = first_of_contains(["oppositionhalfpercentage", "opphalfpercentage", "opphalfperc"])
        if opp_total is not None and appearances:
            pg = fmt_float(num(opp_total) / appearances, 1) if num(opp_total) is not None else None
            pc = fmt_pct(opp_pct)
            if pg or pc:
                setv("Passing", "Acc. opposition half", f"{pg} ({pc})" if (pg and pc) else (pg or pc))

    setv("Passing", "Accurate chip passes", per_game_plus_pct(
        [
            "accurateChipPassesPerGame", "accuratechippassespergame",
            "chipPassesAccuratePerGame", "chippassesaccuratepergame",
            "accurateChippedPassesPerGame", "accuratechippedpassespergame",
        ],
        [
            "accurateChipPasses", "accuratechippasses",
            "chipPassesAccurate", "chippassesaccurate",
            "accurateChippedPasses", "accuratechippedpasses",
        ],
        [
            "accurateChipPassesPercentage", "accuratechippassespercentage",
            "chipPassesAccuratePercentage", "chippassesaccuratepercentage",
            "accurateChippedPassesPercentage", "accuratechippedpassespercentage",
        ]
    ))

    # substring fallback for chip passes
    if row_index[("Passing", "Accurate chip passes")]["Value"] is None:
        chip_total = first_of_contains(["chippass", "chip pass"])
        chip_pct = first_of_contains(["chippasspercentage", "chippassperc", "chip%"])
        if chip_total is not None and appearances:
            pg = fmt_float(num(chip_total) / appearances, 1) if num(chip_total) is not None else None
            pc = fmt_pct(chip_pct)
            if pg or pc:
                setv("Passing", "Accurate chip passes", f"{pg} ({pc})" if (pg and pc) else (pg or pc))

    setv("Passing", "Long balls (accurate)", per_game_plus_pct(
        [
            "accurateLongBallsPerGame", "accuratelongballspergame",
            "longBallsAccuratePerGame", "longballsaccuratepergame",
            "longBallsAccurateAvg", "longballsaccurateavg",
        ],
        [
            "accurateLongBalls", "accuratelongballs",
            "longBallsAccurate", "longballsaccurate",
            "longBallsAccurateTotal", "longballsaccuratetotal",
        ],
        [
            "accurateLongBallsPercentage", "accuratelongballspercentage",
            "longBallsAccuratePercentage", "longballsaccuratepercentage",
        ]
    ))

    # substring fallback for long balls (accurate)
    if row_index[("Passing", "Long balls (accurate)")]["Value"] is None:
        lb_total = first_of_contains(["longball", "long_ball", "long balls", "longballs"])
        lb_pct = first_of_contains(["longballpercentage", "longballspercentage", "longballperc", "longballsperc"])
        if lb_total is not None and appearances and num(lb_total) is not None:
            pg = fmt_float(num(lb_total) / appearances, 1)
            pc = fmt_pct(lb_pct)
            if pg or pc:
                setv("Passing", "Long balls (accurate)", f"{pg} ({pc})" if (pg and pc) else (pg or pc))

    setv("Passing", "Acc. crosses", per_game_plus_pct(
        [
            "accurateCrossesPerGame", "accuratecrossespergame", "crossesAccuratePerGame",
            "crossesAccurateAvg", "crossesaccurateavg",
        ],
        [
            "accurateCrosses", "accuratecrosses", "crossesAccurate",
            "accurateCrossesTotal", "accuratecrossestotal",
        ],
        [
            "accurateCrossesPercentage", "accuratecrossespercentage", "crossesAccuratePercentage",
        ],
        decimals=2
    ))

    # Defending
    setv("Defending", "Interceptions", per_game(["interceptionsPerGame", "interceptionspergame"], ["interceptions"]))
    setv("Defending", "Tackles per game", per_game(["tacklesPerGame", "tacklespergame"], ["tackles"]))
    setv("Defending", "Possession won (final third)", per_game(
        [
            "possessionWonFinalThirdPerGame", "possessionwonfinalthirdpergame",
            "possessionWonAttThirdPerGame", "possessionwonattthirdpergame",
            "possessionWonFinal3rdPerGame", "possessionwonfinal3rdpergame",
        ],
        [
            "possessionWonFinalThird", "possessionwonfinalthird",
            "possessionWonAttThird", "possessionwonattthird",
            "possessionWonFinal3rd", "possessionwonfinal3rd",
        ]
    ))

    # substring fallback for possession won in final third
    if row_index[("Defending", "Possession won (final third)")]["Value"] is None:
        pw = first_of_contains(["possessionwon", "finalthird", "final3rd", "attthird"])
        if pw is not None and appearances and num(pw) is not None:
            setv("Defending", "Possession won (final third)", fmt_float(num(pw) / appearances, 1))

    setv("Defending", "Balls recovered per game", per_game(
        [
            "ballsRecoveredPerGame", "ballsrecoveredpergame",
            "ballRecoveriesPerGame", "ballrecoveriespergame",
            "recoveriesPerGame", "recoveriespergame",
        ],
        [
            "ballsRecovered", "ballsrecovered",
            "ballRecoveries", "ballrecoveries",
            "recoveries", "ballRecoveriesTotal", "ballrecoveriestotal",
        ]
    ))

    # substring fallback for recoveries
    if row_index[("Defending", "Balls recovered per game")]["Value"] is None:
        br = first_of_contains(["ballrecover", "recovery", "recoveries"])
        if br is not None and appearances and num(br) is not None:
            setv("Defending", "Balls recovered per game", fmt_float(num(br) / appearances, 1))

    setv("Defending", "Dribbled past per game", per_game(
        ["dribbledPastPerGame", "dribbledpastpergame"],
        ["dribbledPast", "dribbledpast", "timesDribbledPast", "timesdribbledpast"]
    ))

    if row_index[("Defending", "Dribbled past per game")]["Value"] is None:
        dp = first_of_contains(["dribbledpast", "dribbled_past", "timesdribbledpast"])
        if dp is not None and appearances and num(dp) is not None:
            setv("Defending", "Dribbled past per game", fmt_float(num(dp) / appearances, 1))

    setv("Defending", "Clearances per game", per_game(
        ["clearancesPerGame", "clearancespergame"],
        ["clearances", "clearancestotal", "clearancesTotal"]
    ))

    if row_index[("Defending", "Clearances per game")]["Value"] is None:
        cl = first_of_contains(["clearance", "clearances"])
        if cl is not None and appearances and num(cl) is not None:
            setv("Defending", "Clearances per game", fmt_float(num(cl) / appearances, 1))

    # Blocked shots per game
    # IMPORTANT: In the overall payload, SofaScore exposes both:
    #   - blockedShots (often a different definition)
    #   - outfielderBlocks (this is what matches the UI "Blocked shots" / per-game value)
    # For this player/season: outfielderBlocks=2, appearances=16 => 0.125 -> 0.1 (website)

    # 1) If outfielderBlocks exists, use it as the authoritative total and compute per-game.
    if appearances and ("outfielderBlocks" in overall_stats_dict) and overall_stats_dict.get("outfielderBlocks") is not None:
        ob = num(overall_stats_dict.get("outfielderBlocks"))
        if ob is not None:
            setv_force("Defending", "Blocked shots per game", fmt_float(ob / appearances, 1))

    # 2) Otherwise, try explicit per-game keys from overall season statistics
    if row_index[("Defending", "Blocked shots per game")]["Value"] is None:
        bs_pg = None
        for k in (
            "blockedShotsPerGame", "shotsBlockedPerGame",
            "blockedshotspergame", "shotsblockedpergame",
            "blockedShotsAvg", "blockedshotsavg",
        ):
            if k in overall_stats_dict and overall_stats_dict.get(k) is not None:
                bs_pg = overall_stats_dict.get(k)
                break
        if bs_pg is not None:
            setv("Defending", "Blocked shots per game", fmt_float(bs_pg, 1))

    # 3) General fallback: compute from totals if needed (last resort)
    if row_index[("Defending", "Blocked shots per game")]["Value"] is None and appearances:
        bs_total = None
        for k in (
            "shotsBlocked", "shotsblocked",
            "blockedShots", "blockedshots",
            "blockedShotsTotal", "blockedshotstotal",
            "shotsBlockedTotal", "shotsblockedtotal",
        ):
            if k in overall_stats_dict and overall_stats_dict.get(k) is not None:
                bs_total = overall_stats_dict.get(k)
                break
        if bs_total is not None and num(bs_total) is not None:
            setv("Defending", "Blocked shots per game", fmt_float(num(bs_total) / appearances, 1))

    # 4) If groups exist (some seasons), let the UI/group value win over computed totals.
    ui_bs = find_group_metric_value({"blocked shots", "blocked shots per game"})
    if ui_bs is not None:
        nbs = num(ui_bs)
        if nbs is not None:
            setv_force("Defending", "Blocked shots per game", fmt_float(nbs, 1))
        else:
            setv_force("Defending", "Blocked shots per game", str(ui_bs))

    setv("Defending", "Errors leading to shot", fmt_int(first_of([
        "errorsLeadingToShot", "errorLeadToShot", "errorLeadToShots", "errorsleadingtoshot",
        "errorsLedToShot", "errorsledtoshot",
    ])))

    if row_index[("Defending", "Errors leading to shot")]["Value"] is None:
        els = first_of_contains(["error", "leadingtoshot", "ledtoshot"])
        setv("Defending", "Errors leading to shot", fmt_int(els))

    setv("Defending", "Errors leading to goal", fmt_int(first_of([
        "errorsLeadingToGoal", "errorLeadToGoal", "errorsleadingtogoal",
        "errorsLedToGoal", "errorsledtogoal",
    ])))

    if row_index[("Defending", "Errors leading to goal")]["Value"] is None:
        elg = first_of_contains(["error", "leadingtogoal", "ledtogoal"])
        setv("Defending", "Errors leading to goal", fmt_int(elg))

    setv("Defending", "Penalties committed", fmt_int(first_of([
        "penaltiesCommitted", "penaltiescommitted",
        "penaltyCommitted", "penaltycommitted",
        "penaltiesConceded", "penaltiesconceded",
        "penaltyConceded", "penaltyconceded",
    ])))

    if row_index[("Defending", "Penalties committed")]["Value"] is None:
        pc = first_of_contains(["penalt" , "committed", "conceded"])
        setv("Defending", "Penalties committed", fmt_int(pc))

    # Other (per game)
    setv("Other (per game)", "Succ. dribbles", per_game_plus_pct(
        ["successfulDribblesPerGame", "successfuldribblespergame"],
        ["successfulDribbles", "successfuldribbles"],
        ["successfulDribblesPercentage", "successfuldribblespercentage"]
    ))
    setv("Other (per game)", "Total duels won", per_game_plus_pct(
        ["totalDuelsWonPerGame", "totalduelswonpergame", "duelsWonPerGame"],
        ["totalDuelsWon", "totalduelswon", "duelsWon", "duelswon"],
        ["totalDuelsWonPercentage", "totalduelswonpercentage", "duelsWonPercentage", "duelswonpercentage"]
    ))
    setv("Other (per game)", "Ground duels won", per_game_plus_pct(
        ["groundDuelsWonPerGame", "groundduelswonpergame"],
        ["groundDuelsWon", "groundduelswon"],
        ["groundDuelsWonPercentage", "groundduelswonpercentage"]
    ))
    setv("Other (per game)", "Aerial duels won", per_game_plus_pct(
        ["aerialDuelsWonPerGame", "aerialduelswonpergame"],
        ["aerialDuelsWon", "aerialduelswon"],
        ["aerialDuelsWonPercentage", "aerialduelswonpercentage"]
    ))
    setv("Other (per game)", "Possession lost", per_game(
        ["possessionLostPerGame", "possessionlostpergame"],
        ["possessionLost", "possessionlost"]
    ))
    setv("Other (per game)", "Fouls per game", per_game(["foulsPerGame", "foulspergame"], ["fouls"]))
    setv("Other (per game)", "Was fouled", per_game(["wasFouledPerGame", "wasfouledpergame"], ["wasFouled", "wasfouled"]))
    setv("Other (per game)", "Offsides", per_game(["offsidesPerGame", "offsidespergame"], ["offsides"]))

    # --- Final correction: prefer UI/group value for Blocked shots per game ---
    # Some payloads only expose this correctly in grouped tables as "Blocked shots" (already per-game).
    # If we computed from totals we may get ~1.1; UI shows 0.1. Let the UI value win.
    ui_bs = find_group_metric_value({"blocked shots", "blocked shots per game"})
    if ui_bs is not None:
        # if it looks numeric, format to 1 decimal like the website
        nbs = num(ui_bs)
        if nbs is not None:
            # Only override when UI value is plausible and different
            cur = row_index[("Defending", "Blocked shots per game")]["Value"]
            cur_n = num(cur)
            # Override if current is missing OR differs materially (e.g., 1.1 vs 0.1)
            if cur_n is None or abs(cur_n - nbs) >= 0.4:
                setv_force("Defending", "Blocked shots per game", fmt_float(nbs, 1))
        else:
            setv_force("Defending", "Blocked shots per game", str(ui_bs))

    df_long = pd.DataFrame(rows, columns=["Category", "Metric", "Value"])
    df_long = df_long.drop(columns=["Category"])

    # Transpose: one row, metrics as columns
    df_wide = df_long.set_index("Metric").T
    df_wide.reset_index(drop=True, inplace=True)
    df_wide.insert(0, "Name", None)

    return df_wide


# -------------------- MAIN --------------------
def main():
    print("SofaScore — Player Detail (Stable Season Stats)\n")

    raw = input("Paste SofaScore PLAYER or TEAM URL/id: ").strip()

    # If the user pastes a tournament link, auto-detect tournament id and season id from the URL
    auto_tid = None
    auto_sid = None
    if "/tournament/" in raw.lower() or "/unique-tournament/" in raw.lower():
        try:
            auto_tid = parse_unique_tournament_id(raw)
        except Exception:
            auto_tid = None
        auto_sid = parse_season_id_from_url(raw)

    tid_raw = input("Tournament id [default 52 = Trendyol Süper Lig]: ").strip()
    if tid_raw:
        tournament_id = int(tid_raw)
    elif auto_tid is not None:
        tournament_id = auto_tid
    else:
        tournament_id = 52

    sid_raw = input("Season id (numeric or '25/26') [default: 25/26]: ").strip()

    # If the URL includes a season id (#id:...), trust it first.
    if auto_sid is not None and not sid_raw:
        season_id = int(auto_sid)
    # If user pressed Enter, use a fast numeric default when we have one.
    elif not sid_raw:
        season_id = DEFAULT_SEASON_BY_TOURNAMENT.get(tournament_id)
        if season_id is None:
            # No known numeric default for this tournament; resolve via API.
            try:
                season_id = resolve_season_id(tournament_id, "25/26")
            except Exception as e:
                # Graceful handling for 403 challenge
                if hasattr(e, 'args') and e.args and '403' in str(e.args[0]):
                    print(f"\n✗ BLOCKED while resolving season (Cloudflare challenge): {e}")
                    print("Tip: open sofascore.com in a normal browser on the same network to pass the challenge, then rerun.")
                    return
                else:
                    raise
    else:
        # User typed something
        try:
            season_id = resolve_season_id(tournament_id, sid_raw)
        except Exception as e:
            if hasattr(e, 'args') and e.args and '403' in str(e.args[0]):
                print(f"\n✗ BLOCKED while resolving season (Cloudflare challenge): {e}")
                print("Tip: open sofascore.com in a normal browser on the same network to pass the challenge, then rerun.")
                return
            else:
                raise

    print(f"Using Tournament={tournament_id}, Season={season_id}")

    # -------------------- TOURNAMENT BULK MODE --------------------
    if "/unique-tournament/" in raw.lower() or "/tournament/" in raw.lower():
        ut_id = parse_unique_tournament_id(raw)
        print(f"\nDetected TOURNAMENT mode. Unique tournament id: {ut_id}")

        print("Fetching tournament info…")
        try:
            ut_js = fetch_unique_tournament(ut_id)
        except ChallengeBlocked as e:
            print(f"\n✗ BLOCKED (Cloudflare challenge) while fetching tournament info: {e}")
            print("This is a temporary anti-bot block from SofaScore.")
            print("What usually works: wait a bit (15–60 min), reduce scraping frequency, or try a different network.")
            return
        tournament_name = (ut_js.get("uniqueTournament") or {}).get("name") or f"tournament_{ut_id}"

        print("Fetching standings teams…")
        try:
            teams = fetch_standings_team_ids(ut_id, season_id)
        except ChallengeBlocked as e:
            print(f"\n✗ BLOCKED (Cloudflare challenge) while fetching standings: {e}")
            print("This is a temporary anti-bot block from SofaScore.")
            print("What usually works: wait a bit (15–60 min), reduce scraping frequency, or try a different network.")
            return
        if not teams:
            raise RuntimeError("No teams found in standings for this tournament/season.")

        print(f"Found {len(teams)} teams in standings. Scraping teams → players…\n")

        all_profile = []
        all_summary = []
        all_stats = []

        for ti, (team_id, team_name_hint) in enumerate(teams, start=1):
            team_label = team_name_hint or str(team_id)
            print(f"\n=== [{ti}/{len(teams)}] TEAM: {team_label} (id={team_id}) ===")

            try:
                team_players_raw = fetch_team_players(team_id)
                players = []
                for entry in team_players_raw:
                    pid, pname = normalize_team_player_entry(entry)
                    if pid:
                        players.append((int(pid), pname))

                # de-dup preserve order
                seen = set()
                players_unique = []
                for pid, pname in players:
                    if pid not in seen:
                        seen.add(pid)
                        players_unique.append((pid, pname))

                print(f"Players found: {len(players_unique)}")

                for pi, (pid, pname) in enumerate(players_unique, start=1):
                    label = pname or str(pid)
                    print(f"  [{pi}/{len(players_unique)}] {label} (id={pid})")
                    try:
                        df_p, df_s, df_st, _ = scrape_one_player(pid, tournament_id, season_id)
                        all_profile.append(df_p)
                        all_summary.append(df_s)
                        all_stats.append(df_st)
                        print("    ✓ OK")
                    except Exception as e:
                        print(f"    ✗ ERROR: {e}")
                    time.sleep(0.35)

            except Exception as e:
                print(f"✗ TEAM ERROR: {e}")
                continue

        if not all_profile or not all_summary or not all_stats:
            raise RuntimeError("Tournament bulk run produced no rows (everything failed).")

        df_profile = pd.concat(all_profile, ignore_index=True, sort=False)
        df_summary = pd.concat(all_summary, ignore_index=True, sort=False)
        df_stats = pd.concat(all_stats, ignore_index=True, sort=False)

        safe_tname = str(tournament_name).replace(" ", "_")
        out_base = f"{safe_tname}_AllTeams_PlayerDetail_{tournament_id}_{season_id}"
        xlsx_path = os.path.abspath(out_base + ".xlsx")

        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df_profile.to_excel(writer, sheet_name="Profile", index=False)
            df_summary.to_excel(writer, sheet_name="Season_Summary", index=False)
            df_stats.to_excel(writer, sheet_name="Stats", index=False)

        print("\n✅ Tournament bulk done.")
        print(f"Saved Excel: {xlsx_path}")
        return
    # -------------------- TEAM BULK MODE --------------------
    if "/team/" in raw.lower() and ("/tournament/" not in raw.lower()) and ("/unique-tournament/" not in raw.lower()):
        team_id = parse_team_id(raw)
        print(f"\nDetected TEAM mode. Team id: {team_id}")

        # Team name is cosmetic (used only for output filename). Avoid hard-failing on /team/{id}
        # because it is often the first endpoint to trigger Cloudflare/anti-bot challenges.
        team_name = None
        try:
            # Try to derive a readable name from the URL slug first (e.g. /team/galatasaray/3061)
            m = re.search(r"/team/([^/]+)/\d+", str(raw), flags=re.IGNORECASE)
            if m:
                team_name = m.group(1).replace("-", " ").strip()
                team_name = " ".join(w.capitalize() for w in team_name.split())
        except Exception:
            team_name = None

        if not team_name:
            print("Fetching team info…")
            try:
                team_js = fetch_team(team_id)
                team_name = (team_js.get("team") or {}).get("name") or f"team_{team_id}"
            except ChallengeBlocked as e:
                print(f"\n✗ BLOCKED (Cloudflare challenge) while fetching team info: {e}")
                print("This is a temporary anti-bot block from SofaScore.")
                print("What usually works: wait a bit (15–60 min), reduce scraping frequency, or try a different network.")
                return
            except Exception as e:
                print(f"[WARN] Could not fetch team info; continuing with fallback name. Reason: {e}")
                team_name = f"team_{team_id}"

        print("Fetching team players…")
        try:
            team_players_raw = fetch_team_players(team_id)
        except ChallengeBlocked as e:
            print(f"\n✗ BLOCKED (Cloudflare challenge) while fetching team players: {e}")
            print("This is a temporary anti-bot block from SofaScore.")
            print("What usually works: wait a bit (15–60 min), reduce scraping frequency, or try a different network.")
            return

        players = []
        for entry in team_players_raw:
            pid, pname = normalize_team_player_entry(entry)
            if pid:
                players.append((int(pid), pname))

        # de-duplicate while preserving order
        seen = set()
        players_unique = []
        for pid, pname in players:
            if pid not in seen:
                seen.add(pid)
                players_unique.append((pid, pname))

        if not players_unique:
            raise RuntimeError("No players found for this team.")

        print(f"Found {len(players_unique)} players. Scraping each player…\n")

        all_profile = []
        all_summary = []
        all_stats = []

        # small politeness delay to reduce rate-limit risk
        for i, (pid, pname) in enumerate(players_unique, start=1):
            label = pname or str(pid)
            print(f"[{i}/{len(players_unique)}] {label} (id={pid})")
            try:
                df_p, df_s, df_st, _ = scrape_one_player(pid, tournament_id, season_id)
                all_profile.append(df_p)
                all_summary.append(df_s)
                all_stats.append(df_st)
                print("  ✓ OK")
            except Exception as e:
                print(f"  ✗ ERROR: {e}")
            time.sleep(0.4)

        if not all_profile or not all_summary or not all_stats:
            raise RuntimeError("Bulk run produced no rows (all players failed).")

        df_profile = pd.concat(all_profile, ignore_index=True, sort=False)
        df_summary = pd.concat(all_summary, ignore_index=True, sort=False)
        df_stats = pd.concat(all_stats, ignore_index=True, sort=False)

        # filename: <TeamName>_PlayerDetail_<tournamentId>_<seasonId>.xlsx
        safe_team = str(team_name).replace(" ", "_")
        out_base = f"{safe_team}_PlayerDetail_{tournament_id}_{season_id}"
        xlsx_path = os.path.abspath(out_base + ".xlsx")

        with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
            df_profile.to_excel(writer, sheet_name="Profile", index=False)
            df_summary.to_excel(writer, sheet_name="Season_Summary", index=False)
            df_stats.to_excel(writer, sheet_name="Stats", index=False)

        print("\n✅ Team bulk done.")
        print(f"Saved Excel: {xlsx_path}")
        return

    # -------------------- SINGLE PLAYER MODE --------------------
    player_id = parse_player_id(raw)

    print("\nDetected PLAYER mode.")
    print("Scraping one player…")

    df_profile, df_summary, df_stats, player_name = scrape_one_player(player_id, tournament_id, season_id)

    # Save
    safe_name = (player_name or f"player_{player_id}").replace(" ", "_")
    out_base = f"{safe_name}_Season_{tournament_id}_{season_id}"
    xlsx_path = os.path.abspath(out_base + ".xlsx")

    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        df_profile.to_excel(writer, sheet_name="Profile", index=False)
        df_summary.to_excel(writer, sheet_name="Season_Summary", index=False)
        df_stats.to_excel(writer, sheet_name="Stats", index=False)

    print("\n✅ Done.")
    print(f"Saved Excel: {xlsx_path}")

if __name__ == "__main__":
    main()