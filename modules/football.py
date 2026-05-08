"""
Football Module - Player data processing, stats, and ML analysis for football players.
"""
import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
import warnings
warnings.filterwarnings('ignore')


FOOTBALL_STATS_CONFIG = {
    "key_metrics": ["goals", "assists", "pass_accuracy", "xG", "xA", "shots_per_game"],
    "radar_axes": ["pace", "shooting", "passing", "dribbling", "defending", "physical"],
    "time_series_col": ["2019_goals", "2020_goals", "2021_goals", "2022_goals", "2023_goals", "2024_goals"],
    "time_labels": ["2019", "2020", "2021", "2022", "2023", "2024"],
    "positions": ["Forward", "Midfielder", "Defender", "Goalkeeper"],
    "outfield_cols": ["goals", "assists", "pass_accuracy", "xG", "shots_per_game", "dribbles", "key_passes"],
    "gk_cols": ["clean_sheets", "saves"],
    "def_cols": ["tackles", "interceptions"],
}


def load_football_data(filepath: str) -> pd.DataFrame:
    """Load and validate football dataset."""
    try:
        df = pd.read_csv(filepath)
        df = df.fillna(0)
        df["name_lower"] = df["name"].str.lower()
        return df
    except Exception as e:
        raise FileNotFoundError(f"Football data load failed: {e}")


def search_players(df: pd.DataFrame, query: str) -> list[dict]:
    """Search players by name (partial match, case-insensitive)."""
    query = query.lower().strip()
    matches = df[df["name_lower"].str.contains(query, na=False)]
    return matches[["player_id", "name", "team", "position", "nationality"]].to_dict("records")


def get_player_profile(df: pd.DataFrame, player_id: str) -> dict | None:
    """Get full player profile by ID."""
    row = df[df["player_id"] == player_id]
    if row.empty:
        return None
    return row.iloc[0].to_dict()


def get_key_stats(player: dict) -> dict:
    """Extract key stat cards for a football player."""
    position = player.get("position", "")
    stats = {
        "Matches": int(player.get("matches", 0)),
        "Goals": int(player.get("goals", 0)),
        "Assists": int(player.get("assists", 0)),
        "Pass Acc %": round(float(player.get("pass_accuracy", 0)), 1),
    }
    if position == "Goalkeeper":
        stats["Clean Sheets"] = int(player.get("clean_sheets", 0))
        stats["Saves"] = int(player.get("saves", 0))
        del stats["Goals"]
        del stats["Assists"]
    elif position in ["Forward", "Midfielder"]:
        stats["xG"] = round(float(player.get("xG", 0)), 2)
        stats["xA"] = round(float(player.get("xA", 0)), 2)
        stats["Shots/Game"] = round(float(player.get("shots_per_game", 0)), 1)
    elif position == "Defender":
        stats["Tackles"] = round(float(player.get("tackles", 0)), 1)
        stats["Intercept."] = round(float(player.get("interceptions", 0)), 1)
    return stats


def get_radar_data(player: dict) -> dict:
    """Get radar chart data for a football player."""
    axes = FOOTBALL_STATS_CONFIG["radar_axes"]
    values = []
    for ax in axes:
        val = float(player.get(ax, 0))
        values.append(min(val, 100))
    return {"axes": axes, "values": values}


def get_time_series(player: dict) -> dict:
    """Get performance over time for a football player."""
    cols = FOOTBALL_STATS_CONFIG["time_series_col"]
    labels = FOOTBALL_STATS_CONFIG["time_labels"]
    values = [int(player.get(c, 0)) for c in cols]
    return {"labels": labels, "values": values, "metric": "Goals"}


def compare_players(df: pd.DataFrame, p1_id: str, p2_id: str) -> dict:
    """Compare two football players side by side."""
    p1 = get_player_profile(df, p1_id)
    p2 = get_player_profile(df, p2_id)
    if not p1 or not p2:
        return {}

    compare_cols = ["goals", "assists", "pass_accuracy", "xG", "xA",
                    "shots_per_game", "dribbles", "tackles", "matches"]
    compare_labels = ["Goals", "Assists", "Pass Acc%", "xG", "xA",
                      "Shots/Game", "Dribbles", "Tackles", "Matches"]

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
    """Generate rule-based AI insights for a football player."""
    position = player.get("position", "")
    goals = int(player.get("goals", 0))
    assists = int(player.get("assists", 0))
    pass_acc = float(player.get("pass_accuracy", 0))
    xG = float(player.get("xG", 0))
    form = float(player.get("form_score", 0))
    dribbles = float(player.get("dribbles", 0))
    tackles = float(player.get("tackles", 0))
    clean_sheets = int(player.get("clean_sheets", 0))
    saves = int(player.get("saves", 0))
    market_val = float(player.get("market_value", 0))

    strengths = []
    weaknesses = []
    insights = []

    if position == "Goalkeeper":
        if clean_sheets > 200:
            strengths.append(f"Outstanding {clean_sheets} clean sheets — legendary reliability")
        elif clean_sheets > 100:
            strengths.append(f"Impressive {clean_sheets} clean sheets — elite shot-stopper")
        if saves > 800:
            strengths.append(f"Extraordinary {saves} career saves — instinctive reflexes")
    else:
        if goals > 500:
            strengths.append(f"Legendary {goals} career goals — all-time great scorer")
        elif goals > 200:
            strengths.append(f"Elite {goals} career goals — world-class finisher")
        elif goals > 50 and position == "Midfielder":
            strengths.append(f"Excellent {goals} goals for a midfielder — attacking threat")

        if assists > 200:
            strengths.append(f"Exceptional {assists} assists — supreme creative force")
        elif assists > 100:
            strengths.append(f"Great {assists} assists — consistent chance creator")

        if pass_acc > 90:
            strengths.append(f"Elite pass accuracy of {pass_acc}% — technically outstanding")
        elif pass_acc < 78 and position == "Midfielder":
            weaknesses.append(f"Pass accuracy of {pass_acc}% below expectation for this role")

        if xG > 0.8:
            strengths.append(f"Devastating xG of {xG} per game — maximises scoring positions")
        elif xG < 0.3 and position == "Forward":
            weaknesses.append(f"xG of {xG} suggests not getting into scoring positions enough")

        if dribbles > 7:
            strengths.append(f"Exceptional dribbling ({dribbles}/game) — unplayable 1v1")
        elif dribbles < 2 and position == "Forward":
            weaknesses.append("Limited dribbling output — relies heavily on team build-up")

        if position == "Defender":
            if tackles > 6:
                strengths.append(f"Dominant tackling ({tackles}/game) — commanding defensive presence")
            weaknesses.append("Need to analyse ball-playing ability more deeply") if pass_acc < 85 else None

    # Form
    if form > 88:
        insights.append("Exceptional current form — performing at peak level")
    elif form > 80:
        insights.append("In good form — consistently delivering for the team")
    elif form < 75:
        insights.append("Below-par form recently — tactical adjustment may be needed")

    # Market value insight
    if market_val > 150000000:
        insights.append(f"Market value of €{int(market_val/1000000)}M reflects generational talent status")
    elif market_val > 80000000:
        insights.append(f"Strong market value of €{int(market_val/1000000)}M — proven elite performer")

    # Time trend
    ts_cols = ["2022_goals", "2023_goals", "2024_goals"]
    ts_vals = [float(player.get(c, 0)) for c in ts_cols]
    non_zero = [v for v in ts_vals if v > 0]
    if len(non_zero) >= 2:
        trend = non_zero[-1] - non_zero[0]
        if trend > 5:
            insights.append("Goal contribution trending upward — still improving")
        elif trend < -8:
            insights.append("Declining goal output — could reflect age or system change")
        else:
            insights.append("Consistent goal contribution across recent seasons")

    if not strengths:
        strengths.append("Important squad player with tactical discipline")
    if not weaknesses:
        weaknesses.append("No significant weaknesses in current dataset")

    rating = min(100, int((form * 0.5) + (min(goals / 10, 30)) + (min(assists / 8, 20))))
    rating = max(50, rating)

    return {
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "insights": insights[:3],
        "performance_rating": rating,
        "form_trend": "Rising" if form > 85 else "Stable" if form > 72 else "Declining",
    }


def train_performance_model(df: pd.DataFrame) -> dict:
    """Train a simple regression model to predict player form score."""
    try:
        feature_cols = ["matches", "goals", "assists", "pass_accuracy",
                        "xG", "xA", "dribbles", "tackles"]
        target_col = "form_score"

        data = df[feature_cols + [target_col]].dropna()
        data = data[(data >= 0).all(axis=1)]

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
    """Predict form score for a player using trained model."""
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
        feature_cols = ["goals", "assists", "pass_accuracy", "dribbles", "tackles"]
        data = df[feature_cols + ["player_id", "name"]].copy()
        data = data.fillna(0)

        X = data[feature_cols].values
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        data["cluster"] = km.fit_predict(X_scaled)

        player_row = data[data["player_id"] == player_id]
        if player_row.empty:
            return []

        cluster_id = player_row.iloc[0]["cluster"]
        similar = data[(data["cluster"] == cluster_id) & (data["player_id"] != player_id)]
        return similar["name"].tolist()[:4]
    except Exception:
        return []
