#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Oct 12 19:33:45 2025

@author: kagancalikoglu
"""

"""
Spatial Cluster Modeling for Football Matches (NumPy 2.x compatible, scikit-learn version)
------------------------------------------------------------------------------------------
This script:
1. Builds a 12x9 pitch grid and 10 clusters (6 squares + 4 linears).
2. Places Team1 players according to the formation (4-1-3-2, 4-2-3-1, 4-3-3, 4-4-2).
3. Aggregates player ratings into spatial clusters (+/-1 neighborhood rule).
4. Runs regressions (via scikit-learn) for:
      - Outcome_3W1D0L
      - Team1_BigChances
      - Team1_TotalShots
      - Team2_BigChances
      - Team2_TotalShots
5. Saves engineered outputs and predictions to a single Excel file.
6. Visualizes the first test-row formation with player dots and values, and prints cluster averages.

"""

from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
import matplotlib.pyplot as plt

# ------------------ User-configurable paths ------------------
EXCEL_PATH = Path("/Users/kagancalikoglu/Documents/PredictaBall/Inputs/Fenerbahce_Games_Input.xlsx")
INPUT_SHEET = "Team_Inputs"
TEST_SHEET = "Team_Test"
OUTPUT_PATH = Path("/Users/kagancalikoglu/Documents/PredictaBall/Outputs/Matrix_Model_Output.xlsx")
FIG_PATH = Path("Formation_Visualization.png")

# Column names
TEAM1_FORMATION_COL = "Team1_Formation"
TEAM1_PLAYERS = [f"Team1Player{i}" for i in range(1, 12)]  # 1..11

# Targets
TARGET_COLS = [
    "Team1_BigChances",
    "Team1_TotalShots",
    "Team2_BigChances",
    "Team2_TotalShots",
]

# ------------------ Grid & clusters ------------------
X_MIN, X_MAX = 1, 5     # left → right (def → attack)
Y_MIN, Y_MAX = 1, 9     # top → bottom (left → right)


@dataclass(frozen=True)
class Cluster:
    name: str
    x1: int; x2: int
    y1: int; y2: int
    def contains_with_margin(self, x: int, y: int, margin: int = 1) -> bool:
        return (self.x1 - margin <= x <= self.x2 + margin) and (self.y1 - margin <= y <= self.y2 + margin)

def build_clusters() -> List[Cluster]:
    """
    Define 11 spatial clusters for a 5×9 pitch.
    - GK occupies x=1 (entire width)
    - Remaining 10 clusters are for Def/Mid/Att lines × Left/Right
    - Plus linear corridors
    """
    
    clusters = [
        # Goalkeeper zone
        Cluster("Goalkeeper_Zone", 1, 1, 1, 9),

        # Defense
        Cluster("Back_Left",  2, 3, 1, 3),
        Cluster("Back_Right", 2, 3, 7, 9),

        # Midfield
        Cluster("Mid_Def",  2, 3, 4, 6),
        Cluster("Mid_Att", 4, 5, 4, 6),

        # Attack
        Cluster("Wing_Left",  4, 5, 1, 3),
        Cluster("Wing_Right", 4, 5, 7, 9),

        # Central + wide linear strips
        Cluster("Left_Strip", 2, 5, 1, 3),
        Cluster("Mid_Strip", 2, 5, 4, 6),
        Cluster("Right_Strip",  2, 5, 7, 9)
    ]
    return clusters


CLUSTERS = build_clusters()
CLUSTER_NAMES = [c.name for c in CLUSTERS]

# ------------------ Formation templates ------------------
FORMATION_TEMPLATES: Dict[str, List[Tuple[int, int]]] = {
    # === 4-back systems ===
    "4-1-3-2": [
        (1,5),                              # GK
        (2,2), (2,4), (2,6), (2,8),         # 4-back
        (3,5),                              # CDM
        (4,3), (4,5), (4,7),                # 3 mids
        (5,4), (5,6),                       # 2 strikers
    ],
    "4-2-3-1": [
        (1,5),
        (2,2), (2,4), (2,6), (2,8),
        (3,4), (3,6),                       # 2 CDMs
        (4,3), (4,5), (4,7),                # 3 CAMs
        (5,5),                              # striker
    ],
    "4-3-3": [
        (1,5),
        (2,2), (2,4), (2,6), (2,8),
        (3,4), (3,5), (3,6),                # 3 mids
        (4,2), (4,5), (4,8),                # 3 forwards
    ],
    "4-4-2": [
        (1,5),
        (2,2), (2,4), (2,6), (2,8),
        (3,3), (3,7),                       # 2 mids wide
        (4,4), (4,6),                       # 2 central mids
        (5,4), (5,6),                       # 2 strikers
    ],
    "4-1-4-1": [
        (1,5),
        (2,2), (2,4), (2,6), (2,8),
        (3,5),                              # CDM
        (4,2), (4,4), (4,6), (4,8),         # 4 mids
        (5,5),                              # striker
    ],
    "4-2-2-2": [
        (1,5),
        (2,2), (2,4), (2,6), (2,8),
        (3,3), (3,7),                       # 2 wide mids
        (4,4), (4,6),                       # 2 CAMs
        (5,4), (5,6),                       # 2 strikers
    ],

    # === 3-back systems ===
    "3-4-3": [
        (1,5),
        (2,3), (2,5), (2,7),                # 3 CBs
        (3,2), (3,4), (3,6), (3,8),         # 4 mids
        (4,3), (4,5), (4,7),                # 3 forwards
    ],
    "3-4-1-2": [
        (1,5),
        (2,3), (2,5), (2,7),
        (3,2), (3,4), (3,6), (3,8),         # 4 mids
        (4,5),                              # CAM
        (5,4), (5,6),                       # 2 strikers
    ],
    "3-4-2-1": [
        (1,5),
        (2,3), (2,5), (2,7),
        (3,2), (3,4), (3,6), (3,8),         # 4 mids
        (4,4), (4,6),                       # 2 CAMs
        (5,5),                              # striker
    ],
    "3-5-2": [
        (1,5),
        (2,3), (2,5), (2,7),
        (3,2), (3,4), (3,5), (3,6), (3,8),  # 5 mids
        (5,4), (5,6),                       # 2 strikers
    ],
    "3-1-4-2": [
        (1,5),
        (2,3), (2,5), (2,7),                # 3 CBs
        (3,5),                              # CDM
        (4,2), (4,4), (4,6), (4,8),         # 4 mids
        (5,4), (5,6),                       # 2 strikers
    ],

    # === 5-back systems ===
    "5-3-2": [
        (1,5),
        (2,2), (2,3), (2,5), (2,7), (2,8),  # 5-back
        (3,4), (3,5), (3,6),                # 3 mids
        (5,4), (5,6),                       # 2 strikers
    ],
    "5-4-1": [
        (1,5),
        (2,2), (2,3), (2,5), (2,7), (2,8),  # 5-back
        (3,3), (3,5), (3,7), (4,5),         # 4 mids
        (5,5),                              # striker
    ],
}

DEFAULT_FORMATION = "4-2-3-1"

def parse_formation(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return DEFAULT_FORMATION
    s = s.strip().replace(" ", "")
    return s if s in FORMATION_TEMPLATES else DEFAULT_FORMATION

def coords_for_match(formation_str: str) -> List[Tuple[int,int]]:
    return FORMATION_TEMPLATES[parse_formation(formation_str)]

# ------------------ Cluster feature engineering ------------------
def player_cluster_memberships(x: int, y: int, clusters: List[Cluster], margin: int = 1) -> List[str]:
    return [c.name for c in clusters if c.contains_with_margin(x, y, margin=margin)]

def compute_cluster_features_for_row(row: pd.Series) -> Dict[str, float]:
    formation = row.get(TEAM1_FORMATION_COL, DEFAULT_FORMATION)
    coords = coords_for_match(formation)
    ratings = [row.get(col, np.nan) for col in TEAM1_PLAYERS]
    bucket: Dict[str, List[float]] = {name: [] for name in CLUSTER_NAMES}
    for i, (x, y) in enumerate(coords):
        rating = ratings[i]
        if pd.isna(rating):
            continue
        for cname in player_cluster_memberships(x, y, CLUSTERS, margin=0):
            bucket[cname].append(float(rating))
    agg = {}
    for cname, vals in bucket.items():
        agg[f"Cluster_{cname}_Avg"] = float(np.mean(vals)) if len(vals) else np.nan
        agg[f"Cluster_{cname}_Cnt"] = int(len(vals))
    return agg

def engineer_dataset(df: pd.DataFrame) -> pd.DataFrame:
    features = df.apply(compute_cluster_features_for_row, axis=1, result_type="expand")
    out = pd.concat([df.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    # derive outcome 3/1/0 if goals or result present
    if {"Team1_Goals", "Team2_Goals"}.issubset(out.columns):
        g1, g2 = out["Team1_Goals"], out["Team2_Goals"]
        out["Outcome_3W1D0L"] = np.where(g1 > g2, 3, np.where(g1 == g2, 1, 0))
    elif "Result" in out.columns:
        res = out["Result"].astype(str).str.upper().str.strip()
        out["Outcome_3W1D0L"] = res.map({"W": 3, "D": 1, "L": 0})
    return out

# ------------------ Modeling ------------------
def fit_linear(y: pd.Series, X: pd.DataFrame, label: str):
    mask = y.notna() & X.notna().all(axis=1)
    X_valid, y_valid = X[mask], y[mask]
    pipe = Pipeline([
        ('scale', StandardScaler()),
        ('ols', LinearRegression())
    ])
    pipe.fit(X_valid, y_valid)
    r2 = pipe.score(X_valid, y_valid)
    print(f"\n{'='*80}\nLinear Regression: {label}\n{'='*80}")
    print(f"R² = {r2:.3f}\n")
    coefs = pipe.named_steps['ols'].coef_
    coef_table = pd.Series(coefs, index=X.columns).sort_values(ascending=False)
    print(coef_table.head(10))
    return pipe

def run_models(df_engineered: pd.DataFrame):
    feat_cols = [c for c in df_engineered.columns if c.startswith("Cluster_") and c.endswith("_Avg")]
    X = df_engineered[feat_cols]
    models = {}
    if "Outcome_3W1D0L" in df_engineered.columns:
        models["Outcome_3W1D0L"] = fit_linear(df_engineered["Outcome_3W1D0L"], X, "Outcome_3W1D0L")
    for t in TARGET_COLS:
        if t in df_engineered.columns:
            models[t] = fit_linear(df_engineered[t], X, t)
    return models

# ------------------ Visualization ------------------
def visualize_formation(row: pd.Series, title: str = "Team Formation with Player Values",
                        save_path: Path | None = None) -> pd.DataFrame:
    """
    Draw the team formation for a single row.
    - Dots = players placed by template
    - Value printed *under* each dot
    - Returns a DataFrame of cluster averages for that row
    """
    formation = row.get(TEAM1_FORMATION_COL, DEFAULT_FORMATION)
    coords = coords_for_match(formation)
    ratings = [row.get(col, np.nan) for col in TEAM1_PLAYERS]

    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.set_title(title, fontsize=14, fontweight="bold")
    ax.set_xlim(X_MIN, X_MAX)
    ax.set_ylim(Y_MIN, Y_MAX)
    ax.invert_yaxis()
    ax.set_aspect("equal")
    ax.axis("off")

    # Pitch border
    ax.plot([X_MIN, X_MAX, X_MAX, X_MIN, X_MIN],
            [Y_MIN, Y_MIN, Y_MAX, Y_MAX, Y_MIN], color="black", lw=2)

    # Players
    for i, ((x, y), rating) in enumerate(zip(coords, ratings), start=1):
        ax.scatter(x, y, s=260, color="gold", edgecolor="black", zorder=3)
        # label (optional): player index slightly above
        ax.text(x, y - 0.55, f"{rating:.1f}" if not pd.isna(rating) else "NA",
                ha="center", va="top", fontsize=9, color="blue")  # value UNDER the dot
        ax.text(x, y + 0.35, f"P{i}", ha="center", va="bottom", fontsize=8, color="black")

    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, dpi=160, bbox_inches="tight")
        print(f"📷 Formation figure saved to: {save_path}")
    plt.close(fig)

    # Cluster averages for this row
    cluster_values = compute_cluster_features_for_row(row)
    cluster_df = pd.DataFrame(
        [(k.replace("Cluster_", "").replace("_Avg", ""), v)
         for k, v in cluster_values.items() if k.endswith("_Avg")],
        columns=["Cluster", "Avg_Rating"]
    ).sort_values("Cluster").reset_index(drop=True)

    print("\n⚙️  Cluster Averages for this Formation:")
    print(cluster_df.to_string(index=False))
    return cluster_df

# ------------------ Main ------------------
def main():
    if not EXCEL_PATH.exists():
        raise FileNotFoundError(f"Excel file not found at: {EXCEL_PATH}")

    xl = pd.ExcelFile(EXCEL_PATH)
    if INPUT_SHEET not in xl.sheet_names:
        raise ValueError(f"Sheet '{INPUT_SHEET}' not found. Found: {xl.sheet_names}")

    # --- TRAIN ---
    train_df = pd.read_excel(EXCEL_PATH, sheet_name=INPUT_SHEET)
    eng_train = engineer_dataset(train_df)
    print(f"✅ Training data processed. Shape: {eng_train.shape}")
    models = run_models(eng_train)

    # --- TEST & PREDICT ---
    eng_test = pd.DataFrame()
    cluster_viz_df = pd.DataFrame()
    if TEST_SHEET in xl.sheet_names:
        test_df = pd.read_excel(EXCEL_PATH, sheet_name=TEST_SHEET)
        eng_test = engineer_dataset(test_df)
        print(f"\n✅ Test data processed. Shape: {eng_test.shape}")

        feat_cols = [c for c in eng_test.columns if c.startswith("Cluster_") and c.endswith("_Avg")]
        X_test = eng_test[feat_cols]

        for label, model in models.items():
            if hasattr(model, "predict"):
                y_pred = model.predict(X_test)
                eng_test[f"Pred_{label}"] = y_pred
                print(f"\n🔹 Predicted {label}:")
                print(pd.DataFrame({"Prediction": y_pred}).head())

        # Visualize first test row and capture cluster averages
        if len(eng_test) > 0:
            print("\n🎯 Visualizing first test match setup...")
            cluster_viz_df = visualize_formation(
                eng_test.iloc[0],
                title="Predicted Team1 Formation (Next Match)",
                save_path=FIG_PATH
            )

    # --- SAVE TO EXCEL ---
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        eng_train.to_excel(writer, sheet_name="Engineered_Train", index=False)
        if not eng_test.empty:
            eng_test.to_excel(writer, sheet_name="Predictions", index=False)
        if not cluster_viz_df.empty:
            cluster_viz_df.to_excel(writer, sheet_name="Viz_Cluster_Averages", index=False)

    print(f"\n✅ Results saved to: {OUTPUT_PATH}")
    if FIG_PATH.exists():
        print(f"✅ Formation image saved to: {FIG_PATH}")

if __name__ == "__main__":
    main()
