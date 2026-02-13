#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Send one email per match prediction for a given round.

This is designed for the weekly automation flow:
1. scrape + ingest
2. generate round predictions
3. send standalone emails for each predicted match
"""

import argparse
import json
import os
import smtplib
import ssl
import sys
import time
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
PREDICTIONS_DIR = BASE_DIR / "Data" / "predictions"
DEFAULT_TO_ADDRESS = "goloncesi@gmail.com"


def _load_env_file(path):
    """Load KEY=VALUE pairs into os.environ without overriding existing values."""
    env_path = Path(path)
    if not env_path.exists() or not env_path.is_file():
        return False

    loaded = False
    with open(env_path, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
                loaded = True
    return loaded


def load_email_env():
    """Load optional env files for launchd/non-interactive runs."""
    candidate_files = []
    custom_env_file = os.getenv("GOLO_EMAIL_ENV_FILE", "").strip()
    if custom_env_file:
        candidate_files.append(custom_env_file)
    candidate_files.append(str(BASE_DIR / "scripts" / ".email.env"))
    candidate_files.append(str(BASE_DIR / ".env"))

    for path in candidate_files:
        _load_env_file(path)


def _env_bool(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _env_float(name, default=0.0):
    value = os.getenv(name)
    if value is None:
        return float(default)
    try:
        return float(value)
    except Exception:
        return float(default)


def _env_int(name, default=0):
    value = os.getenv(name)
    if value is None:
        return int(default)
    try:
        return int(value)
    except Exception:
        return int(default)


def _format_pct(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "0.0%"


def _format_float(value, digits=2):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return f"{0.0:.{digits}f}"


def _to_public_url(value, base_url):
    if not value:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/") and base_url:
        return f"{base_url.rstrip('/')}{value}"
    return value


def _confidence_details(confidence, probs):
    home = float(probs.get("home_win", 0))
    draw = float(probs.get("draw", 0))
    away = float(probs.get("away_win", 0))

    max_prob = max(home, draw, away)
    min_prob = min(home, draw, away)
    spread = max_prob - min_prob

    if confidence == "high":
        reason = (
            f"Clear favorite detected (max {max_prob:.1f}%, spread {spread:.1f}%). "
            "Strong model separation between outcomes."
        )
    elif confidence == "medium":
        reason = (
            f"Moderate favorite detected (max {max_prob:.1f}%, spread {spread:.1f}%). "
            "Prediction is useful but there is non-trivial uncertainty."
        )
    else:
        reason = (
            f"Close outcome probabilities (max {max_prob:.1f}%, spread {spread:.1f}%). "
            "Match is competitive and model certainty is lower."
        )

    return {
        "max_probability": round(max_prob, 1),
        "spread": round(spread, 1),
        "reason": reason,
    }


def load_predictions(round_number):
    predictions_file = PREDICTIONS_DIR / f"round_{round_number:02d}.json"
    if not predictions_file.exists():
        raise FileNotFoundError(
            f"Predictions file not found: {predictions_file}. "
            "Run scripts/weekly_predictions.py first."
        )

    with open(predictions_file, "r", encoding="utf-8") as f:
        return json.load(f), predictions_file


def build_match_email_body(match, round_number, generated_at, public_base_url):
    home_team = match.get("home_team", "Unknown Home")
    away_team = match.get("away_team", "Unknown Away")
    match_id = match.get("match_id", "")
    probs = match.get("probabilities", {}) or {}
    expected_goals = match.get("expected_goals", {}) or {}
    confidence = str(match.get("confidence", "low")).lower()
    confidence_data = _confidence_details(confidence, probs)

    top5_scores = match.get("top5_scores", []) or []
    markov_form = match.get("markov_form", {}) or {}
    avg_ratings = match.get("avg_ratings", {}) or {}

    team1_logo_url = _to_public_url(match.get("team1_logo_url"), public_base_url)
    team2_logo_url = _to_public_url(match.get("team2_logo_url"), public_base_url)
    player_heatmap_url = _to_public_url(match.get("player_heatmap_url"), public_base_url)
    main_cluster_heatmap_url = _to_public_url(match.get("main_cluster_heatmap_url"), public_base_url)
    strip_cluster_heatmap_url = _to_public_url(match.get("strip_cluster_heatmap_url"), public_base_url)

    # Fallback for legacy nested format
    heatmaps = match.get("heatmaps", {}) or {}
    if not player_heatmap_url:
        player_heatmap_url = _to_public_url(heatmaps.get("player"), public_base_url)
    if not main_cluster_heatmap_url:
        main_cluster_heatmap_url = _to_public_url(heatmaps.get("main_clusters"), public_base_url)
    if not strip_cluster_heatmap_url:
        strip_cluster_heatmap_url = _to_public_url(heatmaps.get("strip_clusters"), public_base_url)

    lines = [
        "MATCH_INTELLIGENCE_BRIEF",
        "PURPOSE: Structured simulation output for rapid LLM/Perplexity ingestion.",
        "",
        "MATCH_META",
        f"- round: {round_number}",
        f"- generated_at: {generated_at}",
        f"- match_id: {match_id}",
        f"- date: {match.get('date', '')}",
        f"- time: {match.get('time', '')}",
        f"- datetime_iso: {match.get('datetime_iso', '')}",
        f"- home_team: {home_team}",
        f"- away_team: {away_team}",
        "",
        "CARD_OUTPUT",
        f"- predicted_score: {match.get('predicted_score', '0-0')}",
        (
            f"- probabilities: home_win={_format_pct(probs.get('home_win', 0))}, "
            f"draw={_format_pct(probs.get('draw', 0))}, "
            f"away_win={_format_pct(probs.get('away_win', 0))}"
        ),
        f"- confidence_level: {confidence}",
        f"- confidence_max_probability: {_format_pct(confidence_data['max_probability'])}",
        f"- confidence_spread: {_format_pct(confidence_data['spread'])}",
        f"- confidence_reason: {confidence_data['reason']}",
        (
            f"- expected_goals: home={_format_float(expected_goals.get('home', 0), 2)}, "
            f"away={_format_float(expected_goals.get('away', 0), 2)}"
        ),
        "",
        "MOST_LIKELY_SCORELINES_TOP5",
    ]

    if top5_scores:
        for item in top5_scores:
            lines.append(
                f"- score={item.get('score', '')}; "
                f"count={item.get('count', 0)}; "
                f"probability={_format_pct(item.get('percentage', 0))}"
            )
    else:
        lines.append("- none")

    lines.extend(["", "MARKOV_FORM"])

    team1_form = markov_form.get("team1", {}) if isinstance(markov_form, dict) else {}
    team2_form = markov_form.get("team2", {}) if isinstance(markov_form, dict) else {}

    if team1_form or team2_form:
        for idx, team_form in enumerate([team1_form, team2_form], start=1):
            if not team_form:
                continue
            lines.extend(
                [
                    f"- team{idx}_name: {team_form.get('name', '')}",
                    f"  form_label: {team_form.get('form_label', '')}",
                    f"  next_win_prob: {_format_pct(team_form.get('next_win_prob', 0))}",
                    f"  next_draw_prob: {_format_pct(team_form.get('next_draw_prob', 0))}",
                    f"  next_loss_prob: {_format_pct(team_form.get('next_loss_prob', 0))}",
                    f"  matches_analyzed: {team_form.get('matches_analyzed', 0)}",
                    f"  hidden_states: {team_form.get('hidden_states', 0)}",
                ]
            )

            state_profiles = team_form.get("state_profiles", []) or []
            if state_profiles:
                lines.append("  state_profiles:")
                for state in state_profiles:
                    lines.extend(
                        [
                            f"  - label: {state.get('label', '')}",
                            f"    count: {state.get('count', 0)}",
                            f"    win_prob: {_format_pct(state.get('win_prob', 0))}",
                            f"    draw_prob: {_format_pct(state.get('draw_prob', 0))}",
                            f"    loss_prob: {_format_pct(state.get('loss_prob', 0))}",
                        ]
                    )
            else:
                lines.append("  state_profiles: []")
    else:
        lines.append("- unavailable")

    lines.extend(
        [
            "",
            "AVERAGE_PLAYER_RATINGS",
            f"- home_team_rating: {_format_float(avg_ratings.get('team1', 0), 2)}",
            f"- away_team_rating: {_format_float(avg_ratings.get('team2', 0), 2)}",
            "",
            "ASSET_LINKS",
            f"- home_team_logo: {team1_logo_url}",
            f"- away_team_logo: {team2_logo_url}",
            f"- player_ratings_heatmap: {player_heatmap_url}",
            f"- main_cluster_heatmap: {main_cluster_heatmap_url}",
            f"- strip_cluster_heatmap: {strip_cluster_heatmap_url}",
            "",
            "RAW_JSON",
            "```json",
            json.dumps(match, ensure_ascii=False, indent=2),
            "```",
            "",
            "END_OF_BRIEF",
        ]
    )

    return "\n".join(lines)


def send_round_emails(
    round_number,
    to_address,
    dry_run=False,
    max_emails=0,
):
    enabled = _env_bool("GOLO_EMAIL_ENABLED", True)
    if not enabled and not dry_run:
        print("Email sending disabled via GOLO_EMAIL_ENABLED=false. Skipping.")
        return True

    predictions, predictions_file = load_predictions(round_number)
    matches = predictions.get("matches", []) or []
    generated_at = predictions.get("generated_at", "")
    public_base_url = os.getenv("GOLO_EMAIL_PUBLIC_BASE_URL", "").strip()

    if max_emails > 0:
        matches = matches[:max_emails]

    if not matches:
        print(f"No matches found in {predictions_file}. Nothing to send.")
        return True

    from_address = os.getenv("GOLO_EMAIL_FROM", "").strip()
    smtp_password = os.getenv("GOLO_EMAIL_PASSWORD", "").strip()
    smtp_host = os.getenv("GOLO_EMAIL_SMTP_HOST", "smtp.gmail.com").strip()
    smtp_port = _env_int("GOLO_EMAIL_SMTP_PORT", 465)
    smtp_user = os.getenv("GOLO_EMAIL_SMTP_USER", from_address).strip()
    smtp_timeout = _env_int("GOLO_EMAIL_SMTP_TIMEOUT", 30)
    use_ssl = _env_bool("GOLO_EMAIL_USE_SSL", True)
    reply_to = os.getenv("GOLO_EMAIL_REPLY_TO", "").strip()
    subject_prefix = os.getenv("GOLO_EMAIL_SUBJECT_PREFIX", "").strip()
    delay_seconds = _env_float("GOLO_EMAIL_DELAY_SECONDS", 1.0)

    if dry_run:
        print(
            f"[DRY RUN] Loaded {len(matches)} matches from {predictions_file}. "
            "No emails will be sent."
        )
    else:
        missing = []
        if not from_address:
            missing.append("GOLO_EMAIL_FROM")
        if not smtp_password:
            missing.append("GOLO_EMAIL_PASSWORD")

        if missing:
            print(
                "Missing required email environment variables: "
                + ", ".join(missing)
            )
            return False

    sent_count = 0
    failed_count = 0
    errors = []

    smtp_client = None
    if not dry_run:
        try:
            if use_ssl:
                context = ssl.create_default_context()
                smtp_client = smtplib.SMTP_SSL(
                    smtp_host, smtp_port, timeout=smtp_timeout, context=context
                )
            else:
                smtp_client = smtplib.SMTP(smtp_host, smtp_port, timeout=smtp_timeout)
                smtp_client.ehlo()
                smtp_client.starttls(context=ssl.create_default_context())
                smtp_client.ehlo()
            smtp_client.login(smtp_user, smtp_password)
            print(f"SMTP connection established to {smtp_host}:{smtp_port}.")
        except Exception as exc:
            print(f"Failed to connect/login to SMTP: {exc}")
            return False

    try:
        for idx, match in enumerate(matches, start=1):
            home = match.get("home_team", "Home")
            away = match.get("away_team", "Away")
            subject_base = f"{home} vs {away}"
            subject = f"{subject_prefix} {subject_base}".strip() if subject_prefix else subject_base
            body = build_match_email_body(
                match=match,
                round_number=round_number,
                generated_at=generated_at,
                public_base_url=public_base_url,
            )

            if dry_run:
                print(f"[DRY RUN] [{idx}/{len(matches)}] {subject}")
                continue

            msg = EmailMessage()
            msg["From"] = from_address
            msg["To"] = to_address
            msg["Subject"] = subject
            msg["Date"] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")
            if reply_to:
                msg["Reply-To"] = reply_to
            msg.set_content(body)

            try:
                smtp_client.send_message(msg)
                sent_count += 1
                print(f"[{idx}/{len(matches)}] Sent: {subject}")
            except Exception as exc:
                failed_count += 1
                error_message = f"[{idx}/{len(matches)}] Failed: {subject} | {exc}"
                errors.append(error_message)
                print(error_message)

            if delay_seconds > 0:
                time.sleep(delay_seconds)
    finally:
        if smtp_client is not None:
            try:
                smtp_client.quit()
            except Exception:
                pass

    if dry_run:
        print("[DRY RUN] Completed successfully.")
        return True

    print("")
    print("Email dispatch summary:")
    print(f"- target: {to_address}")
    print(f"- round: {round_number}")
    print(f"- attempted: {len(matches)}")
    print(f"- sent: {sent_count}")
    print(f"- failed: {failed_count}")

    if errors:
        print("Failures:")
        for item in errors:
            print(f"- {item}")

    return failed_count == 0


def main():
    load_email_env()

    parser = argparse.ArgumentParser(
        description="Send one prediction email per match for a selected round."
    )
    parser.add_argument(
        "--round",
        type=int,
        required=True,
        help="Round number to email (uses Data/predictions/round_XX.json).",
    )
    parser.add_argument(
        "--to",
        type=str,
        default=os.getenv("GOLO_EMAIL_TO", DEFAULT_TO_ADDRESS),
        help=f"Recipient email address (default: {DEFAULT_TO_ADDRESS}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview subjects without sending email.",
    )
    parser.add_argument(
        "--max-emails",
        type=int,
        default=0,
        help="If > 0, send only the first N emails (useful for testing).",
    )
    args = parser.parse_args()

    if args.round < 1 or args.round > 34:
        print(f"Round must be between 1 and 34, got {args.round}.")
        sys.exit(1)

    ok = send_round_emails(
        round_number=args.round,
        to_address=args.to,
        dry_run=args.dry_run,
        max_emails=args.max_emails,
    )
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
