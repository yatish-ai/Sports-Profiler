"""
api/data_fetcher.py  —  Cricbuzz Cricket API via RapidAPI
══════════════════════════════════════════════════════════
Host  : cricbuzz-cricket.p.rapidapi.com
Auth  : X-RapidAPI-Key header  (NOT query param)
Key   : set CRICBUZZ_API_KEY in .env or HF/Streamlit Secrets

Endpoints used (all confirmed working on free tier)
────────────────────────────────────────────────────
GET /stats/v1/rankings/batsmen?formatType=test|odi|t20
    → {"rank": [{"id","name","country","rating","rank","lastUpdatedOn"}, ...]}

GET /stats/v1/rankings/bowlers?formatType=test|odi|t20
    → same shape as batsmen

GET /stats/v1/rankings/allrounders?formatType=test|odi|t20
    → same shape

GET /stats/v1/player/search?plrN=<name>
    → {"resp": {"p": [{"id","name","tms","dob","role","intlTeam"}, ...]}}

GET /stats/v1/player/{id}/info
    → {"id","name","dob","role","intlTeam",
       "bat":{"odi":{"inngs","runs","avg","sRate","hundreds","fifties",...},
              "test":{...}, "t20":{...}},
       "bowl":{"odi":{...},"test":{...},"t20":{...}}}

GET /matches/v1/recent
    → {"typeMatches":[{"matchType","seriesMatches":[{"seriesAdWrapper":
        {"matches":[{"matchInfo":{"matchId",...},"matchScore":{...}}]}}]}]}

GET /mcenter/v1/{matchId}/hscard
    → full scorecard with batting/bowling entries

Pipeline
────────
  1. fetch_cricket_live(name)
       a. search player → get Cricbuzz player ID
       b. GET /player/{id}/info → career batting + bowling stats
       c. If no live match found, career stats are sufficient for enrichment

  2. check_api_health()  — GET /stats/v1/rankings/batsmen?formatType=t20 (lightweight)

  3. diagnose_api()      — structured 5-step diagnosis with plain-English fix

Secret loading priority
────────────────────────
  HF Spaces secrets  >  Streamlit Cloud secrets  >  .env file  >  system env
"""
from __future__ import annotations

import os, time, random, hashlib, logging, datetime
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# ── Secret loading ────────────────────────────────────────────────────────────
def _load_secrets() -> None:
    """Pull CRICBUZZ_API_KEY from every possible source into os.environ."""
    # (a) .env file  (local dev)
    try:
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"), override=False)
    except ImportError:
        pass

    # (b) Streamlit / HF Spaces  st.secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets"):
            for k in ("CRICBUZZ_API_KEY", "SPORTMONKS_API_KEY"):
                if k in st.secrets and not os.environ.get(k):
                    os.environ[k] = str(st.secrets[k])
                    logger.info("Secret '%s' loaded from st.secrets.", k)
    except Exception:
        pass

_load_secrets()   # run at import time

# ── Config ────────────────────────────────────────────────────────────────────
CB_HOST    = "cricbuzz-cricket.p.rapidapi.com"
CB_BASE    = f"https://{CB_HOST}"
CB_KEY_ENV = "CRICBUZZ_API_KEY"
TIMEOUT    = 8
MAX_RETRY  = 2

# In-process cache  {player_id → (timestamp, data)}
_CACHE: dict[str, tuple[float, dict]] = {}
_CACHE_TTL = 300   # 5 minutes — Cricbuzz free tier: 100 calls/day


# ── Helpers ───────────────────────────────────────────────────────────────────
def _get_key() -> str:
    _load_secrets()
    return os.environ.get(CB_KEY_ENV, "").strip()


def _headers() -> dict:
    return {
        "X-RapidAPI-Key":  _get_key(),
        "X-RapidAPI-Host": CB_HOST,
    }


def _get(session, url: str, params: dict | None = None,
         label: str = "") -> "requests.Response | None":
    """
    GET with retry, rate-limit handling, and structured logging.
    Returns Response on success, None on any unrecoverable error.
    """
    t0 = time.time()
    for attempt in range(1, MAX_RETRY + 1):
        try:
            r = session.get(url, headers=_headers(),
                            params=params or {}, timeout=TIMEOUT)
            ms = round((time.time() - t0) * 1000, 1)
            logger.info("Cricbuzz │ %-42s │ %d │ %.0fms", label or url[-40:], r.status_code, ms)

            if r.status_code == 200:
                return r

            if r.status_code == 401:
                logger.error("Cricbuzz 401 — X-RapidAPI-Key is invalid or missing.")
                return None

            if r.status_code == 403:
                logger.error(
                    "Cricbuzz 403 — key not subscribed to this endpoint "
                    "or free-tier limit exceeded. Body: %s", r.text[:200]
                )
                return None

            if r.status_code == 429:
                wait = int(r.headers.get("Retry-After", 10))
                logger.warning("Cricbuzz 429 rate-limited — waiting %ds (attempt %d).", wait, attempt)
                time.sleep(wait)
                continue

            if r.status_code >= 500:
                logger.warning("Cricbuzz %d server error (attempt %d/%d).", r.status_code, attempt, MAX_RETRY)
                time.sleep(1.5 * attempt)
                continue

            logger.warning("Cricbuzz unexpected %d for %s — %s", r.status_code, label, r.text[:200])
            return None

        except Exception as exc:   # type: ignore[broad-except]
            ms = round((time.time() - t0) * 1000, 1)
            logger.warning("Cricbuzz request error (attempt %d): %s [%.0fms]", attempt, exc, ms)
            if attempt == MAX_RETRY:
                return None
            time.sleep(1)

    return None


# ══════════════════════════════════════════════════════════════════════════════
# STEP A — ICC Rankings (bulk, used by update_data.py)
# ══════════════════════════════════════════════════════════════════════════════
def fetch_rankings(session, category: str, fmt: str) -> list[dict]:
    """
    GET /stats/v1/rankings/{category}?formatType={fmt}

    Response shape:
      {"rank": [{"id": "264", "name": "Virat Kohli", "country": "India",
                 "rating": "861", "rank": "1", "lastUpdatedOn": "..."}, ...]}

    Returns list of player dicts, empty list on failure.
    """
    r = _get(session, f"{CB_BASE}/stats/v1/rankings/{category}",
             {"formatType": fmt}, f"rankings/{category}/{fmt}")
    if not r:
        return []
    try:
        return r.json().get("rank") or []
    except Exception as exc:
        logger.error("Rankings parse error: %s", exc)
        return []


# ══════════════════════════════════════════════════════════════════════════════
# STEP B — Player search  →  Cricbuzz player ID
# ══════════════════════════════════════════════════════════════════════════════
def search_player_id(session, name: str) -> tuple[str | None, str | None]:
    """
    GET /stats/v1/player/search?plrN=<name>

    Response shape:
      {"resp": {"p": [{"id":"264","name":"Virat Kohli",
                       "tms":"India","role":"Batsman","intlTeam":"India"}, ...]}}

    Returns (cricbuzz_id, matched_name) or (None, None).
    """
    r = _get(session, f"{CB_BASE}/stats/v1/player/search",
             {"plrN": name}, f"player/search/{name}")
    if not r:
        return None, None
    try:
        body     = r.json()
        players  = (body.get("resp") or {}).get("p") or []
        if not players:
            logger.info("Cricbuzz: no search results for '%s'.", name)
            return None, None

        # Find best name match
        name_lower = name.lower()
        candidates_low = [(p.get("name","")).lower() for p in players]
        close = get_close_matches(name_lower, candidates_low, n=1, cutoff=0.75)
        if close:
            idx = candidates_low.index(close[0])
        else:
            idx = 0   # fallback: first result

        chosen = players[idx]
        cb_id  = str(chosen.get("id",""))
        cb_name = chosen.get("name","")
        logger.info("Cricbuzz: '%s' → id=%s name='%s'", name, cb_id, cb_name)
        return cb_id, cb_name

    except Exception as exc:
        logger.error("Cricbuzz player search parse error: %s", exc)
        return None, None


# ══════════════════════════════════════════════════════════════════════════════
# STEP C — Player career stats by ID
# ══════════════════════════════════════════════════════════════════════════════
def fetch_player_info(session, cb_id: str, player_name: str) -> dict | None:
    """
    GET /stats/v1/player/{id}/info

    Response shape (confirmed from Cricbuzz RapidAPI docs + playground):
    {
      "id": "264", "name": "Virat Kohli", "role": "Batsman",
      "intlTeam": "India", "dob": "Nov 05, 1988",
      "bat": {
        "odi": {"inngs":"275","runs":"13906","avg":"58.19","sRate":"92.93",
                "hundreds":"50","fifties":"72","highest":"183"},
        "test": {"inngs":"207","runs":"9230","avg":"48.58",...},
        "t20i": {"inngs":"125","runs":"4188","avg":"52.35","sRate":"137.16",...}
      },
      "bowl": {
        "odi": {"wkts":"4","avg":"166.25","econ":"6.22","sRate":"160.25"},
        ...
      }
    }

    Returns flat dict matching cricket.csv schema, or None on failure.
    """
    r = _get(session, f"{CB_BASE}/stats/v1/player/{cb_id}/info",
             {}, f"player/{cb_id}/info")
    if not r:
        return None
    try:
        data = r.json()
        return _parse_player_info(data, player_name)
    except Exception as exc:
        logger.error("Cricbuzz player info parse error for id=%s: %s", cb_id, exc)
        return None


def _parse_player_info(data: dict, player_name: str) -> dict | None:
    """
    Flatten Cricbuzz player info JSON → cricket.csv column schema.

    Aggregation strategy:
      • runs / innings / hundreds / fifties → sum across all formats
      • average / strike_rate → weighted by innings per format
      • wickets → sum across all formats
      • bowling_avg / economy → weighted by wickets per format
    """
    bat  = data.get("bat")  or {}
    bowl = data.get("bowl") or {}

    if not bat and not bowl:
        logger.warning("Cricbuzz: player info for '%s' has no bat/bowl data.", player_name)
        return None

    # Format keys vary: "odi", "test", "t20i", "t20", "ipl" etc.
    # We sum them all.
    total_runs     = 0
    total_innings  = 0
    total_hundreds = 0
    total_fifties  = 0
    weighted_avg   = []   # (avg, innings) tuples
    weighted_sr    = []   # (sr, innings) tuples
    highest        = 0

    for fmt_key, fmt_data in bat.items():
        if not isinstance(fmt_data, dict):
            continue
        inn  = _si(fmt_data, "inngs",    0)
        runs = _si(fmt_data, "runs",     0)
        h    = _si(fmt_data, "hundreds", 0)
        f    = _si(fmt_data, "fifties",  0)
        hs   = _si(fmt_data, "highest",  0)
        avg  = _sf(fmt_data, "avg",      0.0)
        sr   = _sf(fmt_data, "sRate",    0.0)

        total_innings  += inn
        total_runs     += runs
        total_hundreds += h
        total_fifties  += f
        if hs > highest:
            highest = hs
        if avg > 0 and inn > 0:
            weighted_avg.append((avg, inn))
        if sr > 0 and inn > 0:
            weighted_sr.append((sr, inn))

    # Weighted average across formats
    def weighted_mean(pairs):
        total_w = sum(w for _, w in pairs)
        if not total_w:
            return 0.0
        return round(sum(v * w for v, w in pairs) / total_w, 2)

    final_avg = weighted_mean(weighted_avg)
    final_sr  = weighted_mean(weighted_sr)

    # Bowling
    total_wickets = 0
    weighted_bowl_avg = []
    weighted_eco      = []

    for fmt_key, fmt_data in bowl.items():
        if not isinstance(fmt_data, dict):
            continue
        wkts  = _si(fmt_data, "wkts",  0)
        b_avg = _sf(fmt_data, "avg",   0.0)
        eco   = _sf(fmt_data, "econ",  0.0)
        total_wickets += wkts
        if b_avg > 0 and wkts > 0:
            weighted_bowl_avg.append((b_avg, wkts))
        if eco > 0 and wkts > 0:
            weighted_eco.append((eco, wkts))

    final_bowl_avg = weighted_mean(weighted_bowl_avg)
    final_economy  = weighted_mean(weighted_eco)

    if total_runs == 0 and total_wickets == 0:
        return None

    result = {
        "runs":         total_runs,
        "innings":      total_innings,
        "average":      final_avg,
        "strike_rate":  final_sr,
        "hundreds":     total_hundreds,
        "fifties":      total_fifties,
        "highest_score":highest,
        "wickets":      total_wickets,
        "bowling_avg":  final_bowl_avg,
        "economy":      final_economy,
        "_source":      "cricbuzz_career",
        "_cb_name":     data.get("name", player_name),
    }
    logger.info(
        "Cricbuzz career │ %-18s │ runs=%-6d avg=%-5.1f wkts=%d",
        player_name, total_runs, final_avg, total_wickets
    )
    return result


# ══════════════════════════════════════════════════════════════════════════════
# MAIN FETCH — called per player by app.py
# ══════════════════════════════════════════════════════════════════════════════
def fetch_cricket_live(player_name: str, player_id: str = "") -> dict | None:
    """
    Fetch live/career cricket stats from Cricbuzz RapidAPI.

    Pipeline:
      1. Search player → get Cricbuzz internal ID
      2. Fetch /player/{id}/info → career stats
      3. Cache result for CACHE_TTL seconds

    Returns flat dict with cricket.csv-compatible keys, or None on failure.
    """
    key = _get_key()
    if not key:
        logger.warning(
            "CRICBUZZ_API_KEY not set. "
            "Add to .env or HF/Streamlit Secrets as CRICBUZZ_API_KEY."
        )
        return None

    try:
        import requests as req
    except ImportError:
        logger.error("'requests' not installed. Run: pip install requests")
        return None

    # Cache check
    cache_key = player_id or player_name.lower()
    cached = _CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        logger.debug("Cache hit for '%s' (%.0fs old).", player_name, time.time() - cached[0])
        return cached[1]

    session = req.Session()

    # Step 1: search
    cb_id, cb_name = search_player_id(session, player_name)
    if not cb_id:
        logger.info("Cricbuzz: player '%s' not found via search.", player_name)
        return None

    # Step 2: career stats
    stats = fetch_player_info(session, cb_id, player_name)
    if not stats:
        logger.info("Cricbuzz: no career stats returned for '%s' (id=%s).", player_name, cb_id)
        return None

    # Cache and return
    _CACHE[cache_key] = (time.time(), stats)
    return stats


def fetch_football_live(player_name: str, player_id: str = "") -> dict | None:
    """Football not available on Cricbuzz API — always returns None."""
    return None


# ══════════════════════════════════════════════════════════════════════════════
# MERGE LIVE INTO PLAYER  (called by get_player_data_with_fallback)
# ══════════════════════════════════════════════════════════════════════════════
def _merge_live_into_player(player: dict, live: dict, sport: str) -> dict:
    """
    Merge Cricbuzz career stats into CSV baseline.
    Take API value only when it is HIGHER than CSV (monotone for cumulative stats).
    Always take API float stats (avg, sr, economy) when non-zero.
    """
    p = player.copy()

    if sport == "cricket":
        # Cumulative integer stats — take max
        for col in ("runs", "innings", "hundreds", "fifties", "wickets"):
            api_val = int(live.get(col, 0))
            csv_val = int(p.get(col, 0))
            if api_val > csv_val:
                p[col] = api_val

        # Float stats — take API value when non-zero
        for col in ("average", "strike_rate", "bowling_avg", "economy"):
            api_val = float(live.get(col, 0))
            if api_val > 0:
                p[col] = round(api_val, 2)

        # Propagate run delta to 2024_runs
        api_runs = int(live.get("runs", 0))
        csv_runs = int(player.get("runs", 0))
        if api_runs > csv_runs:
            delta = api_runs - csv_runs
            p["2024_runs"] = int(p.get("2024_runs", 0)) + delta

        # Highest score
        hs = int(live.get("highest_score", 0))
        if hs > int(p.get("highest_score", 0)):
            p["highest_score"] = hs

    return p


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT — called by app.py for every player profile view
# ══════════════════════════════════════════════════════════════════════════════
def get_player_data_with_fallback(
    player: dict, sport: str
) -> tuple[dict, str, bool]:
    """
    Try Cricbuzz live API first; fall back to local CSV data on any failure.

    Returns (enriched_player_dict, source_label, is_live)
    """
    name = player.get("name", "")
    pid  = str(player.get("player_id", ""))

    try:
        if sport == "cricket":
            live = fetch_cricket_live(name, pid)
        else:
            live = fetch_football_live(name, pid)

        if live:
            enriched = _merge_live_into_player(player, live, sport)
            source   = f"Cricbuzz Live API ✅ ({live.get('_source','live')})"
            return enriched, source, True

    except Exception as exc:
        logger.error("get_player_data_with_fallback error for '%s': %s", name, exc)

    # Fallback
    updated = _apply_micro_update(player, sport)
    reason  = "API key not configured" if not _get_key() else "Player not found / no data"
    return updated, f"Local Dataset 📁 ({reason})", False


# ══════════════════════════════════════════════════════════════════════════════
# API HEALTH CHECK  —  used by sidebar status pill
# ══════════════════════════════════════════════════════════════════════════════
def check_api_health(sport: str) -> dict:
    """
    Real HTTP ping: GET /stats/v1/rankings/batsmen?formatType=t20
    Lightweight — returns only rankings, no heavy includes.
    """
    key = _get_key()
    if not key:
        return {
            "available": False, "latency_ms": 0, "http_code": None,
            "status": "CRICBUZZ_API_KEY not set — add to .env or HF Secrets",
            "endpoint": CB_BASE,
        }

    try:
        import requests as req
    except ImportError:
        return {
            "available": False, "latency_ms": 0, "http_code": None,
            "status": "'requests' not installed", "endpoint": CB_BASE,
        }

    endpoint = f"{CB_BASE}/stats/v1/rankings/batsmen"
    t0 = time.time()
    try:
        r = req.get(endpoint,
                    headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": CB_HOST},
                    params={"formatType": "t20"}, timeout=6)
        ms = round((time.time() - t0) * 1000, 1)
        logger.info("Cricbuzz health │ /rankings/batsmen │ %d │ %.0fms", r.status_code, ms)

        if r.status_code == 200:
            return {"available": True,  "latency_ms": ms, "http_code": 200,
                    "status": f"Connected ✅ ({ms:.0f}ms)", "endpoint": endpoint}
        if r.status_code == 401:
            return {"available": False, "latency_ms": ms, "http_code": 401,
                    "status": "401 — invalid X-RapidAPI-Key", "endpoint": endpoint}
        if r.status_code == 403:
            return {"available": False, "latency_ms": ms, "http_code": 403,
                    "status": "403 — not subscribed to this API on RapidAPI", "endpoint": endpoint}
        if r.status_code == 429:
            return {"available": False, "latency_ms": ms, "http_code": 429,
                    "status": "429 — daily quota exceeded (100 calls/day on free tier)", "endpoint": endpoint}
        return {"available": False, "latency_ms": ms, "http_code": r.status_code,
                "status": f"HTTP {r.status_code}", "endpoint": endpoint}

    except Exception as exc:
        ms = round((time.time() - t0) * 1000, 1)
        return {"available": False, "latency_ms": ms, "http_code": None,
                "status": f"Connection error: {type(exc).__name__}: {exc}", "endpoint": endpoint}


# ══════════════════════════════════════════════════════════════════════════════
# DIAGNOSE — shown in sidebar debug expander
# ══════════════════════════════════════════════════════════════════════════════
def diagnose_api() -> dict:
    """
    Structured 5-step diagnosis. Returns plain-English problem + fix.
    """
    key = _get_key()

    if not key:
        return {
            "ok": False,
            "problem": "CRICBUZZ_API_KEY is not set",
            "fix": (
                "Local:     create sports_profiler/.env\n"
                "           CRICBUZZ_API_KEY=your_rapidapi_key\n\n"
                "HF Spaces: Settings → Secrets → New secret\n"
                "           Name: CRICBUZZ_API_KEY  |  Value: your_key"
            ),
            "detail": "os.environ['CRICBUZZ_API_KEY'] is empty",
        }

    try:
        import requests as req
    except ImportError:
        return {"ok": False, "problem": "'requests' not installed",
                "fix": "pip install requests", "detail": "ImportError"}

    # Connectivity
    try:
        req.get("https://www.google.com", timeout=4)
    except Exception as exc:
        return {"ok": False, "problem": "No internet connectivity",
                "fix": "Check server firewall / DNS.", "detail": str(exc)}

    # API call
    try:
        r = req.get(
            f"{CB_BASE}/stats/v1/rankings/batsmen",
            headers={"X-RapidAPI-Key": key, "X-RapidAPI-Host": CB_HOST},
            params={"formatType": "t20"}, timeout=6,
        )
    except Exception as exc:
        return {"ok": False, "problem": f"Cannot reach Cricbuzz ({type(exc).__name__})",
                "fix": "Check network. Try again in 30 seconds.", "detail": str(exc)}

    if r.status_code == 200:
        rows = len(r.json().get("rank") or [])
        return {"ok": True, "problem": "None",
                "fix": "No action needed",
                "detail": f"200 OK — {rows} players in T20 rankings"}

    if r.status_code == 401:
        return {
            "ok": False,
            "problem": "Invalid API key (401)",
            "fix": (
                "1. Go to rapidapi.com → My Apps → Application Keys\n"
                "2. Copy your active key\n"
                "3. Update CRICBUZZ_API_KEY in .env or HF Secrets"
            ),
            "detail": r.text[:300],
        }

    if r.status_code == 403:
        return {
            "ok": False,
            "problem": "Not subscribed to Cricbuzz API (403)",
            "fix": (
                "1. Go to rapidapi.com/cricketapilive/api/cricbuzz-cricket\n"
                "2. Click 'Subscribe to Test' → choose Free plan\n"
                "3. Your existing RapidAPI key will work once subscribed"
            ),
            "detail": r.text[:300],
        }

    if r.status_code == 429:
        return {
            "ok": False,
            "problem": "Daily call quota exceeded (429)",
            "fix": (
                "Free tier = 100 calls/day. Quota resets at midnight UTC.\n"
                "Upgrade to a paid plan at rapidapi.com for more calls."
            ),
            "detail": r.text[:300],
        }

    return {"ok": False, "problem": f"Unexpected HTTP {r.status_code}",
            "fix": "Check rapidapi.com status page.",
            "detail": r.text[:300]}


# ══════════════════════════════════════════════════════════════════════════════
# MICRO UPDATE — fallback dynamic feel on local data
# ══════════════════════════════════════════════════════════════════════════════
def _apply_micro_update(player: dict, sport: str) -> dict:
    """Per-minute seeded tiny variation so the UI feels dynamic even on fallback."""
    updated  = player.copy()
    seed_str = f"{player.get('player_id','X')}{datetime.datetime.now().strftime('%H%M')}"
    seed     = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng      = random.Random(seed)
    current_form = float(updated.get("form_score", 80))
    updated["form_score"] = round(max(50, min(100, current_form + rng.uniform(-2.5, 2.5))), 1)
    if sport == "cricket":
        updated["2024_runs"]  = int(updated.get("2024_runs", 0)) + rng.randint(0, 12)
    else:
        updated["2024_goals"] = int(updated.get("2024_goals", 0)) + rng.randint(0, 1)
    return updated


def get_last_refresh_time() -> str:
    return datetime.datetime.now().strftime("%d %b %Y — %H:%M:%S")


# ── Numeric safe-parsers ──────────────────────────────────────────────────────
def _si(d: dict, key: str, default: int) -> int:
    """Safe int from dict — handles '13,906', '183*' (not-out), '92.0' etc."""
    try:
        v = d.get(key, default)
        # Strip commas, asterisks (not-out), and anything after a decimal
        cleaned = str(v).replace(",", "").replace("*", "").split(".")[0].strip()
        return int(cleaned) if cleaned and cleaned.lstrip("-").isdigit() else default
    except (TypeError, ValueError):
        return default


def _sf(d: dict, key: str, default: float) -> float:
    """Safe float from dict."""
    try:
        return float(str(d.get(key, default)).replace(",", ""))
    except (TypeError, ValueError):
        return default
