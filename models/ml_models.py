"""
Models - ML model training, prediction, and persistence for both sports.
"""
import os
import pickle
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.model_selection import cross_val_score
import warnings
warnings.filterwarnings('ignore')

MODELS_DIR = os.path.dirname(os.path.abspath(__file__))


def train_and_save_models(cricket_df: pd.DataFrame, football_df: pd.DataFrame) -> dict:
    """Train performance prediction models for both sports and save them."""
    results = {}

    # Cricket model
    cricket_features = ["matches", "average", "strike_rate", "hundreds",
                        "fifties", "wickets", "consistency"]
    results["cricket"] = _train_model(cricket_df, cricket_features, "form_score", "cricket")

    # Football model
    football_features = ["matches", "goals", "assists", "pass_accuracy",
                         "xG", "xA", "dribbles", "tackles"]
    results["football"] = _train_model(football_df, football_features, "form_score", "football")

    return results


def _train_model(df: pd.DataFrame, features: list, target: str, sport: str) -> dict:
    """Internal: train a Ridge regression model and return metadata."""
    try:
        data = df[features + [target]].dropna().copy()
        data = data.replace([np.inf, -np.inf], np.nan).dropna()
        data = data[data[target] > 0]

        if len(data) < 5:
            return {"trained": False, "error": "Insufficient data", "sport": sport}

        X = data[features].values.astype(float)
        y = data[target].values.astype(float)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        model = Ridge(alpha=1.0)
        model.fit(X_scaled, y)

        # Cross-validation score
        if len(data) >= 5:
            scores = cross_val_score(model, X_scaled, y, cv=min(3, len(data)), scoring="r2")
            r2 = round(float(np.mean(scores)), 3)
        else:
            r2 = 0.0

        # Save model
        model_path = os.path.join(MODELS_DIR, f"{sport}_model.pkl")
        with open(model_path, "wb") as f:
            pickle.dump({"model": model, "scaler": scaler, "features": features}, f)

        return {
            "trained": True,
            "sport": sport,
            "r2_score": r2,
            "n_samples": len(data),
            "features": features,
            "model_path": model_path,
        }
    except Exception as e:
        return {"trained": False, "error": str(e), "sport": sport}


def load_model(sport: str) -> dict:
    """Load a pre-trained model from disk."""
    try:
        model_path = os.path.join(MODELS_DIR, f"{sport}_model.pkl")
        if not os.path.exists(model_path):
            return {"loaded": False, "error": "Model file not found"}
        with open(model_path, "rb") as f:
            data = pickle.load(f)
        data["loaded"] = True
        return data
    except Exception as e:
        return {"loaded": False, "error": str(e)}


def predict_score(player: dict, model_data: dict) -> float:
    """Predict a player's performance score using a loaded/trained model."""
    try:
        features = model_data.get("features", [])
        scaler = model_data.get("scaler")
        model = model_data.get("model")

        if not features or scaler is None or model is None:
            return float(player.get("form_score", 75))

        X = np.array([[float(player.get(f, 0)) for f in features]])
        X_scaled = scaler.transform(X)
        pred = model.predict(X_scaled)[0]
        return round(float(np.clip(pred, 50, 100)), 1)
    except Exception:
        return float(player.get("form_score", 75))


def get_peer_cluster(df: pd.DataFrame, player_id: str, sport: str, n_clusters: int = 4) -> list[str]:
    """Cluster players and find peers of the given player."""
    try:
        if sport == "cricket":
            features = ["runs", "average", "strike_rate", "wickets", "consistency"]
        else:
            features = ["goals", "assists", "pass_accuracy", "dribbles", "tackles"]

        data = df[features + ["player_id", "name"]].copy().fillna(0)
        X = data[features].values.astype(float)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        n = min(n_clusters, len(data) - 1)
        km = KMeans(n_clusters=n, random_state=42, n_init=10)
        data = data.copy()
        data["cluster"] = km.fit_predict(X_scaled)

        target = data[data["player_id"] == player_id]
        if target.empty:
            return []

        cid = target.iloc[0]["cluster"]
        peers = data[(data["cluster"] == cid) & (data["player_id"] != player_id)]
        return peers["name"].tolist()[:4]
    except Exception:
        return []
