"""
API Module - Semi-real-time data fetching with graceful fallback to local dataset.
"""
import datetime
import random
import time
import hashlib


API_ENDPOINTS = {
    "cricket": "https://api.cricketdata.org/api/v2/",       # example endpoint
    "football": "https://v3.football.api-sports.io/players", # example endpoint
}


def fetch_cricket_live(player_name: str) -> dict | None:
    """
    Attempt to fetch live cricket stats from external API.
    Returns None on failure — triggers fallback to local dataset.
    
    In production: replace with real API call using requests library.
    API key would be loaded from environment variable: os.getenv('CRICKET_API_KEY')
    """
    # Simulated API call — always "fails" gracefully to demo fallback
    # In production:
    # import requests, os
    # headers = {"x-apisports-key": os.getenv("CRICKET_API_KEY", "")}
    # resp = requests.get(f"{API_ENDPOINTS['cricket']}players?name={player_name}", headers=headers, timeout=5)
    # if resp.status_code == 200: return resp.json()
    # return None

    time.sleep(0.1)  # Simulate network latency
    return None  # Simulated failure → triggers fallback


def fetch_football_live(player_name: str) -> dict | None:
    """
    Attempt to fetch live football stats from external API.
    Returns None on failure — triggers fallback to local dataset.
    
    In production: replace with real API call.
    API key: os.getenv('FOOTBALL_API_KEY')
    """
    # Simulated API call
    # import requests, os
    # headers = {"x-rapidapi-key": os.getenv("FOOTBALL_API_KEY", "")}
    # resp = requests.get(API_ENDPOINTS["football"], headers=headers,
    #                     params={"search": player_name}, timeout=5)
    # if resp.status_code == 200: return resp.json()
    # return None

    time.sleep(0.1)
    return None  # Simulated failure → fallback to CSV


def get_player_data_with_fallback(player: dict, sport: str) -> tuple[dict, str, bool]:
    """
    Try live API first; fallback to local data if API fails.
    
    Returns:
        (player_data, source_label, is_live)
    """
    try:
        name = player.get("name", "")
        if sport == "cricket":
            live_data = fetch_cricket_live(name)
        else:
            live_data = fetch_football_live(name)

        if live_data:
            # Merge live data into player dict
            merged = {**player, **live_data}
            return merged, "Live API ✅", True
        else:
            # API failed — use local data with simulated micro-update
            updated = _apply_micro_update(player, sport)
            return updated, "Local Dataset (API Unavailable) 📁", False

    except Exception as e:
        updated = _apply_micro_update(player, sport)
        return updated, f"Local Dataset (Error: {type(e).__name__}) 📁", False


def _apply_micro_update(player: dict, sport: str) -> dict:
    """Apply tiny simulated variation to mimic real-time feel."""
    updated = player.copy()
    
    # Use player_id + current minute as seed for consistent-per-minute results
    seed_str = f"{player.get('player_id','X')}{datetime.datetime.now().strftime('%H%M')}"
    seed = int(hashlib.md5(seed_str.encode()).hexdigest()[:8], 16)
    rng = random.Random(seed)

    current_form = float(updated.get("form_score", 80))
    updated["form_score"] = round(max(50, min(100, current_form + rng.uniform(-2.5, 2.5))), 1)

    if sport == "cricket":
        runs_2024 = int(updated.get("2024_runs", 0))
        updated["2024_runs"] = runs_2024 + rng.randint(0, 12)
    
    if sport == "football":
        goals_2024 = int(updated.get("2024_goals", 0))
        updated["2024_goals"] = goals_2024 + rng.randint(0, 1)

    return updated


def check_api_health(sport: str) -> dict:
    """Check API availability and return status summary."""
    start = time.time()
    try:
        # Simulate a health check
        time.sleep(0.05)
        latency = (time.time() - start) * 1000
        # In production, do a real ping to the API endpoint
        return {
            "available": False,  # Simulated: API key not configured
            "latency_ms": round(latency, 1),
            "status": "API key not configured — running in dataset-only mode",
            "endpoint": API_ENDPOINTS.get(sport, "N/A"),
        }
    except Exception as e:
        return {
            "available": False,
            "latency_ms": 0,
            "status": f"Connection error: {e}",
            "endpoint": API_ENDPOINTS.get(sport, "N/A"),
        }


def get_last_refresh_time() -> str:
    """Return human-readable last refresh timestamp."""
    return datetime.datetime.now().strftime("%d %b %Y — %H:%M:%S")
