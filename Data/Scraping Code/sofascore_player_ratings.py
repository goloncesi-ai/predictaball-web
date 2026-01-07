#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Sofascore — Team Top Players (Average Rating) scraper

Usage:
    python sofascore_player_ratings.py

Then:
    - Paste Sofascore TEAM URL or numeric id (e.g. Fenerbahçe team page)
    - Optionally change tournament id (default 52 = Trendyol Süper Lig)
    - Enter season id:
        • either the numeric id from the URL (…/52#id:63814)
        • or a short string like "24/25" or "25/26"
"""

import re
import time
import os
import sys
from typing import List, Dict, Any

import pandas as pd
import requests

API_BASE = "https://api.sofascore.com/api/v1"

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (compatible; sofascore-scraper/1.0)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.sofascore.com/",
})

# ---------------- HTTP helper ----------------
def get_json(url: str, retries: int = 3, backoff: float = 1.3) -> Dict[str, Any]:
    """
    Generic JSON GET with simple retry / backoff.
    """
    last = None
    for i in range(retries):
        r = SESSION.get(url, timeout=20)
        if r.ok:
            return r.json()
        last = (r.status_code, r.text[:800])
        time.sleep(backoff ** i)

    code, body = last or ("?", "?")
    raise RuntimeError(f"Request failed {url} [{code}]: {body}")

# ---------------- ID parsing ----------------
def parse_team_id(s: str) -> int:
    """
    Extract team id from:
      - full team URL (…/team/football/fenerbahce/3052)
      - Turkish URL (…/tr/football/team/fenerbahce-istanbul/3052)
      - or plain numeric id like '3052'
    """
    s = str(s).strip()
    # Pattern: /team/.../<id>
    m = re.search(r"/team/[^/]+/(\d+)", s)
    if m:
        return int(m.group(1))

    # Otherwise, last block of digits
    m = re.search(r"(\d+)$", s)
    if m:
        return int(m.group(1))

    raise ValueError(f"Could not detect team id from: {s}")

# ---------------- Season resolver ----------------
def resolve_season_id(tournament_id: int, sid_raw: str) -> int:
    """
    Try to convert user input into a season id.

    Cases:
      - '63814'        -> 63814 (numeric directly)
      - '24/25', '25/26' etc -> look up in
            /unique-tournament/{tid}/seasons
        and match the string against season name/slug/year text.
    """
    s = sid_raw.strip()
    if not s:
        raise ValueError("Empty season id")

    # pure integer -> use directly
    if s.isdigit():
        return int(s)

    # normalize user text like "24-25", "24 / 25" etc
    wanted = s.replace(" ", "")
    wanted = wanted.replace("-", "/")

    seasons_url = f"{API_BASE}/unique-tournament/{tournament_id}/seasons"
    data = get_json(seasons_url)

    seasons = (
        data.get("seasons")
        or data.get("uniqueTournamentSeasons")
        or data.get("data")
        or []
    )

    for season in seasons:
        text_parts = []
        for key in ("name", "slug", "fullName", "yearDisplay", "year"):
            if key in season and season[key] is not None:
                text_parts.append(str(season[key]))
        text = " ".join(text_parts)
        norm = text.replace(" ", "").replace("-", "/")
        if wanted in norm:
            sid = season.get("id")
            if sid is not None:
                return int(sid)

    raise ValueError(
        f"Could not resolve season '{sid_raw}' for tournament {tournament_id}. "
        "Please open the league page on Sofascore and copy the numeric season id "
        "from the URL (…/52#id:<season_id>)."
    )

# ---------------- League stats fetch ----------------
def fetch_league_player_stats(unique_tournament_id: int,
                              season_id: int,
                              limit: int = 100) -> List[Dict[str, Any]]:
    """
    Fetch *all* player statistics rows for a given league season, using
    Sofascore's /unique-tournament/{tid}/season/{sid}/statistics endpoint.

    We page through results using limit/offset, because Sofascore caps page size.
    """
    all_results: List[Dict[str, Any]] = []
    offset = 0

    while True:
        url = (
            f"{API_BASE}/unique-tournament/{unique_tournament_id}"
            f"/season/{season_id}/statistics"
            f"?limit={limit}&order=-rating&offset={offset}"
            f"&accumulation=total&group=summary"
        )
        data = get_json(url)
        results = data.get("results", [])

        if not results:
            break

        all_results.extend(results)

        if len(results) < limit:
            # Last page
            break

        offset += limit
        time.sleep(0.3)  # be polite

    return all_results

# ---------------- Main logic ----------------
def main() -> None:
    print("Sofascore — Team Top Players (Average Rating) scraper\n")

    # 1) Team
    team_raw = input("Paste Sofascore TEAM URL or numeric team id: ").strip()
    if not team_raw:
        print("No team given. Exiting.")
        return

    try:
        team_id = parse_team_id(team_raw)
    except Exception as e:
        print(f"Error parsing team id: {e}")
        return

    # 2) Tournament (default Trendyol Süper Lig = 52)
    tid_raw = input("Unique tournament id [default 52 = Trendyol Süper Lig]: ").strip()
    if tid_raw:
        try:
            tournament_id = int(tid_raw)
        except ValueError:
            print("Invalid tournament id, must be integer.")
            return
    else:
        tournament_id = 52

    # 3) Season id
    sid_raw = input("Season id (numeric, or like '24/25', '25/26'): ").strip()
    try:
        season_id = resolve_season_id(tournament_id, sid_raw)
    except Exception as e:
        print(f"Error resolving season id: {e}")
        return

    print(f"\nUsing tournament={tournament_id}, season={season_id}")
    print("Fetching league player statistics from Sofascore…")
    try:
        stats_rows = fetch_league_player_stats(tournament_id, season_id)
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return

    if not stats_rows:
        print("No stats returned. This usually means:")
        print("  • the tournament/season combination is wrong, OR")
        print("  • Sofascore has no player statistics table for that league/season yet.")
        return

    # 4) Filter to this team only
    team_rows = [r for r in stats_rows if r.get("team", {}).get("id") == team_id]

    if not team_rows:
        print("No player rows found for this team.")
        print("Check that the team actually plays in this league/season.")
        return

    # Sort by rating desc
    def rating_of(row: Dict[str, Any]) -> float:
        rt = row.get("rating") or row.get("statistics", {}).get("rating")
        try:
            return float(rt)
        except (TypeError, ValueError):
            return float("nan")

    team_rows.sort(key=rating_of, reverse=True)

    # Get team name from first row
    team_name = team_rows[0].get("team", {}).get("name") or f"team_{team_id}"

    # 5) Build DataFrame of players
    records = []
    for rank, r in enumerate(team_rows, start=1):
        player = r.get("player", {}) or {}
        stats = r.get("statistics", {}) or {}

        rt_raw = r.get("rating") or stats.get("rating")
        try:
            rt = float(rt_raw) if rt_raw is not None else None
        except (TypeError, ValueError):
            rt = None

        rec = {
            "Rank": rank,
            "Player": player.get("name"),
            "Position": player.get("position"),
            "Matches": stats.get("matches"),
            "Minutes": stats.get("minutesPlayed"),
            "AverageRating": rt,
            "Team": team_name,
            "TeamId": team_id,
            "TournamentId": tournament_id,
            "SeasonId": season_id,
        }
        records.append(rec)

    df = pd.DataFrame(records)

    # Type clean-up
    for col in ["Matches", "Minutes"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

    df["AverageRating"] = pd.to_numeric(df["AverageRating"], errors="coerce")

    # 6) Save
    default_base = f"{team_name.replace(' ', '_')}_TopPlayers_{tournament_id}_{season_id}"
    out_base = input(
        f"\nOutput filename base "
        f"[default: {default_base}]: "
    ).strip() or default_base

    xlsx_path = os.path.abspath(out_base + ".xlsx")
    csv_path = os.path.abspath(out_base + ".csv")

    try:
        df.to_excel(xlsx_path, index=False)
        df.to_csv(csv_path, index=False)
    except Exception as e:
        print(f"\n[ERROR] Could not save files: {e}")
        return

    print("\n✅ Done.")
    print(f"Saved Excel : {xlsx_path}")
    print(f"Saved CSV   : {csv_path}")

if __name__ == "__main__":
    main()