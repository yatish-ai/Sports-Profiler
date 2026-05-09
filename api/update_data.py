"""
<<<<<<< HEAD
api/update_data.py  —  Cricbuzz RapidAPI bulk update engine
════════════════════════════════════════════════════════════
Called when user clicks "⚡ UPDATE DATA" in the sidebar.

Pipeline
────────
  fetch_from_api(sport, df)
    ├─ GET /stats/v1/rankings/batsmen  (test + odi + t20)
    ├─ GET /stats/v1/rankings/bowlers  (test + odi + t20)
    ├─ GET /stats/v1/rankings/allrounders (test + odi + t20)
    └─ For each CSV player matched in rankings:
         GET /stats/v1/player/{id}/info  → full career stats

  simulate_update(sport, df)     — fallback when API unavailable
  merge_data(existing, fresh)    — monotone safe merge
  update_data(sport)             — orchestrate, backup, save CSV
  auto_update_if_needed(sport)   — weekly scheduler / cron hook
"""
from __future__ import annotations

import os, random, hashlib, logging, datetime, shutil, time
=======
api/update_data.py
──────────────────
TRUE semi-real-time update engine — wired to Cricbuzz Cricket API (RapidAPI).

How the Cricket update pipeline works
──────────────────────────────────────
Step 1 │ fetch_from_api()
       │  ├─ Calls /stats/v1/rankings/batsmen   → top batsmen (runs, avg, sr)
       │  ├─ Calls /stats/v1/rankings/bowlers   → top bowlers (wickets, economy)
       │  └─ Calls /matches/v1/recent           → recent match IDs
       │     └─ Calls /mcenter/v1/{id}/hscard   → scorecard per match
       │
Step 2 │ _build_update_dataframe()
       │  Fuzzy-matches Cricbuzz names → our CSV player names (difflib 0.82)
       │  Returns DataFrame with only matched rows + API-fresh columns
       │
Step 3 │ simulate_update()   [fallback when API key absent / rate-limited]
       │  Seeded by player_id + ISO-week → same click same week = same delta
       │
Step 4 │ merge_data()
       │  Monotone safe merge — stats never go backwards, no rows deleted
       │
Step 5 │ update_data()
       │  Orchestrates 1-4, writes timestamped backup, saves CSV to disk

Setup
──────
  1. pip install requests python-dotenv
  2. Create  sports_profiler/.env :
         CRICBUZZ_API_KEY=your_rapidapi_key_here
  3. Click "⚡ UPDATE DATA" in sidebar — done.

Cricbuzz RapidAPI endpoints used
──────────────────────────────────
  Host : cricbuzz-cricket.p.rapidapi.com
  GET /stats/v1/rankings/batsmen?formatType=test|odi|t20
  GET /stats/v1/rankings/bowlers?formatType=test|odi|t20
  GET /matches/v1/recent
  GET /mcenter/v1/{matchId}/hscard
"""

from __future__ import annotations

import os
import random
import hashlib
import logging
import datetime
import shutil
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
from difflib import get_close_matches

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

<<<<<<< HEAD
# ── Secret loading ─────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
except ImportError:
    pass

try:
    import streamlit as st
    if hasattr(st, "secrets"):
        for _k in ("CRICBUZZ_API_KEY",):
            if _k in st.secrets and not os.environ.get(_k):
                os.environ[_k] = str(st.secrets[_k])
except Exception:
    pass

# ── Paths ──────────────────────────────────────────────────────────────────
_HERE        = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR    = os.path.join(_HERE, "..", "data")
_BACKUP_DIR  = os.path.join(_DATA_DIR, "backups")
CRICKET_CSV  = os.path.join(_DATA_DIR, "cricket.csv")
FOOTBALL_CSV = os.path.join(_DATA_DIR, "football.csv")

CB_HOST    = "cricbuzz-cricket.p.rapidapi.com"
CB_BASE    = f"https://{CB_HOST}"
CB_KEY_ENV = "CRICBUZZ_API_KEY"
TIMEOUT    = 8


def _get_key() -> str:
    return os.environ.get(CB_KEY_ENV, "").strip()


def _hdr() -> dict:
    return {"X-RapidAPI-Key": _get_key(), "X-RapidAPI-Host": CB_HOST}


# ══════════════════════════════════════════════════════════════════════════════
# FETCH FROM CRICBUZZ API
# ══════════════════════════════════════════════════════════════════════════════
def fetch_from_api(sport: str, df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Fetch latest cricket stats from Cricbuzz RapidAPI.
    Returns a DataFrame (cricket.csv schema) or None on failure.
    Football always returns None.
=======
# ── Load .env if present ──────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
except ImportError:
    pass  # dotenv optional — key can also be set via system env var

# ── Paths ─────────────────────────────────────────────────────────────────────
_HERE       = os.path.dirname(os.path.abspath(__file__))
_DATA_DIR   = os.path.join(_HERE, "..", "data")
_BACKUP_DIR = os.path.join(_DATA_DIR, "backups")

CRICKET_CSV  = os.path.join(_DATA_DIR, "cricket.csv")
FOOTBALL_CSV = os.path.join(_DATA_DIR, "football.csv")

# ── Cricbuzz RapidAPI config ──────────────────────────────────────────────────
CRICBUZZ_HOST    = "cricbuzz-cricket.p.rapidapi.com"
CRICBUZZ_BASE    = f"https://{CRICBUZZ_HOST}"
CRICBUZZ_KEY_ENV = "CRICBUZZ_API_KEY"


# =============================================================================
# STEP 1 — FETCH FROM CRICBUZZ API
# =============================================================================

def fetch_from_api(sport: str, df: pd.DataFrame):
    """
    Fetch live stats from Cricbuzz RapidAPI.
    Returns a DataFrame (cricket.csv schema) on success, or None on failure.
    Football always returns None — uses simulation fallback.
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    """
    if sport != "cricket":
        return None

<<<<<<< HEAD
    key = _get_key()
    if not key:
        logger.warning("CRICBUZZ_API_KEY not set — using simulation fallback.")
        return None

    try:
        import requests as req
    except ImportError:
        logger.error("'requests' not installed.")
        return None

    session  = req.Session()
    ranked   = {}   # player_name_lower → {id, rating, ...}

    # ── 1. Pull rankings across all formats & categories ──────────────────
    from api.data_fetcher import fetch_rankings
    for category in ("batsmen", "bowlers", "allrounders"):
        for fmt in ("test", "odi", "t20"):
            entries = fetch_rankings(session, category, fmt)
            for e in entries:
                name = (e.get("name") or "").strip()
                if not name:
                    continue
                k = name.lower()
                if k not in ranked:
                    ranked[k] = {"name": name, "cb_id": str(e.get("id", ""))}

    if not ranked:
        logger.warning("Cricbuzz rankings returned 0 players — falling back.")
        return None

    # ── 2. Match ranked players to our CSV ────────────────────────────────
    csv_names_low = [n.lower() for n in df["name"].tolist()]
    matched_rows  = []

    from api.data_fetcher import fetch_player_info, search_player_id

    for csv_idx, csv_row in df.iterrows():
        csv_name = csv_row["name"]
        csv_low  = csv_name.lower()

        # Try exact or fuzzy match in rankings
        cb_id = None
        if csv_low in ranked and ranked[csv_low]["cb_id"]:
            cb_id = ranked[csv_low]["cb_id"]
        else:
            close = get_close_matches(csv_low, list(ranked.keys()), n=1, cutoff=0.78)
            if close and ranked[close[0]]["cb_id"]:
                cb_id = ranked[close[0]]["cb_id"]

        # If not in rankings, try direct search
        if not cb_id:
            cb_id, _ = search_player_id(session, csv_name)

        if not cb_id:
            logger.debug("Cricbuzz: no ID found for '%s' — skipping.", csv_name)
            matched_rows.append(csv_row.to_dict())
            continue

        # Fetch career stats
        stats = fetch_player_info(session, cb_id, csv_name)
        if not stats:
            matched_rows.append(csv_row.to_dict())
            continue

        merged = csv_row.to_dict()

        # Apply career stat updates (monotone for cumulative, replace for rates)
        for col in ("runs", "innings", "hundreds", "fifties", "wickets"):
            api_val = int(stats.get(col, 0))
            if api_val > int(merged.get(col, 0)):
                merged[col] = api_val

        for col in ("average", "strike_rate", "bowling_avg", "economy"):
            api_val = float(stats.get(col, 0))
            if api_val > 0:
                merged[col] = round(api_val, 2)

        hs = int(stats.get("highest_score", 0))
        if hs > int(merged.get("highest_score", 0)):
            merged["highest_score"] = hs

        # Propagate run delta to 2024_runs
        api_runs = int(stats.get("runs", 0))
        csv_runs = int(csv_row.get("runs", 0))
        if api_runs > csv_runs:
            merged["2024_runs"] = int(merged.get("2024_runs", 0)) + (api_runs - csv_runs)

        matched_rows.append(merged)
        # Small delay to stay within free tier (100 calls/day)
        time.sleep(0.2)

    if not matched_rows:
        return None

    logger.info("Cricbuzz bulk update: %d/%d players processed.", len(matched_rows), len(df))
    return pd.DataFrame(matched_rows)


# ══════════════════════════════════════════════════════════════════════════════
# SIMULATE UPDATE  (fallback)
# ══════════════════════════════════════════════════════════════════════════════
def simulate_update(sport: str, df: pd.DataFrame) -> pd.DataFrame:
    """Weekly-seeded deterministic deltas — same week = same increments."""
    iso_y, iso_w, _ = datetime.date.today().isocalendar()
    week_seed = f"{iso_y}W{iso_w:02d}"

=======
    api_key = os.getenv(CRICBUZZ_KEY_ENV, "").strip()
    if not api_key:
        logger.warning(
            "CRICBUZZ_API_KEY not found in environment/.env — "
            "using simulation fallback. "
            "Add it to sports_profiler/.env to enable live data."
        )
        return None

    try:
        import requests
    except ImportError:
        logger.error("'requests' not installed. Run: pip install requests")
        return None

    headers = {
        "x-rapidapi-key":  api_key,
        "x-rapidapi-host": CRICBUZZ_HOST,
    }

    collected = {}   # player_name_lower -> {stat: value, ...}

    # ── Batting rankings (TEST, ODI, T20) ─────────────────────────────────────
    for fmt in ("test", "odi", "t20"):
        try:
            resp = requests.get(
                f"{CRICBUZZ_BASE}/stats/v1/rankings/batsmen",
                headers=headers, params={"formatType": fmt}, timeout=7
            )
            resp.raise_for_status()
            rankings = _dig(resp.json(), ["rank", "data.rank"], default=[])
            for entry in rankings[:50]:
                name = (_pick(entry, ["name", "fullName"]) or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key not in collected:
                    collected[key] = {"name": name}
                _si(collected[key], "runs",        entry, ["runs", "totalRuns"])
                _sf(collected[key], "average",     entry, ["avg", "average", "battingAverage"])
                _sf(collected[key], "strike_rate", entry, ["strikeRate", "sr"])
                _si(collected[key], "hundreds",    entry, ["hundreds", "100s", "centuries"])
                _si(collected[key], "fifties",     entry, ["fifties", "50s"])
            logger.info("Batting rankings [%s]: %d entries", fmt, len(rankings))
        except Exception as exc:
            logger.warning("Batting rankings [%s] error: %s", fmt, exc)

    # ── Bowling rankings (TEST, ODI, T20) ─────────────────────────────────────
    for fmt in ("test", "odi", "t20"):
        try:
            resp = requests.get(
                f"{CRICBUZZ_BASE}/stats/v1/rankings/bowlers",
                headers=headers, params={"formatType": fmt}, timeout=7
            )
            resp.raise_for_status()
            rankings = _dig(resp.json(), ["rank", "data.rank"], default=[])
            for entry in rankings[:50]:
                name = (_pick(entry, ["name", "fullName"]) or "").strip()
                if not name:
                    continue
                key = name.lower()
                if key not in collected:
                    collected[key] = {"name": name}
                _si(collected[key], "wickets",     entry, ["wickets", "totalWickets"])
                _sf(collected[key], "bowling_avg", entry, ["avg", "bowlingAverage", "average"])
                _sf(collected[key], "economy",     entry, ["economy", "econ", "economyRate"])
            logger.info("Bowling rankings [%s]: %d entries", fmt, len(rankings))
        except Exception as exc:
            logger.warning("Bowling rankings [%s] error: %s", fmt, exc)

    # ── Recent match scorecards ───────────────────────────────────────────────
    try:
        resp = requests.get(f"{CRICBUZZ_BASE}/matches/v1/recent",
                            headers=headers, timeout=7)
        resp.raise_for_status()
        match_ids = _extract_match_ids(resp.json())
        for mid in match_ids[:5]:          # cap at 5 to respect rate limits
            try:
                sc = requests.get(f"{CRICBUZZ_BASE}/mcenter/v1/{mid}/hscard",
                                  headers=headers, timeout=7)
                sc.raise_for_status()
                _parse_scorecard(sc.json(), collected)
            except Exception as exc:
                logger.debug("Scorecard [%s] error: %s", mid, exc)
    except Exception as exc:
        logger.warning("Recent matches error: %s", exc)

    if not collected:
        logger.warning("Cricbuzz returned no usable data — falling back.")
        return None

    return _build_update_dataframe(df, collected)


# =============================================================================
# STEP 2 — MAP CRICBUZZ NAMES → CSV ROWS
# =============================================================================

def _build_update_dataframe(existing_df: pd.DataFrame, collected: dict):
    """Fuzzy-match collected Cricbuzz names to CSV player names."""
    csv_names     = existing_df["name"].tolist()
    csv_names_low = [n.lower() for n in csv_names]

    rows = []
    for api_key, api_stats in collected.items():
        # Exact match first, then fuzzy
        if api_key in csv_names_low:
            idx = csv_names_low.index(api_key)
        else:
            close = get_close_matches(api_key, csv_names_low, n=1, cutoff=0.82)
            if not close:
                continue
            idx = csv_names_low.index(close[0])

        merged = existing_df.iloc[idx].to_dict()

        for col in ("runs", "average", "strike_rate", "hundreds",
                    "fifties", "wickets", "bowling_avg", "economy"):
            if api_stats.get(col) is not None:
                merged[col] = api_stats[col]

        # Propagate run delta to 2024_runs
        if "runs" in api_stats:
            api_runs = int(api_stats["runs"])
            old_runs = int(merged.get("runs", 0))
            if api_runs > old_runs:
                merged["2024_runs"] = int(merged.get("2024_runs", 0)) + (api_runs - old_runs)
                merged["runs"] = api_runs

        rows.append(merged)

    if not rows:
        logger.warning("Name-matching produced 0 rows — falling back.")
        return None

    result = pd.DataFrame(rows)
    logger.info("API update: matched %d / %d players.", len(rows), len(existing_df))
    return result


def _extract_match_ids(data: dict) -> list:
    ids = []
    try:
        for tg in (data.get("typeMatches") or
                   data.get("data", {}).get("typeMatches") or []):
            for sg in tg.get("seriesMatches") or []:
                for m in (sg.get("seriesAdWrapper", {}).get("matches") or
                          sg.get("matches") or []):
                    mid = (m.get("matchInfo", {}).get("matchId") or
                           m.get("matchId") or m.get("id"))
                    if mid:
                        ids.append(str(mid))
    except Exception as exc:
        logger.debug("Match ID extraction: %s", exc)
    return ids


def _parse_scorecard(sc: dict, collected: dict) -> None:
    try:
        for inn in (sc.get("scoreCard") or
                    sc.get("data", {}).get("scoreCard") or []):
            # Batting
            bat = (inn.get("batTeamDetails", {}).get("batsmenData") or
                   inn.get("battingData") or {})
            for e in (bat.values() if isinstance(bat, dict) else bat):
                name = (_pick(e, ["batName", "name"]) or "").strip().lower()
                runs = int(e.get("runs") or e.get("r") or 0)
                if name:
                    collected.setdefault(name, {"name": name})
                    collected[name]["match_runs_recent"] = (
                        int(collected[name].get("match_runs_recent", 0)) + runs
                    )
            # Bowling
            bowl = (inn.get("bowlTeamDetails", {}).get("bowlersData") or
                    inn.get("bowlingData") or {})
            for e in (bowl.values() if isinstance(bowl, dict) else bowl):
                name = (_pick(e, ["bowlName", "name"]) or "").strip().lower()
                wkts = int(e.get("wickets") or e.get("w") or 0)
                if name:
                    collected.setdefault(name, {"name": name})
                    collected[name]["match_wkts_recent"] = (
                        int(collected[name].get("match_wkts_recent", 0)) + wkts
                    )
    except Exception as exc:
        logger.debug("Scorecard parse: %s", exc)


# =============================================================================
# STEP 3 — SIMULATE UPDATE  (fallback)
# =============================================================================

def simulate_update(sport: str, df: pd.DataFrame) -> pd.DataFrame:
    """Weekly-seeded stat deltas. Same week = same increments (idempotent)."""
    iso_year, iso_week, _ = datetime.date.today().isocalendar()
    week_seed = f"{iso_year}W{iso_week:02d}"
    # Cast all numeric columns to float to allow mixed int/float assignments
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    numeric_cols = df.select_dtypes(include="number").columns
    updated = df.copy()
    updated[numeric_cols] = updated[numeric_cols].astype(float)

    for idx, row in updated.iterrows():
        pid  = str(row.get("player_id", idx))
        seed = int(hashlib.md5(f"{pid}{week_seed}".encode()).hexdigest()[:8], 16)
        rng  = random.Random(seed)

        if sport == "cricket":
            role = str(row.get("role", "Batsman"))
<<<<<<< HEAD
            updated.at[idx, "matches"] = float(int(row["matches"]) + rng.randint(1, 3))
            if role in ("Batsman", "All-Rounder", "Wicket-Keeper"):
                new_inn = int(row["innings"]) + rng.randint(1, 3)
                updated.at[idx, "innings"] = float(new_inn)
                avg = max(float(row.get("average", 30)), 1.0)
                rdelta = max(0, min(int(rng.gauss(avg * 1.2, avg * 0.5)), 250))
                new_runs = int(row["runs"]) + rdelta
                updated.at[idx, "runs"]      = float(new_runs)
                updated.at[idx, "2024_runs"] = float(int(row.get("2024_runs", 0)) + rdelta)
=======
            updated.at[idx, "matches"] = int(row["matches"]) + rng.randint(1, 3)

            if role in ("Batsman", "All-Rounder", "Wicket-Keeper"):
                new_inn = int(row["innings"]) + rng.randint(1, 3)
                updated.at[idx, "innings"] = new_inn
                avg = max(float(row.get("average", 30)), 1)
                rdelta = max(0, min(int(rng.gauss(avg * 1.2, avg * 0.5)), 250))
                new_runs = int(row["runs"]) + rdelta
                updated.at[idx, "runs"]      = new_runs
                updated.at[idx, "2024_runs"] = int(row.get("2024_runs", 0)) + rdelta
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
                if new_inn > 0:
                    updated.at[idx, "average"] = round(new_runs / new_inn, 2)
                updated.at[idx, "strike_rate"] = round(
                    max(40.0, float(row.get("strike_rate", 80)) + rng.uniform(-1.5, 1.5)), 1)
<<<<<<< HEAD
            if role in ("Bowler", "All-Rounder"):
                updated.at[idx, "wickets"] = float(int(row.get("wickets", 0)) + rng.randint(0, 8))
=======

            if role in ("Bowler", "All-Rounder"):
                updated.at[idx, "wickets"] = int(row.get("wickets", 0)) + rng.randint(0, 8)
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
                updated.at[idx, "economy"] = round(
                    max(2.0, float(row.get("economy", 4)) + rng.uniform(-0.1, 0.1)), 2)

        elif sport == "football":
            pos = str(row.get("position", "Forward"))
<<<<<<< HEAD
            updated.at[idx, "matches"] = float(int(row["matches"]) + rng.randint(1, 2))
            if pos == "Goalkeeper":
                updated.at[idx, "clean_sheets"] = float(int(row.get("clean_sheets", 0)) + rng.randint(0, 1))
                updated.at[idx, "saves"]        = float(int(row.get("saves", 0)) + rng.randint(0, 5))
            else:
                gd = rng.randint(0, 3) if pos == "Forward" else rng.randint(0, 1) if pos == "Midfielder" else 0
                ad = rng.randint(0, 2) if pos != "Defender" else rng.randint(0, 1)
                updated.at[idx, "goals"]      = float(int(row["goals"]) + gd)
                updated.at[idx, "assists"]    = float(int(row["assists"]) + ad)
                updated.at[idx, "2024_goals"] = float(int(row.get("2024_goals", 0)) + gd)
                updated.at[idx, "xG"] = round(max(0.0, float(row.get("xG",0)) + rng.uniform(-0.03,0.03)), 3)
                updated.at[idx, "xA"] = round(max(0.0, float(row.get("xA",0)) + rng.uniform(-0.02,0.02)), 3)
                updated.at[idx, "pass_accuracy"] = round(
                    max(60.0, min(99.0, float(row.get("pass_accuracy",80)) + rng.uniform(-0.5,0.5))), 1)
=======
            updated.at[idx, "matches"] = int(row["matches"]) + rng.randint(1, 2)
            if pos == "Goalkeeper":
                updated.at[idx, "clean_sheets"] = int(row.get("clean_sheets", 0)) + rng.randint(0, 1)
                updated.at[idx, "saves"]        = int(row.get("saves", 0)) + rng.randint(0, 5)
            else:
                gd = rng.randint(0, 3) if pos == "Forward" else rng.randint(0, 1) if pos == "Midfielder" else 0
                ad = rng.randint(0, 2) if pos != "Defender" else rng.randint(0, 1)
                updated.at[idx, "goals"]      = int(row["goals"]) + gd
                updated.at[idx, "assists"]    = int(row["assists"]) + ad
                updated.at[idx, "2024_goals"] = int(row.get("2024_goals", 0)) + gd
                updated.at[idx, "xG"] = round(max(0.0, float(row.get("xG", 0)) + rng.uniform(-0.03, 0.03)), 3)
                updated.at[idx, "xA"] = round(max(0.0, float(row.get("xA", 0)) + rng.uniform(-0.02, 0.02)), 3)
                updated.at[idx, "pass_accuracy"] = round(
                    max(60.0, min(99.0, float(row.get("pass_accuracy", 80)) + rng.uniform(-0.5, 0.5))), 1)
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca

        updated.at[idx, "form_score"] = round(
            max(50.0, min(100.0, float(row.get("form_score", 75)) + rng.uniform(-4.0, 4.0))), 1)

    return updated


<<<<<<< HEAD
# ══════════════════════════════════════════════════════════════════════════════
# MERGE DATA
# ══════════════════════════════════════════════════════════════════════════════
def merge_data(existing: pd.DataFrame, fresh: pd.DataFrame,
               id_col: str = "player_id") -> pd.DataFrame:
    """Monotone safe merge — stats never go backwards, no unknown players added."""
=======
# =============================================================================
# STEP 4 — MERGE DATA  (monotone, non-destructive)
# =============================================================================

def merge_data(existing: pd.DataFrame, fresh: pd.DataFrame,
               id_col: str = "player_id") -> pd.DataFrame:
    """Safe merge: stats never go backwards, unknown players never added."""
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    if fresh is None or fresh.empty:
        return existing

    existing = existing.copy()
    now_ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    MONOTONE = {
<<<<<<< HEAD
        "matches","innings","runs","wickets","hundreds","fifties",
        "catches","stumpings","clean_sheets","saves",
=======
        "matches", "innings", "runs", "wickets", "hundreds", "fifties",
        "catches", "stumpings", "clean_sheets", "saves",
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
        "2019_runs","2020_runs","2021_runs","2022_runs","2023_runs","2024_runs",
        "2019_goals","2020_goals","2021_goals","2022_goals","2023_goals","2024_goals",
    }
    DRIFTABLE = {
<<<<<<< HEAD
        "average","strike_rate","bowling_avg","economy",
        "pass_accuracy","xG","xA","shots_per_game","form_score",
=======
        "average", "strike_rate", "bowling_avg", "economy",
        "pass_accuracy", "xG", "xA", "shots_per_game", "form_score",
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    }

    existing.set_index(id_col, inplace=True)
    if id_col in fresh.columns:
        fresh_idx = fresh.set_index(id_col)
        for pid in existing.index:
            if pid not in fresh_idx.index:
                continue
            frow = fresh_idx.loc[pid]
            for col in frow.index:
                if col not in existing.columns:
                    continue
                fval, oval = frow[col], existing.at[pid, col]
                if col in MONOTONE:
                    try:
<<<<<<< HEAD
                        existing.at[pid, col] = max(int(oval), int(float(fval)))
=======
                        existing.at[pid, col] = max(int(oval), int(fval))
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
                    except (TypeError, ValueError):
                        pass
                elif col in DRIFTABLE:
                    try:
                        existing.at[pid, col] = round(float(fval), 3)
                    except (TypeError, ValueError):
                        pass

    existing.reset_index(inplace=True)
    existing["last_updated"] = now_ts
    return existing


<<<<<<< HEAD
# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
def update_data(sport: str) -> dict:
    """Run full pipeline: fetch → fallback → merge → backup → save."""
=======
# =============================================================================
# STEP 5 — MAIN ORCHESTRATOR
# =============================================================================

def update_data(sport: str) -> dict:
    """Run the full pipeline and persist results to CSV."""
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    csv_path = CRICKET_CSV if sport == "cricket" else FOOTBALL_CSV
    now_str  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if not os.path.exists(csv_path):
<<<<<<< HEAD
            return _err(sport, "CSV file not found.", now_str)

        existing_df = pd.read_csv(csv_path).fillna(0)
        fresh_df    = fetch_from_api(sport, existing_df)
        source      = "cricbuzz_api"
=======
            return _error_result(sport, "CSV file not found.", now_str)

        existing_df = pd.read_csv(csv_path).fillna(0)

        fresh_df = fetch_from_api(sport, existing_df)
        source   = "cricbuzz_api"
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca

        if fresh_df is None:
            fresh_df = simulate_update(sport, existing_df)
            source   = "simulated"

        merged_df = merge_data(existing_df, fresh_df)
<<<<<<< HEAD
        _backup(csv_path, sport)
        merged_df.to_csv(csv_path, index=False)

        label = "Cricbuzz API 🌐" if source == "cricbuzz_api" else "Simulation 🔧"
        return {
            "success": True, "source": source, "sport": sport,
            "rows": len(merged_df), "timestamp": now_str,
            "message": f"✅ {sport.title()} updated via {label} — {len(merged_df)} players at {now_str}",
            "error": None,
        }
    except Exception as exc:
        logger.exception("update_data[%s] failed: %s", sport, exc)
        return _err(sport, str(exc), now_str)


# ══════════════════════════════════════════════════════════════════════════════
# SCHEDULER
# ══════════════════════════════════════════════════════════════════════════════
def auto_update_if_needed(sport: str, max_age_days: int = 7):
    """Trigger update only if data is older than max_age_days."""
=======
        _write_backup(csv_path, sport)
        merged_df.to_csv(csv_path, index=False)

        label = "Cricbuzz Live API 🌐" if source == "cricbuzz_api" else "Simulation 🔧"
        logger.info("update_data[%s]: %d rows saved from %s.", sport, len(merged_df), source)

        return {
            "success":   True,
            "source":    source,
            "sport":     sport,
            "rows":      len(merged_df),
            "timestamp": now_str,
            "message":   f"✅ {sport.title()} updated via {label} — {len(merged_df)} players refreshed at {now_str}",
            "error":     None,
        }

    except Exception as exc:
        logger.exception("update_data[%s] failed: %s", sport, exc)
        return _error_result(sport, str(exc), now_str)


# =============================================================================
# AUTO-UPDATE  (weekly scheduler / cron hook)
# =============================================================================

def auto_update_if_needed(sport: str, max_age_days: int = 7):
    """
    Trigger update only if data is older than max_age_days.

    Cron (daily at 06:00 AM):
        0 6 * * * cd /path/to/sports_profiler && python -m api.update_data cricket
        5 6 * * * cd /path/to/sports_profiler && python -m api.update_data football
    """
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    csv_path = CRICKET_CSV if sport == "cricket" else FOOTBALL_CSV
    try:
        df = pd.read_csv(csv_path)
        if "last_updated" not in df.columns:
            return update_data(sport)
        latest = df["last_updated"].replace(0, pd.NA).dropna().max()
        if pd.isna(latest):
            return update_data(sport)
        dt = datetime.datetime.strptime(str(latest), "%Y-%m-%d %H:%M:%S")
        if (datetime.datetime.now() - dt).days >= max_age_days:
            return update_data(sport)
        return None
    except Exception:
        return update_data(sport)


<<<<<<< HEAD
# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_last_update_timestamp(sport: str) -> str:
    csv_path = CRICKET_CSV if sport == "cricket" else FOOTBALL_CSV
    try:
        df = pd.read_csv(csv_path, usecols=["last_updated"])
=======
# =============================================================================
# SIDEBAR HELPERS  (called by app.py)
# =============================================================================

def get_last_update_timestamp(sport: str) -> str:
    csv_path = CRICKET_CSV if sport == "cricket" else FOOTBALL_CSV
    try:
        df     = pd.read_csv(csv_path, usecols=["last_updated"])
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
        latest = df["last_updated"].replace(0, pd.NA).dropna().max()
        return str(latest) if not pd.isna(latest) else "Never"
    except Exception:
        return "Never"


def get_data_age_days(sport: str):
    ts = get_last_update_timestamp(sport)
    if ts == "Never":
        return None
    try:
        dt = datetime.datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
        return (datetime.datetime.now() - dt).days
    except Exception:
        return None


<<<<<<< HEAD
def _backup(csv_path: str, sport: str) -> None:
=======
# =============================================================================
# INTERNAL UTILITIES
# =============================================================================

def _si(target, key, source, fields):
    """Safe set int from first matching field."""
    for f in fields:
        v = source.get(f)
        if v is not None and str(v).strip() not in ("", "-", "N/A"):
            try:
                target[key] = int(float(str(v).replace(",", "")))
                return
            except (ValueError, TypeError):
                continue


def _sf(target, key, source, fields):
    """Safe set float from first matching field."""
    for f in fields:
        v = source.get(f)
        if v is not None and str(v).strip() not in ("", "-", "N/A"):
            try:
                target[key] = round(float(str(v).replace(",", "")), 3)
                return
            except (ValueError, TypeError):
                continue


def _pick(d: dict, fields: list):
    """Return first non-empty value from dict d by field list."""
    for f in fields:
        v = d.get(f)
        if v:
            return v
    return None


def _dig(d: dict, paths: list, default=None):
    """Try multiple dot-notation paths on a dict, return first hit."""
    for path in paths:
        obj = d
        try:
            for part in path.split("."):
                obj = obj[part]
            if obj is not None:
                return obj
        except (KeyError, TypeError):
            continue
    return default


def _write_backup(csv_path: str, sport: str) -> None:
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(csv_path, os.path.join(_BACKUP_DIR, f"{sport}_{ts}.csv"))
    old = sorted([f for f in os.listdir(_BACKUP_DIR) if f.startswith(sport)], reverse=True)
    for f in old[10:]:
        try:
            os.remove(os.path.join(_BACKUP_DIR, f))
        except OSError:
            pass


<<<<<<< HEAD
def _err(sport, error, ts):
    return {"success": False, "source": "none", "sport": sport,
            "rows": 0, "timestamp": ts,
            "message": f"❌ Update failed ({sport}): {error}", "error": error}


=======
def _error_result(sport, error, ts):
    return {
        "success": False, "source": "none", "sport": sport,
        "rows": 0, "timestamp": ts,
        "message": f"❌ Update failed ({sport}): {error}",
        "error": error,
    }


# ── CLI entry-point ───────────────────────────────────────────────────────────
>>>>>>> 769e80c07d40e4d90988c562afa97301d7cf07ca
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(levelname)s │ %(message)s")
    arg = sys.argv[1] if len(sys.argv) > 1 else "cricket"
    if arg not in ("cricket", "football"):
        print("Usage: python update_data.py [cricket|football]")
        sys.exit(1)
    r = update_data(arg)
    print(r["message"])
    sys.exit(0 if r["success"] else 1)
