"""
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
from difflib import get_close_matches

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

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
    """
    if sport != "cricket":
        return None

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

    numeric_cols = df.select_dtypes(include="number").columns
    updated = df.copy()
    updated[numeric_cols] = updated[numeric_cols].astype(float)

    for idx, row in updated.iterrows():
        pid  = str(row.get("player_id", idx))
        seed = int(hashlib.md5(f"{pid}{week_seed}".encode()).hexdigest()[:8], 16)
        rng  = random.Random(seed)

        if sport == "cricket":
            role = str(row.get("role", "Batsman"))
            updated.at[idx, "matches"] = float(int(row["matches"]) + rng.randint(1, 3))
            if role in ("Batsman", "All-Rounder", "Wicket-Keeper"):
                new_inn = int(row["innings"]) + rng.randint(1, 3)
                updated.at[idx, "innings"] = float(new_inn)
                avg = max(float(row.get("average", 30)), 1.0)
                rdelta = max(0, min(int(rng.gauss(avg * 1.2, avg * 0.5)), 250))
                new_runs = int(row["runs"]) + rdelta
                updated.at[idx, "runs"]      = float(new_runs)
                updated.at[idx, "2024_runs"] = float(int(row.get("2024_runs", 0)) + rdelta)
                if new_inn > 0:
                    updated.at[idx, "average"] = round(new_runs / new_inn, 2)
                updated.at[idx, "strike_rate"] = round(
                    max(40.0, float(row.get("strike_rate", 80)) + rng.uniform(-1.5, 1.5)), 1)
            if role in ("Bowler", "All-Rounder"):
                updated.at[idx, "wickets"] = float(int(row.get("wickets", 0)) + rng.randint(0, 8))
                updated.at[idx, "economy"] = round(
                    max(2.0, float(row.get("economy", 4)) + rng.uniform(-0.1, 0.1)), 2)

        elif sport == "football":
            pos = str(row.get("position", "Forward"))
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

        updated.at[idx, "form_score"] = round(
            max(50.0, min(100.0, float(row.get("form_score", 75)) + rng.uniform(-4.0, 4.0))), 1)

    return updated


# ══════════════════════════════════════════════════════════════════════════════
# MERGE DATA
# ══════════════════════════════════════════════════════════════════════════════
def merge_data(existing: pd.DataFrame, fresh: pd.DataFrame,
               id_col: str = "player_id") -> pd.DataFrame:
    """Monotone safe merge — stats never go backwards, no unknown players added."""
    if fresh is None or fresh.empty:
        return existing

    existing = existing.copy()
    now_ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    MONOTONE = {
        "matches","innings","runs","wickets","hundreds","fifties",
        "catches","stumpings","clean_sheets","saves",
        "2019_runs","2020_runs","2021_runs","2022_runs","2023_runs","2024_runs",
        "2019_goals","2020_goals","2021_goals","2022_goals","2023_goals","2024_goals",
    }
    DRIFTABLE = {
        "average","strike_rate","bowling_avg","economy",
        "pass_accuracy","xG","xA","shots_per_game","form_score",
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
                        existing.at[pid, col] = max(int(oval), int(float(fval)))
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


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ORCHESTRATOR
# ══════════════════════════════════════════════════════════════════════════════
def update_data(sport: str) -> dict:
    """Run full pipeline: fetch → fallback → merge → backup → save."""
    csv_path = CRICKET_CSV if sport == "cricket" else FOOTBALL_CSV
    now_str  = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        if not os.path.exists(csv_path):
            return _err(sport, "CSV file not found.", now_str)

        existing_df = pd.read_csv(csv_path).fillna(0)
        fresh_df    = fetch_from_api(sport, existing_df)
        source      = "cricbuzz_api"

        if fresh_df is None:
            fresh_df = simulate_update(sport, existing_df)
            source   = "simulated"

        merged_df = merge_data(existing_df, fresh_df)
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


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR HELPERS
# ══════════════════════════════════════════════════════════════════════════════
def get_last_update_timestamp(sport: str) -> str:
    csv_path = CRICKET_CSV if sport == "cricket" else FOOTBALL_CSV
    try:
        df = pd.read_csv(csv_path, usecols=["last_updated"])
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


def _backup(csv_path: str, sport: str) -> None:
    os.makedirs(_BACKUP_DIR, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    shutil.copy2(csv_path, os.path.join(_BACKUP_DIR, f"{sport}_{ts}.csv"))
    old = sorted([f for f in os.listdir(_BACKUP_DIR) if f.startswith(sport)], reverse=True)
    for f in old[10:]:
        try:
            os.remove(os.path.join(_BACKUP_DIR, f))
        except OSError:
            pass


def _err(sport, error, ts):
    return {"success": False, "source": "none", "sport": sport,
            "rows": 0, "timestamp": ts,
            "message": f"❌ Update failed ({sport}): {error}", "error": error}


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
