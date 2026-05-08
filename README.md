---
title: Sports_profile
emoji: ⚡
colorFrom: blue
colorTo: red
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
---

# ⚡ SportsPulse — Multi-Sport Player Performance Profiling System

> **Color palette:** Deep Royal Blue (#0F1566) · Bold Red (#E8293A) · White (#FFFFFF)  
> Inspired by the England/Shoty slab + script sport aesthetic.

---

## 🗂️ Project Structure

```
sports_profiler/
├── app.py                      # Main Streamlit dashboard
├── requirements.txt
├── data/
│   ├── cricket.csv             # 20 cricket players with full stats
│   └── football.csv            # 20 football players with full stats
├── modules/
│   ├── cricket.py              # Cricket data pipeline + insights
│   └── football.py             # Football data pipeline + insights
├── models/
│   └── ml_models.py            # Ridge regression + KMeans clustering
├── utils/
│   ├── helpers.py              # Formatting, flags, icons
│   └── visualizations.py       # All Plotly charts (radar, line, bar, gauge)
└── api/
    └── data_fetcher.py         # Semi-real-time API layer with fallback
```

---

## 🚀 How to Run

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Launch the app
```bash
streamlit run app.py
```

### 3. Open browser
Navigate to `http://localhost:8501`

---

## 🎮 Features

| Feature | Description |
|---------|-------------|
| **Multi-Sport** | Cricket 🏏 and Football ⚽ — fully separate pipelines |
| **Player Search** | Real-time search with partial name matching |
| **Profile Mode** | Stats cards, radar chart, season trend line, form gauge |
| **Analysis Mode** | AI insights, ML prediction score, consistency analysis |
| **Comparison Mode** | Side-by-side stats, dual radar, winner highlights |
| **Semi-Real-Time** | API layer with dataset fallback + per-minute micro-updates |
| **ML Models** | Ridge regression (performance prediction) + KMeans (peer clustering) |

---

## 📊 Dataset Format

### cricket.csv columns
`player_id, name, team, role, nationality, age, matches, innings, runs, average, strike_rate, hundreds, fifties, highest_score, wickets, bowling_avg, economy, catches, stumpings, form_score, market_value, 2019_runs..2024_runs, speed, power, technique, consistency, fielding, leadership`

### football.csv columns
`player_id, name, team, position, nationality, age, matches, goals, assists, pass_accuracy, xG, xA, shots_per_game, key_passes, dribbles, tackles, interceptions, clean_sheets, saves, form_score, market_value, 2019_goals..2024_goals, pace, shooting, passing, dribbling, defending, physical`

---

## 🔌 API Integration

The `api/data_fetcher.py` module provides a clean interface:
- **Primary**: calls live sports API (Cricket Data API / API-Football)
- **Fallback**: loads local CSV + applies simulated micro-updates
- **Status indicator**: shown in sidebar ("LIVE" vs "DATASET MODE")

To enable real APIs, add your keys to `.env`:
```
CRICKET_API_KEY=your_key_here
FOOTBALL_API_KEY=your_key_here
```
Then uncomment the `requests.get(...)` calls in `api/data_fetcher.py`.

---

## 🤖 ML Models

| Model | Type | Target | Features |
|-------|------|--------|----------|
| Cricket | Ridge Regression | form_score | matches, average, strike_rate, hundreds, wickets, consistency |
| Football | Ridge Regression | form_score | matches, goals, assists, pass_accuracy, xG, xA, dribbles, tackles |
| Both | KMeans (k=4) | peer_cluster | position-specific stats |

Models are saved to `models/cricket_model.pkl` and `models/football_model.pkl` on first run.

---

## 🎨 Colour System

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-deep` | `#060B3A` | Page background |
| `--bg-mid` | `#0F1566` | Cards, panels |
| `--bg-surface` | `#1A1F8C` | Elevated surfaces |
| `--red` | `#E8293A` | Primary accent, badges, highlights |
| `--gold` | `#FFD700` | Winning metrics, value labels |
| `--white` | `#FFFFFF` | Text, labels |
| `--blue-lt` | `#4A5FE8` | Secondary player, comparison |

---

## 🔮 Future Improvements

1. **Live API Integration** — wire up real sports APIs (Cricinfo, API-Football)
2. **Video Highlights** — embed match highlight clips per player
3. **Team Analytics** — aggregate team performance dashboards
4. **Historical Deep Dive** — career timeline with event annotations
5. **Export Reports** — one-click PDF/Excel player report generation
6. **Fantasy Score Predictor** — next-match performance prediction
7. **Mobile PWA** — progressive web app for on-the-go access
