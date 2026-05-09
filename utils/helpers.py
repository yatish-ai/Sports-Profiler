"""
Utils - Shared utility functions for the sports profiler app.
"""
import datetime
import random
import hashlib


def get_last_updated() -> str:
    """Return a formatted 'last updated' timestamp."""
    return datetime.datetime.now().strftime("%d %b %Y, %H:%M:%S")


def simulate_realtime_update(player: dict, sport: str) -> dict:
    """
    Simulate a real-time data update by slightly varying form scores and recent stats.
    In production this would call a live sports API.
    """
    updated = player.copy()
    seed = int(hashlib.md5(f"{player.get('player_id','')}{datetime.datetime.now().minute}".encode()).hexdigest(), 16) % 1000
    random.seed(seed)

    # Slightly vary form score ±3 points
    current_form = float(updated.get("form_score", 80))
    delta = random.uniform(-3, 3)
    updated["form_score"] = round(max(50, min(100, current_form + delta)), 1)

    # Vary 2024 stats slightly for cricket
    if sport == "cricket":
        current_runs = int(updated.get("2024_runs", 0))
        if current_runs > 0:
            updated["2024_runs"] = current_runs + random.randint(0, 15)

    # Vary 2024 goals slightly for football
    if sport == "football":
        current_goals = int(updated.get("2024_goals", 0))
        updated["2024_goals"] = current_goals + random.randint(0, 1)

    return updated


def format_market_value(value: float) -> str:
    """Format market value into readable string."""
    if value >= 1_000_000:
        return f"€{value/1_000_000:.1f}M"
    elif value >= 1_000:
        return f"€{value/1_000:.0f}K"
    return f"€{int(value)}"


def get_flag_emoji(nationality: str) -> str:
    """Return a flag emoji for common nationalities."""
    flags = {
        "Indian": "🇮🇳",
        "English": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
        "Australian": "🇦🇺",
        "Pakistani": "🇵🇰",
        "New Zealander": "🇳🇿",
        "South African": "🇿🇦",
        "Bangladeshi": "🇧🇩",
        "Afghan": "🇦🇫",
        "Argentine": "🇦🇷",
        "Portuguese": "🇵🇹",
        "French": "🇫🇷",
        "Norwegian": "🇳🇴",
        "Brazilian": "🇧🇷",
        "Belgian": "🇧🇪",
        "Croatian": "🇭🇷",
        "Spanish": "🇪🇸",
        "Dutch": "🇳🇱",
        "German": "🇩🇪",
        "Egyptian": "🇪🇬",
        "South Korean": "🇰🇷",
    }
    return flags.get(nationality, "🌍")


def get_role_icon(role_or_position: str, sport: str) -> str:
    """Return an icon for the player's role/position."""
    if sport == "cricket":
        icons = {
            "Batsman": "🏏",
            "Bowler": "⚾",
            "All-Rounder": "⚡",
            "Wicket-Keeper": "🧤",
        }
    else:
        icons = {
            "Forward": "⚽",
            "Midfielder": "🔄",
            "Defender": "🛡️",
            "Goalkeeper": "🧤",
        }
    return icons.get(role_or_position, "🏆")


def safe_float(val, default: float = 0.0) -> float:
    """Safely convert a value to float."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def safe_int(val, default: int = 0) -> int:
    """Safely convert a value to int."""
    try:
        return int(float(val))
    except (TypeError, ValueError):
        return default


def performance_color(score: float) -> str:
    """Return a color hex based on performance score (50-100)."""
    if score >= 88:
        return "#00FF88"
    elif score >= 78:
        return "#FFD700"
    elif score >= 68:
        return "#FF6B35"
    else:
        return "#FF4444"


def trend_indicator(trend: str) -> str:
    """Return an arrow indicator for trend direction."""
    return {"Rising": "📈", "Stable": "📊", "Declining": "📉"}.get(trend, "📊")
