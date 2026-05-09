"""
Cricket Module - Player data processing, stats, and ML analysis for cricket players.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')


CRICKET_STATS_CONFIG = {
    "key_metrics": ["runs", "average", "strike_rate", "hundreds", "fifties", "wickets"],
    "radar_axes": ["speed", "power", "technique", "consistency", "fielding", "leadership"],
    "time_series_col": ["2019_runs", "2020_runs", "2021_runs", "2022_runs", "2023_runs", "2024_runs"],
    "time_labels": ["2019", "2020", "2021", "2022", "2023", "2024"],
    "roles": ["Batsman", "Bowler", "All-Rounder", "Wicket-Keeper"],
    "batting_cols": ["runs", "average", "strike_rate", "hundreds", "fifties", "highest_score"],
    "bowling_cols": ["wickets", "bowling_avg", "economy"],
    "fielding_cols": ["catches", "stumpings"],
}


def load_cricket_data(filepath: str) -> pd.DataFrame:
    """Load and validate cricket dataset."""
    try:
        df = pd.read_csv(filepath)
        df = df.fillna(0)
        df["name_lower"] = df["name"].str.lower()
        return df
    except Exception as e:
        raise FileNotFoundError(f"Cricket data load failed: {e}")


def search_players(df: pd.DataFrame, query: str) -> list[dict]:
    """Search players by name (partial match, case-insensitive)."""
    query = query.lower().strip()
    matches = df[df["name_lower"].str.contains(query, na=False)]
    return matches[["player_id", "name", "team", "role", "nationality"]].to_dict("records")


def get_player_profile(df: pd.DataFrame, player_id: str) -> dict | None:
    """Get full player profile by ID."""
    row = df[df["player_id"] == player_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_key_stats(player: dict) -> dict:
    """Extract key stat cards for a cricket player."""
    role = player.get("role", "")
    stats = {
        "Matches": int(player.get("matches", 0)),
        "Runs": int(player.get("runs", 0)),
        "Average": round(float(player.get("average", 0)), 2),
        "Strike Rate": round(float(player.get("strike_rate", 0)), 2),
        "100s": int(player.get("hundreds", 0)),
        "50s": int(player.get("fifties", 0)),
    }
    if role in ["Bowler", "All-Rounder"]:
        stats["Wickets"] = int(player.get("wickets", 0))
        stats["Bowl Avg"] = round(float(player.get("bowling_avg", 0)), 2)
        stats["Economy"] = round(float(player.get("economy", 0)), 2)
    if role == "Wicket-Keeper":
        stats["Catches"] = int(player.get("catches", 0))
        stats["Stumpings"] = int(player.get("stumpings", 0))
    return stats


def get_radar_data(player: dict) -> dict:
    """Get radar chart data for a cricket player."""
    axes = CRICKET_STATS_CONFIG["radar_axes"]
    values = []
    for ax in axes:
        val = float(player.get(ax, 0))
        values.append(min(val, 100))
    return {"axes": axes, "values": values}


def get_time_series(player: dict) -> dict:
    """Get performance over time for a cricket player."""
    cols = CRICKET_STATS_CONFIG["time_series_col"]
    labels = CRICKET_STATS_CONFIG["time_labels"]
    values = [int(player.get(c, 0)) for c in cols]
    return {"labels": labels, "values": values, "metric": "Runs"}


def compare_players(df: pd.DataFrame, p1_id: str, p2_id: str) -> dict:
    """Compare two cricket players side by side."""
    p1 = get_player_profile(df, p1_id)
    p2 = get_player_profile(df, p2_id)
    if not p1 or not p2:
        return {}

    compare_cols = ["runs", "average", "strike_rate", "hundreds", "fifties",
                    "wickets", "matches", "highest_score", "catches"]
    compare_labels = ["Runs", "Average", "Strike Rate", "100s", "50s",
                      "Wickets", "Matches", "Highest Score", "Catches"]

    p1_vals = [float(p1.get(c, 0)) for c in compare_cols]
    p2_vals = [float(p2.get(c, 0)) for c in compare_cols]

    winner_flags = []
    for v1, v2 in zip(p1_vals, p2_vals):
        if v1 > v2:
            winner_flags.append(1)
        elif v2 > v1:
            winner_flags.append(2)
        else:
            winner_flags.append(0)

    p1_wins = winner_flags.count(1)
    p2_wins = winner_flags.count(2)
    overall_winner = p1["name"] if p1_wins > p2_wins else p2["name"] if p2_wins > p1_wins else "Draw"

    return {
        "player1": p1,
        "player2": p2,
        "labels": compare_labels,
        "p1_values": p1_vals,
        "p2_values": p2_vals,
        "winner_flags": winner_flags,
        "overall_winner": overall_winner,
        "p1_wins": p1_wins,
        "p2_wins": p2_wins,
    }


def generate_ai_insights(player: dict) -> dict:
    """Generate rule-based AI insights for a cricket player."""
    role = player.get("role", "")
    avg = float(player.get("average", 0))
    sr = float(player.get("strike_rate", 0))
    consistency = float(player.get("consistency", 0))
    form = float(player.get("form_score", 0))
    wickets = int(player.get("wickets", 0))
    economy = float(player.get("economy", 0))

    strengths = []
    weaknesses = []
    insights = []

    # Batting analysis
    if role in ["Batsman", "All-Rounder", "Wicket-Keeper"]:
        if avg > 50:
            strengths.append(f"Exceptional batting average of {avg} — elite-tier consistency")
        elif avg > 40:
            strengths.append(f"Solid batting average of {avg} — reliable performer")
        else:
            weaknesses.append(f"Batting average of {avg} needs improvement")

        if sr > 130:
            strengths.append(f"Explosive strike rate of {sr} — match-winner in T20s")
        elif sr < 80 and role != "Bowler":
            weaknesses.append(f"Strike rate of {sr} may be too slow for modern cricket")

    # Bowling analysis
    if role in ["Bowler", "All-Rounder"]:
        if wickets > 250:
            strengths.append(f"Outstanding {wickets} wickets — world-class wicket-taker")
        elif wickets > 100:
            strengths.append(f"Impressive {wickets} wickets — reliable bowling option")

        if economy < 3.0 and economy > 0:
            strengths.append(f"Exceptional economy rate of {economy} — incredibly miserly")
        elif economy > 5.5:
            weaknesses.append(f"Economy rate of {economy} is expensive")

    # Consistency
    if consistency > 88:
        strengths.append(f"Remarkable consistency score ({consistency}/100) — rarely has off days")
    elif consistency < 75:
        weaknesses.append(f"Consistency ({consistency}/100) is a concern — performances too variable")

    # Form
    if form > 85:
        insights.append("Currently in excellent form — riding a hot streak")
    elif form < 70:
        insights.append("Form dip noticed — may benefit from a rest or tactical reset")

    # Time series trend
    ts_cols = ["2022_runs", "2023_runs", "2024_runs"]
    ts_vals = [float(player.get(c, 0)) for c in ts_cols]
    non_zero = [v for v in ts_vals if v > 0]
    if len(non_zero) >= 2:
        trend = non_zero[-1] - non_zero[0]
        if trend > 200:
            insights.append("Strong upward scoring trend in recent seasons — improving with age")
        elif trend < -200:
            insights.append("Declining run tally in recent seasons — worth monitoring")
        else:
            insights.append("Stable scoring pattern across recent seasons — dependable output")

    if not strengths:
        strengths.append("Consistent contributor to team performance")
    if not weaknesses:
        weaknesses.append("No glaring technical weaknesses identified")

    # Performance rating
    rating = min(100, int((form * 0.4) + (consistency * 0.4) + (avg / 1.2) * 0.2))
    rating = max(50, rating)

    return {
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "insights": insights[:3],
        "performance_rating": rating,
        "form_trend": "Rising" if form > 80 else "Stable" if form > 65 else "Declining",
    }


def train_performance_model(df: pd.DataFrame) -> dict:
    """Train a simple regression model to predict player performance score."""
    try:
        feature_cols = ["matches", "average", "strike_rate", "hundreds", "fifties",
                        "wickets", "consistency", "form_score"]
        target_col = "form_score"

        data = df[feature_cols + [target_col]].dropna()
        data = data[(data > 0).all(axis=1)]

        X = data[feature_cols].values
        y = data[target_col].values

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = LinearRegression()
        model.fit(X_scaled, y)

        return {"model": model, "scaler": scaler, "feature_cols": feature_cols, "trained": True}
    except Exception as e:
        return {"trained": False, "error": str(e)}


def predict_player_score(player: dict, model_data: dict) -> float | None:
    """Predict performance score for a player using trained model."""
    if not model_data.get("trained"):
        return None
    try:
        feature_cols = model_data["feature_cols"]
        X = np.array([[float(player.get(c, 0)) for c in feature_cols]])
        X_scaled = model_data["scaler"].transform(X)
        pred = model_data["model"].predict(X_scaled)[0]
        return round(float(np.clip(pred, 50, 100)), 1)
    except Exception:
        return None


def cluster_similar_players(df: pd.DataFrame, player_id: str, n_clusters: int = 4) -> list[str]:
    """Find similar players using KMeans clustering."""
    try:
        feature_cols = ["runs", "average", "strike_rate", "wickets", "consistency"]
        data = df[feature_cols + ["player_id", "name"]].dropna()
        data = data.fillna(0)

        X = data[feature_cols].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        data = data.copy()
        data["cluster"] = km.fit_predict(X_scaled)

        player_row = data[data["player_id"] == player_id]
        if player_row.empty:
            return []

        cluster_id = player_row.iloc[0]["cluster"]
        similar = data[(data["cluster"] == cluster_id) & (data["player_id"] != player_id)]
        return similar["name"].tolist()[:4]
    except Exception:
        return []
