#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import random
import re
import time
from typing import Dict, List, Optional, Tuple

import pandas as pd
import requests

try:
    from bs4 import BeautifulSoup
except Exception as exc:  # pragma: no cover - local dependency check
    raise SystemExit(
        "Missing dependency: bs4. Install with: pip install beautifulsoup4"
    ) from exc


BASE_URL = "https://www.futbin.com"
LIST_PATH = "/players?league=68&version=gold%2Csilver%2Cbronze"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "Mozilla/5.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Referer": BASE_URL,
    }
)

MIN_DELAY_SEC = 0.9
JITTER_SEC = 0.7


def _polite_sleep() -> None:
    time.sleep(MIN_DELAY_SEC + random.random() * JITTER_SEC)


def get_html(url: str, retries: int = 3, backoff: float = 1.4) -> str:
    last = None
    for i in range(retries):
        _polite_sleep()
        resp = SESSION.get(url, timeout=25)
        if resp.ok:
            return resp.text
        last = (resp.status_code, (resp.text or "")[:300])
        time.sleep(backoff**i)
    code, body = last or ("?", "?")
    raise RuntimeError(f"Request failed {url} [{code}]: {body}")


def parse_max_pages(soup: BeautifulSoup) -> int:
    pages = []
    for a in soup.select('a[href*="players?page="]'):
        href = a.get("href", "")
        m = re.search(r"[?&]page=(\d+)", href)
        if m:
            pages.append(int(m.group(1)))
    return max(pages or [1])


def extract_player_links(soup: BeautifulSoup) -> List[str]:
    links = set()
    for a in soup.select("a.player-row-playercard[href]"):
        href = a.get("href", "")
        if "/player/" in href and "playerhover" not in href:
            links.add(BASE_URL + href)
    if not links:
        for a in soup.select("a[href]"):
            href = a.get("href", "")
            if "/player/" in href and "playerhover" not in href:
                links.add(BASE_URL + href)
    return sorted(links)


def _text_int(value: str) -> Optional[int]:
    m = re.search(r"\d+", value or "")
    return int(m.group(0)) if m else None


def extract_name_and_rarity(soup: BeautifulSoup) -> Tuple[Optional[str], Optional[str]]:
    name = None
    rarity = None

    meta = soup.find("meta", {"name": "description"})
    if meta and meta.get("content"):
        first = meta["content"].split(" - EA FC", 1)[0].strip()
        m = re.search(r"\b(Gold|Silver|Bronze)\b(?:\s+(Rare|Common))?", first, re.I)
        if m:
            rarity = m.group(0).strip()
            name = first.replace(m.group(0), "").strip()
        else:
            name = first

    if not name:
        h1 = soup.find("h1")
        if h1:
            h1_text = h1.get_text(" ", strip=True)
            if " - " in h1_text:
                name = h1_text.split(" - ", 1)[0].strip()
            else:
                name = h1_text.strip()

    return name, rarity


def extract_badges(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    header = soup.select_one(".player-header")
    badges = {"Nationality": None, "League": None, "Club": None}
    if not header:
        return badges
    for img in header.select("img[alt]"):
        alt = (img.get("alt") or "").strip()
        title = (img.get("title") or "").strip()
        if alt == "Nation":
            badges["Nationality"] = title or badges["Nationality"]
        elif alt == "League":
            badges["League"] = title or badges["League"]
        elif alt == "Club":
            badges["Club"] = title or badges["Club"]
    return badges


def extract_info_box(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    info = {
        "Skills": None,
        "WeakFoot": None,
        "Height": None,
        "Height_cm": None,
        "Height_ft": None,
        "Foot": None,
        "BodyType": None,
        "Age": None,
    }
    header = soup.select_one(".player-header-info-box")
    if not header:
        return info

    for label_el in header.select(".text-faded"):
        label = label_el.get_text(" ", strip=True)
        label_key = label.lower()
        if label_key in {"skills", "weak foot", "height", "foot", "age", "b.type"}:
            raw = label_el.parent.get_text(" ", strip=True)
            value = raw.replace(label, "", 1).strip()
            if label_key == "skills":
                info["Skills"] = _text_int(value)
            elif label_key == "weak foot":
                info["WeakFoot"] = _text_int(value)
            elif label_key == "height":
                info["Height"] = value
                info["Height_cm"] = _text_int(value)
                m_ft = re.search(r"\|\s*([0-9'\" ]+)", value)
                info["Height_ft"] = m_ft.group(1).strip() if m_ft else None
            elif label_key == "foot":
                info["Foot"] = value
            elif label_key == "age":
                info["Age"] = _text_int(value)
            elif label_key == "b.type":
                info["BodyType"] = value
    return info


def extract_rarity(soup: BeautifulSoup) -> Optional[str]:
    header = soup.select_one(".player-header-info-box")
    if not header:
        return None
    for text in header.stripped_strings:
        if re.search(r"\b(Gold|Silver|Bronze)\b", text, re.I) and re.search(
            r"\b(Rare|Common)\b", text, re.I
        ):
            return text.strip()
    return None


def extract_stats(soup: BeautifulSoup) -> Tuple[Dict[str, Optional[int]], Dict[str, Optional[int]]]:
    main = {}
    sub = {}
    rows = soup.select(".player-stats-container .player-stat-row")
    for row in rows:
        name_el = row.select_one(".player-stat-name")
        val_el = row.select_one(".player-stat-value-wrapper")
        if not name_el or not val_el:
            continue
        name = name_el.get_text(" ", strip=True)
        value = _text_int(val_el.get_text(" ", strip=True))
        classes = row.get("class", [])
        if "standard-font" in classes:
            main[name] = value
        else:
            sub[name] = value
    return main, sub


BASE_COLUMNS = [
    "PlayerName",
    "PlayerUrl",
    "Nationality",
    "League",
    "Club",
    "Rarity",
    "Skills",
    "WeakFoot",
    "Height",
    "Height_cm",
    "Height_ft",
    "Foot",
    "BodyType",
    "Age",
]

MAIN_STAT_COLUMNS = ["Pace", "Shooting", "Passing", "Dribbling", "Defending", "Physical"]

SUB_STAT_COLUMNS = [
    "Acceleration",
    "Sprint Speed",
    "Att. Position",
    "Finishing",
    "Shot Power",
    "Long Shots",
    "Volleys",
    "Penalties",
    "Vision",
    "Crossing",
    "FK Acc.",
    "Short Pass",
    "Long Pass",
    "Curve",
    "Agility",
    "Balance",
    "Reactions",
    "Ball Control",
    "Dribbling_Sub",
    "Composure",
    "Interceptions",
    "Heading Acc.",
    "Def. Aware",
    "Stand Tackle",
    "Slide Tackle",
    "Jumping",
    "Stamina",
    "Strength",
    "Aggression",
]


def build_row(player_url: str, html: str) -> Dict[str, Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    name, rarity = extract_name_and_rarity(soup)
    badges = extract_badges(soup)
    info = extract_info_box(soup)
    rarity = rarity or extract_rarity(soup)
    main_stats, sub_stats = extract_stats(soup)

    row = {
        "PlayerName": name,
        "PlayerUrl": player_url,
        "Nationality": badges.get("Nationality"),
        "League": badges.get("League"),
        "Club": badges.get("Club"),
        "Rarity": rarity,
    }
    row.update(info)

    for col in MAIN_STAT_COLUMNS:
        row[col] = main_stats.get(col)

    for col in SUB_STAT_COLUMNS:
        key = col
        if col == "Dribbling_Sub":
            key = "Dribbling"
        row[col] = sub_stats.get(key)

    return row


def collect_player_urls(max_pages: Optional[int] = None) -> List[str]:
    first_url = BASE_URL + LIST_PATH
    first_html = get_html(first_url)
    soup = BeautifulSoup(first_html, "html.parser")
    total_pages = parse_max_pages(soup)
    if max_pages:
        total_pages = min(total_pages, max_pages)

    all_urls = []
    seen = set()
    for page in range(1, total_pages + 1):
        page_url = f"{BASE_URL}/players?page={page}&league=68&version=gold%2Csilver%2Cbronze"
        html = get_html(page_url)
        page_soup = BeautifulSoup(html, "html.parser")
        links = extract_player_links(page_soup)
        for link in links:
            if link not in seen:
                seen.add(link)
                all_urls.append(link)
        print(f"Page {page}/{total_pages}: {len(links)} player links")
    return all_urls


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Futbin players into an Excel file.")
    parser.add_argument("--max-pages", type=int, default=None, help="Limit pages (for testing).")
    parser.add_argument("--max-players", type=int, default=None, help="Limit players (for testing).")
    parser.add_argument(
        "--out",
        default="futbin_players_league68.xlsx",
        help="Output Excel filename.",
    )
    args = parser.parse_args()

    player_urls = collect_player_urls(max_pages=args.max_pages)
    if args.max_players:
        player_urls = player_urls[: args.max_players]

    rows = []
    for idx, url in enumerate(player_urls, start=1):
        print(f"[{idx}/{len(player_urls)}] {url}")
        html = get_html(url)
        row = build_row(url, html)
        rows.append(row)

    df = pd.DataFrame(rows, columns=BASE_COLUMNS + MAIN_STAT_COLUMNS + SUB_STAT_COLUMNS)
    df.to_excel(args.out, index=False)
    print(f"Saved: {args.out} ({len(df)} rows)")


if __name__ == "__main__":
    main()
