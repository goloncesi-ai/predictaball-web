from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestRegressor
import matplotlib.pyplot as plt

# ------------------ User-configurable paths ------------------
EXCEL_PATH = Path("/Users/kagancalikoglu/Documents/PredictaBall/Inputs/Fenerbahce_Games_Input.xlsx")
INPUT_SHEET = "Team_Inputs"
TEST_SHEET = "Team_Test"
OUTPUT_PATH = Path("/Users/kagancalikoglu/Documents/PredictaBall/Outputs/FB_USG__Matrix_Model_Output.xlsx")
FIG_PATH = Path("Formation_Visualization.png")

# Column names
TEAM1_FORMATION_COL = "Team1Formation"
TEAM2_FORMATION_COL = "Team2Formation"  # if missing, mirror Team1
TEAM1_PLAYERS = [f"Team1Player{i}" for i in range(1, 12)]
TEAM2_PLAYERS = [f"Team2Player{i}" for i in range(1, 12)]

# Targets
TARGET_COLS_LINEAR = [
    "Team1_TotalShots",
    "Team1_BallPosses",
    "Team2_TotalShots",
    "Team2_BallPosses",
]
GOAL_TARGETS = ["Team1_Goals", "Team2_Goals"]
OUTCOME_COL = "Outcome_3W1D0L"  # Multinomial classification

# ------------------ Grid & clusters ------------------
X_MIN, X_MAX = 1, 5     # left → right (Team1 def → attack)
Y_MIN, Y_MAX = 1, 9     # top → bottom (left → right)

@dataclass(frozen=True)
class Cluster:
    name: str
    x1: int; x2: int
    y1: int; y2: int
    def contains_with_margin(self, x: int, y: int, margin: int = 0) -> bool:
        return (self.x1 - margin <= x <= self.x2 + margin) and (self.y1 - margin <= y <= self.y2 + margin)

def build_clusters() -> List[Cluster]:
    # 5x9 pitch logical clusters
    return [
        # Goalkeeper zone
        Cluster("Goalkeeper_Zone", 1, 1, 1, 9),

        # Defense
        Cluster("Back_Left",  2, 3, 1, 3),
        Cluster("Back_Right", 2, 3, 7, 9),

        # Midfield
        Cluster("Mid_Def",  2, 3, 4, 6),
        Cluster("Mid_Att",  4, 5, 4, 6),

        # Attack
        Cluster("Wing_Left",  4, 5, 1, 3),
        Cluster("Wing_Right", 4, 5, 7, 9),

        # Linear strips
        Cluster("Left_Strip",  2, 5, 1, 3),
        Cluster("Mid_Strip",   2, 5, 4, 6),
        Cluster("Right_Strip", 2, 5, 7, 9),
    ]

CLUSTERS = build_clusters()
CLUSTER_NAMES = [c.name for c in CLUSTERS]

# ------------------ Formation templates ------------------
FORMATION_TEMPLATES: Dict[str, List[Tuple[int, int]]] = {
    # === 4-back systems ===
    "4-1-3-2": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,5),(4,3),(4,5),(4,7),(5,4),(5,6)],
    "4-2-3-1": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,4),(3,6),(4,3),(4,5),(4,7),(5,5)],
    "4-3-3":   [(1,5),(2,2),(2,4),(2,6),(2,8),(3,4),(3,5),(3,6),(4,2),(4,5),(4,8)],
    "4-4-2":   [(1,5),(2,2),(2,4),(2,6),(2,8),(3,3),(3,7),(4,4),(4,6),(5,3),(5,7)],
    "4-1-4-1": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,5),(4,2),(4,4),(4,6),(4,8),(5,5)],
    "4-2-2-2": [(1,5),(2,2),(2,4),(2,6),(2,8),(3,3),(3,7),(4,4),(4,6),(5,3),(5,7)],
    # === 3-back systems ===
    "3-4-3":   [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,3),(4,5),(4,7)],
    "3-4-1-2": [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,5),(5,3),(5,7)],
    "3-4-2-1": [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,6),(3,8),(4,3),(4,7),(5,5)],
    "3-5-2":   [(1,5),(2,3),(2,5),(2,7),(3,2),(3,4),(3,5),(3,6),(4,5),(5,3),(5,7)],
    "3-1-4-2": [(1,5),(2,3),(2,5),(2,7),(3,5),(4,2),(4,4),(4,6),(4,8),(5,3),(5,7)],
    # === 5-back systems ===
    "5-3-2":   [(1,5),(2,2),(2,3),(2,5),(2,7),(2,8),(3,4),(3,5),(4,5),(5,3),(5,7)],
    "5-4-1":   [(1,5),(2,2),(2,3),(2,5),(2,7),(2,8),(3,4),(3,5),(4,5),(5,3),(5,7)],
}
DEFAULT_FORMATION = "4-2-3-1"

def parse_formation(s: str) -> str:
    if not isinstance(s, str) or not s.strip():
        return DEFAULT_FORMATION
    s = s.strip().replace(" ", "")
    return s if s in FORMATION_TEMPLATES else DEFAULT_FORMATION

def coords_for_match_team1(formation_str: str) -> List[Tuple[int,int]]:
    return FORMATION_TEMPLATES[parse_formation(formation_str)]

def coords_for_match_team2(formation_str: str) -> List[Tuple[int,int]]:
    """Mirror Team1 coordinates across the vertical axis so Team2 attacks left."""
    coords_t1 = FORMATION_TEMPLATES[parse_formation(formation_str)]
    mirror = lambda x: (X_MIN + X_MAX) - x
    return [(mirror(x), y) for (x, y) in coords_t1]

# ------------------ Cluster feature engineering ------------------
def player_cluster_memberships(x: int, y: int, clusters: List[Cluster], margin: int = 0) -> List[str]:
    return [c.name for c in clusters if c.contains_with_margin(x, y, margin=margin)]

def _aggregate_clusters(coords: List[Tuple[int,int]], ratings: List[float], prefix: str) -> Dict[str, float]:
    bucket: Dict[str, List[float]] = {name: [] for name in CLUSTER_NAMES}
    for (x, y), rating in zip(coords, ratings):
        if pd.isna(rating):
            continue
        for cname in player_cluster_memberships(x, y, CLUSTERS, margin=0):
            bucket[cname].append(float(rating))
    agg: Dict[str, float] = {}
    for cname, vals in bucket.items():
        agg[f"{prefix}Cluster_{cname}_Avg"] = float(np.mean(vals)) if len(vals) else np.nan
        agg[f"{prefix}Cluster_{cname}_Cnt"] = int(len(vals))
    return agg

def _safe_div(a: float, b: float) -> float:
    if pd.isna(a) or pd.isna(b) or b == 0:
        return np.nan
    return a / b

def _competition_ratios(row: pd.Series) -> Dict[str, float]:
    """
    Compute ratios of Team1 attacking zones vs Team2 defending zones,
    and mirrored Team2 attacking vs Team1 defending.
    Generates all competition features expected by the feature lists below.
    """
    getv = row.get

    pairs = [
        # --- From Team1 attacking vs Team2 defending ---
        ("Wing_Right", "Back_Left"),
        ("Wing_Left", "Back_Right"),
        ("Mid_Att", "Mid_Def"),
        ("Left_Strip", "Right_Strip"),
        ("Right_Strip", "Left_Strip"),
        ("Mid_Strip", "Mid_Strip"),
        ("Wing_Right", "Back_Right"),
        ("Wing_Left", "Back_Left"),
        ("Mid_Att", "Goalkeeper_Zone"),

        # --- From Team2 attacking vs Team1 defending (mirrored matchups) ---
        ("Back_Left", "Wing_Right"),
        ("Back_Right", "Wing_Left"),
        ("Mid_Def", "Mid_Att"),
        ("Right_Strip", "Left_Strip"),
        ("Left_Strip", "Right_Strip"),
        ("Mid_Strip", "Mid_Strip"),
        ("Back_Left", "Wing_Left"),
        ("Back_Right", "Wing_Right"),
        ("Goalkeeper_Zone", "Mid_Att"),
    ]

    out = {}
    for l, r in pairs:
        # Team1 attacking vs Team2 defending
        a = getv(f"Team1_Cluster_{l}_Avg")
        b = getv(f"Team2_Cluster_{r}_Avg")
        out[f"Comp_T1_{l}_over_T2_{r}"] = _safe_div(a, b)

        # Team2 attacking vs Team1 defending (mirror)
        a2 = getv(f"Team2_Cluster_{l}_Avg")
        b2 = getv(f"Team1_Cluster_{r}_Avg")
        out[f"Comp_T2_{l}_over_T1_{r}"] = _safe_div(a2, b2)

    return out

def compute_cluster_features_for_row(row: pd.Series) -> Dict[str, float]:
    # Team1
    f1 = row.get(TEAM1_FORMATION_COL, DEFAULT_FORMATION)
    coords1 = coords_for_match_team1(f1)
    ratings1 = [row.get(col, np.nan) for col in TEAM1_PLAYERS]
    agg1 = _aggregate_clusters(coords1, ratings1, prefix="Team1_")

    # Team2 (mirror Team1 formation if Team2_Formation missing)
    f2 = row.get(TEAM2_FORMATION_COL, f1)
    coords2 = coords_for_match_team2(f2)
    ratings2 = [row.get(col, np.nan) for col in TEAM2_PLAYERS]
    agg2 = _aggregate_clusters(coords2, ratings2, prefix="Team2_")

    # Competition ratios
    comp = _competition_ratios(pd.Series({**agg1, **agg2}))

    return {**agg1, **agg2, **comp}

def engineer_dataset(df: pd.DataFrame) -> pd.DataFrame:
    features = df.apply(compute_cluster_features_for_row, axis=1, result_type="expand")
    out = pd.concat([df.reset_index(drop=True), features.reset_index(drop=True)], axis=1)
    # derive outcome 3/1/0 if goals or result present
    if {"Team1_Goals", "Team2_Goals"}.issubset(out.columns):
        g1, g2 = out["Team1_Goals"], out["Team2_Goals"]
        out[OUTCOME_COL] = np.where(g1 > g2, 3, np.where(g1 == g2, 1, 0))
    elif "Result" in out.columns:
        res = out["Result"].astype(str).str.upper().str.strip()
        out[OUTCOME_COL] = res.map({"W": 3, "D": 1, "L": 0})
    return out

# ------------------ Modeling helpers ------------------
def _valid_Xy(X: pd.DataFrame, y: pd.Series):
    mask = y.notna() & X.notna().all(axis=1)
    return X[mask], y[mask]

def _report_fit(label: str, model, X, y):
    if hasattr(model, "score"):
        try:
            score = model.score(X, y)
            print(f"{label} | Score: {score:.3f}")
        except Exception as e:
            print(f"{label} | Score unavailable: {e}")

# ------------------ Feature lists (manual control) ------------------

# Core cluster averages (Team 1)
TEAM1_CLUSTER_AVG = [f"Team1_Cluster_{c}_Avg" for c in [
    "Goalkeeper_Zone", "Back_Left", "Back_Right", "Mid_Def", "Mid_Att",
    "Wing_Left", "Wing_Right", "Left_Strip", "Mid_Strip", "Right_Strip"
]]

# Core cluster averages (Team 2)
TEAM2_CLUSTER_AVG = [f"Team2_Cluster_{c}_Avg" for c in [
    "Goalkeeper_Zone", "Back_Left", "Back_Right", "Mid_Def", "Mid_Att",
    "Wing_Left", "Wing_Right", "Left_Strip", "Mid_Strip", "Right_Strip"
]]

TEAM1_ATT = [f"Team1_Cluster_{c}_Avg" for c in ["Mid_Att", "Wing_Left", "Wing_Right", "Mid_Strip"]]
TEAM1_DEF = [f"Team1_Cluster_{c}_Avg" for c in ["Goalkeeper_Zone", "Back_Left", "Back_Right", "Mid_Def"]]
TEAM1_GK  = ["Team1_Cluster_Goalkeeper_Zone_Avg"]
TEAM2_GK  = ["Team2_Cluster_Goalkeeper_Zone_Avg"]

# Team 1 attacking vs Team 2 defending
COMP_FEATURES_T1_ATTACK = [
    "Comp_T1_Wing_Right_over_T2_Back_Left",
    "Comp_T1_Wing_Left_over_T2_Back_Right",
    "Comp_T1_Mid_Att_over_T2_Mid_Def",
    "Comp_T1_Left_Strip_over_T2_Right_Strip",
    "Comp_T1_Right_Strip_over_T2_Left_Strip",
    "Comp_T1_Mid_Strip_over_T2_Mid_Strip",
]

# Team 2 attacking vs Team 1 defending (mirror set)
COMP_FEATURES_T2_ATTACK = [
    "Comp_T1_Back_Left_over_T2_Wing_Right",
    "Comp_T1_Back_Right_over_T2_Wing_Left",
    "Comp_T1_Mid_Def_over_T2_Mid_Att",
    "Comp_T1_Right_Strip_over_T2_Left_Strip",
    "Comp_T1_Left_Strip_over_T2_Right_Strip",
    "Comp_T1_Mid_Strip_over_T2_Mid_Strip",
]

# Combined competition features for general models
COMPETITION_FEATURES = COMP_FEATURES_T1_ATTACK + COMP_FEATURES_T2_ATTACK

# Default full set used for general models (Outcome, Shots, Possession)
FEATURES_ALL = COMPETITION_FEATURES + TEAM1_GK  # you can expand with TEAM1/TEAM2 cluster avgs if desired

# Goal models: selective (attacking vs defending clusters)
#FEATURES_GOALS_T1 = COMP_FEATURES_T1_ATTACK + TEAM2_GK
FEATURES_GOALS_T1 = COMPETITION_FEATURES + TEAM2_GK
#FEATURES_GOALS_T2 = COMP_FEATURES_T2_ATTACK + TEAM1_GK
FEATURES_GOALS_T2 = COMPETITION_FEATURES + TEAM1_GK

# Ensure all feature columns exist helper (prevents feature-name mismatch)
def _ensure_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = set(FEATURES_ALL + FEATURES_GOALS_T1 + FEATURES_GOALS_T2)
    for col in expected:
        if col not in df.columns:
            df[col] = np.nan
    return df

# ------------------ Model builders ------------------
def run_models(df_engineered: pd.DataFrame):
    models = {}

    # Guarantee all columns exist (avoids train-time mismatch)
    df_engineered = _ensure_feature_columns(df_engineered)

    # Use manual feature lists
    X_all = df_engineered[FEATURES_ALL]
    X_t1_goal = df_engineered[FEATURES_GOALS_T1]
    X_t2_goal = df_engineered[FEATURES_GOALS_T2]

    # ===== Multinomial outcome (0/1/3) =====
    if OUTCOME_COL in df_engineered.columns:
        y_outcome = df_engineered[OUTCOME_COL]
        X_tr, y_tr = _valid_Xy(X_all, y_outcome)
        pipe_mn = Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(multi_class="multinomial", max_iter=200, solver="lbfgs"))
        ])
        pipe_mn.fit(X_tr, y_tr)
        _report_fit("Multinomial Outcome (0/1/3)", pipe_mn, X_tr, y_tr)
        models[OUTCOME_COL] = pipe_mn

    # ===== Random Forest models for shots/possession =====
    for t in TARGET_COLS_LINEAR:
        if t in df_engineered.columns:
            y = df_engineered[t]
            X_tr, y_tr = _valid_Xy(X_all, y)
            rf = RandomForestRegressor(
                n_estimators=400,
                max_depth=None,
                min_samples_leaf=2,
                random_state=42
            )
            rf.fit(X_tr, y_tr)
            _report_fit(f"RF: {t}", rf, X_tr, y_tr)
            models[t] = rf

    # ===== Random Forest models for goals =====
    if "Team1_Goals" in df_engineered.columns:
        y_t1 = df_engineered["Team1_Goals"]
        X_tr, y_tr = _valid_Xy(X_t1_goal, y_t1)
        rf1 = RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=42)
        rf1.fit(X_tr, y_tr)
        _report_fit("RF: Team1_Goals", rf1, X_tr, y_tr)
        models["Team1_Goals"] = rf1

    if "Team2_Goals" in df_engineered.columns:
        y_t2 = df_engineered["Team2_Goals"]
        X_tr, y_tr = _valid_Xy(X_t2_goal, y_t2)
        rf2 = RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=42)
        rf2.fit(X_tr, y_tr)
        _report_fit("RF: Team2_Goals", rf2, X_tr, y_tr)
        models["Team2_Goals"] = rf2

    # ------------------ Coefficient/Importance export ------------------
    coef_rows = []

    def add_coefs(label: str, model, feature_names: list):
        """
        Extract coefficients or feature importances and append to coef_rows.
        Supports Linear/Logistic (coef_) and RandomForest (feature_importances_).
        """
        # Unwrap pipeline if needed
        if isinstance(model, Pipeline):
            if 'ols' in model.named_steps:     # Linear Regression
                model_core = model.named_steps['ols']
            elif 'clf' in model.named_steps:   # Logistic Regression
                model_core = model.named_steps['clf']
            else:
                return
        else:
            model_core = model  # Could be RandomForest directly

        # Linear/Logistic: coef_
        if hasattr(model_core, "coef_"):
            coefs = model_core.coef_
            if hasattr(coefs, "ndim") and coefs.ndim == 2:  # multinomial
                for class_index, row in enumerate(coefs):
                    for f, val in zip(feature_names, row):
                        coef_rows.append({
                            "Model": f"{label}_Class{class_index}",
                            "Feature": f,
                            "Coefficient": float(val),
                        })
            else:
                for f, val in zip(feature_names, coefs):
                    coef_rows.append({
                        "Model": label,
                        "Feature": f,
                        "Coefficient": float(val),
                    })
            return

        # RandomForest: feature_importances_
        if hasattr(model_core, "feature_importances_"):
            importances = model_core.feature_importances_
            for f, val in zip(feature_names, importances):
                coef_rows.append({
                    "Model": label,
                    "Feature": f,
                    "Importance": float(val),
                })
            return

    # Add each model’s coefficients/importances
    for name, mdl in models.items():
        if name in GOAL_TARGETS:
            feats = FEATURES_GOALS_T1 if "Team1" in name else FEATURES_GOALS_T2
        else:
            feats = FEATURES_ALL
        add_coefs(name, mdl, feats)

    coef_df = pd.DataFrame(coef_rows)
    return models, coef_df

# ------------------ Visualization ------------------
def visualize_formation(row: pd.Series, title: str = "Team Formation with Player Values",
                        save_path: Path | None = None) -> pd.DataFrame:
    formation = row.get(TEAM1_FORMATION_COL, DEFAULT_FORMATION)
    coords = coords_for_match_team1(formation)
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
        ax.text(x, y - 0.55, f"{rating:.1f}" if not pd.isna(rating) else "NA",
                ha="center", va="top", fontsize=9, color="blue")
        ax.text(x, y + 0.35, f"P{i}", ha="center", va="bottom", fontsize=8, color="black")

    fig.tight_layout()
    if save_path is not None:
        fig.savefig(save_path, dpi=160, bbox_inches="tight")
        print(f"📷 Formation figure saved to: {save_path}")
    plt.close(fig)

    # Cluster averages for this row (Team1 only view)
    cluster_values = {}
    f1 = row.get(TEAM1_FORMATION_COL, DEFAULT_FORMATION)
    coords1 = coords_for_match_team1(f1)
    ratings1 = [row.get(col, np.nan) for col in TEAM1_PLAYERS]
    bucket = {name: [] for name in CLUSTER_NAMES}
    for (x,y), r in zip(coords1, ratings1):
        if not pd.isna(r):
            for cname in player_cluster_memberships(x, y, CLUSTERS, margin=0):
                bucket[cname].append(float(r))
    for cname, vals in bucket.items():
        cluster_values[cname] = float(np.mean(vals)) if len(vals) else np.nan

    cluster_df = pd.DataFrame(
        [(k, v) for k, v in cluster_values.items()],
        columns=["Cluster", "Avg_Rating"]
    ).sort_values("Cluster").reset_index(drop=True)

    print("\n⚙️  Team1 Cluster Averages for this Formation:")
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
    train_df = train_df.fillna(0)
    eng_train = engineer_dataset(train_df)
    eng_train = _ensure_feature_columns(eng_train)
    print(f"✅ Training data processed. Shape: {eng_train.shape}")

    models, coef_df = run_models(eng_train)

    # --- TEST & PREDICT ---
    eng_test = pd.DataFrame()
    cluster_viz_df = pd.DataFrame()
    if TEST_SHEET in xl.sheet_names:
        test_df = pd.read_excel(EXCEL_PATH, sheet_name=TEST_SHEET)
        test_df = test_df.fillna(0)
        eng_test = engineer_dataset(test_df)
        eng_test = _ensure_feature_columns(eng_test)
        print(f"\n✅ Test data processed. Shape: {eng_test.shape}")

        # Feature sets for predictions
        X_all_test = eng_test[FEATURES_ALL]
        X_t1_goal_test = eng_test[FEATURES_GOALS_T1]
        X_t2_goal_test = eng_test[FEATURES_GOALS_T2]

        #print("Any NaNs?", np.isnan(X_all_test).any())
        #print("NaNs per column:\n", np.isnan(X_all_test).sum())
        #print("Dtypes:", X_all_test.dtypes)

        # Multinomial outcome
        if OUTCOME_COL in models:
            y_proba = models[OUTCOME_COL].predict_proba(X_all_test)
            class_labels = models[OUTCOME_COL].named_steps["clf"].classes_
            for c_idx, c_val in enumerate(class_labels):
                eng_test[f"PredP_{OUTCOME_COL}_{c_val}"] = y_proba[:, c_idx]
            eng_test[f"Pred_{OUTCOME_COL}"] = models[OUTCOME_COL].predict(X_all_test)

        # Linear/RF targets
        for t in TARGET_COLS_LINEAR:
            if t in models:
                eng_test[f"Pred_{t}"] = models[t].predict(X_all_test)

        # Goals
        if "Team1_Goals" in models:
            eng_test["Pred_Team1_Goals"] = np.clip(
                models["Team1_Goals"].predict(X_t1_goal_test), a_min=0, a_max=None
            )
        if "Team2_Goals" in models:
            eng_test["Pred_Team2_Goals"] = np.clip(
                models["Team2_Goals"].predict(X_t2_goal_test), a_min=0, a_max=None
            )

        # Visualize first test row (Team1)
        if len(eng_test) > 0:
            print("\n🎯 Visualizing first test match setup (Team1):")
            cluster_viz_df = visualize_formation(
                eng_test.iloc[0],
                title="Predicted Team1 Formation (Next Match)",
                save_path=FIG_PATH
            )

    # --- SAVE TO EXCEL ---
    with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl") as writer:
        eng_train.to_excel(writer, sheet_name="Engineered_Train", index=False)
        coef_df.to_excel(writer, sheet_name="Model_Coefficients", index=False)
        if not eng_test.empty:
            eng_test.to_excel(writer, sheet_name="Predictions", index=False)
        if not cluster_viz_df.empty:
            cluster_viz_df.to_excel(writer, sheet_name="Viz_Cluster_Averages_T1", index=False)

    # --- PIVOT TABLE (64 pairs) & PROBABILITY STATS ---
    if not eng_test.empty and "Pred_Outcome_3W1D0L" in eng_test.columns:
        # Build counts by (Team1Formation, Team2Formation) × outcome
        pivot = (
            eng_test
            .pivot_table(
                index=["Team1Formation", "Team2Formation"],
                columns="Pred_Outcome_3W1D0L",
                aggfunc="size",
                fill_value=0
            )
        )

        # Ensure outcome columns are exactly [0, 1, 3]
        for col in [0, 1, 3]:
            if col not in pivot.columns:
                pivot[col] = 0
        pivot = pivot[[0, 1, 3]]  # order columns

        # Ensure *all* 8×8 formation pairs appear (even if zero count)
        t1_list = sorted(eng_test["Team1Formation"].dropna().unique().tolist())
        t2_list = sorted(eng_test["Team2Formation"].dropna().unique().tolist())
        full_index = pd.MultiIndex.from_product(
            [t1_list, t2_list],
            names=["Team1Formation", "Team2Formation"]
        )
        pivot = pivot.reindex(full_index, fill_value=0).sort_index()

        # Pretty index to columns if you want a flat sheet
        pivot_reset = pivot.reset_index()

        total_matches = len(eng_test)
        win_prob = (eng_test["Pred_Outcome_3W1D0L"] == 3).sum() / total_matches
        draw_prob = (eng_test["Pred_Outcome_3W1D0L"] == 1).sum() / total_matches
        lose_prob = (eng_test["Pred_Outcome_3W1D0L"] == 0).sum() / total_matches

        print("\n📊 Predicted Outcome Probabilities:")
        print(f" - Possibility of Team 1 winning: {win_prob:.2%}")
        print(f" - Possibility of Team 1 drawing: {draw_prob:.2%}")
        print(f" - Possibility of Team 1 losing:  {lose_prob:.2%}")

        # Append pivot after everything else is saved
        with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            pivot_reset.to_excel(writer, sheet_name="Formation_Pivot", index=False)

        # --- PREDICTED FINAL SCORE AGGREGATION ---
        if {"Pred_Team1_Goals", "Pred_Team2_Goals", "Pred_Outcome_3W1D0L"}.issubset(eng_test.columns):
            df_scores = eng_test.copy()

            def predict_final_score(row):
                g1 = row["Pred_Team1_Goals"]
                g2 = row["Pred_Team2_Goals"]
                outcome = row["Pred_Outcome_3W1D0L"]

                if pd.isna(g1) or pd.isna(g2) or pd.isna(outcome):
                    return np.nan

                # Match your Excel formula behavior
                if outcome == 3:
                    return f"{int(np.ceil(g1))}-{int(np.floor(g2))}"
                elif outcome == 0:
                    return f"{int(np.floor(g1))}-{int(np.ceil(g2))}"
                else:
                    if abs(g1 - g2) < 1:
                        return f"{int(np.floor(g1))}-{int(np.floor(g2))}"
                    else:
                        hi = int(np.floor(max(g1, g2)))
                        lo = int(np.ceil(min(g1, g2)))
                        return f"{hi}-{lo}"

            df_scores["Predicted_Final_Score"] = df_scores.apply(predict_final_score, axis=1)

            # Count unique scores (robust to pandas version)
            score_counts = df_scores["Predicted_Final_Score"].value_counts().reset_index()
            score_counts.columns = ["Score", "Count"]

            if not score_counts.empty:
                top_score = score_counts.iloc[0]["Score"]
                print(f"\n🏁 The expected score of the game is {top_score}")
            else:
                print("\n⚠️ No valid scores generated — check prediction inputs.")

            with pd.ExcelWriter(OUTPUT_PATH, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
                score_counts.to_excel(writer, sheet_name="Predicted_Scores", index=False)

    print(f"\n✅ Results saved to: {OUTPUT_PATH}")
    if FIG_PATH.exists():
        print(f"✅ Formation image saved to: {FIG_PATH}")


if __name__ == "__main__":
    main()
