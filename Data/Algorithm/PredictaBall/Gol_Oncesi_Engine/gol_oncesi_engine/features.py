from __future__ import annotations
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from .clusters import Cluster, build_clusters

TEAM1_FORMATION_COL = "Team1Formation"
TEAM2_FORMATION_COL = "Team2Formation"
OUTCOME_COL = "Outcome_3W1D0L"

TEAM1_PLAYERS = [f"Team1Player{i}" for i in range(1, 12)]
TEAM2_PLAYERS = [f"Team2Player{i}" for i in range(1, 12)]

CLUSTERS = build_clusters()
CLUSTER_NAMES = [c.name for c in CLUSTERS]

def player_cluster_memberships(x: int, y: int, clusters: List[Cluster], margin: int = 0) -> List[str]:
    return [c.name for c in clusters if c.contains(x, y, margin=margin)]

def _aggregate_clusters(coords: List[Tuple[int, int]], ratings: List[float], prefix: str) -> Dict[str, float]:
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

def _safe_div(
    a: float,
    b: float,
    hi_ratio: float = 1.9,
    lo_ratio: float = 0.1,
    eq_ratio: float = 1.0,
    treat_one_as_bad: bool = True,
) -> float:
    if pd.isna(a) or pd.isna(b):
        return np.nan
    if a == 0 and b == 0:
        return eq_ratio
    bad = (a == 0) or (b == 0) or (treat_one_as_bad and ((a == 1) or (b == 1)))
    if bad:
        if a > b:
            return hi_ratio
        if a < b:
            return lo_ratio
        return eq_ratio
    return a / b

def _competition_ratios(row: pd.Series) -> Dict[str, float]:
    pairs = [
        ("Wing_Right", "Back_Left"),
        ("Wing_Left", "Back_Right"),
        ("Mid_Att", "Mid_Def"),
        ("Left_Strip", "Right_Strip"),
        ("Right_Strip", "Left_Strip"),
        ("Mid_Strip", "Mid_Strip"),
        ("Wing_Right", "Back_Right"),
        ("Wing_Left", "Back_Left"),
        ("Mid_Att", "Goalkeeper_Zone"),
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
    getv = row.get
    for l, r in pairs:
        a = getv(f"Team1_Cluster_{l}_Avg")
        b = getv(f"Team2_Cluster_{r}_Avg")
        out[f"Comp_T1_{l}_over_T2_{r}"] = _safe_div(a, b)

        a2 = getv(f"Team2_Cluster_{l}_Avg")
        b2 = getv(f"Team1_Cluster_{r}_Avg")
        out[f"Comp_T2_{l}_over_T1_{r}"] = _safe_div(a2, b2)
    return out

def compute_cluster_features_for_row(
    row: pd.Series,
    coords_team1_fn,
    coords_team2_fn,
) -> Dict[str, float]:
    f1 = row.get(TEAM1_FORMATION_COL)
    coords1 = coords_team1_fn(f1)
    ratings1 = [row.get(col, np.nan) for col in TEAM1_PLAYERS]
    agg1 = _aggregate_clusters(coords1, ratings1, prefix="Team1_")

    f2 = row.get(TEAM2_FORMATION_COL, f1)
    coords2 = coords_team2_fn(f2)
    ratings2 = [row.get(col, np.nan) for col in TEAM2_PLAYERS]
    agg2 = _aggregate_clusters(coords2, ratings2, prefix="Team2_")

    comp = _competition_ratios(pd.Series({**agg1, **agg2}))
    return {**agg1, **agg2, **comp}

def engineer_dataset(df: pd.DataFrame, coords_team1_fn, coords_team2_fn) -> pd.DataFrame:
    feats = df.apply(lambda r: compute_cluster_features_for_row(r, coords_team1_fn, coords_team2_fn),
                     axis=1, result_type="expand")
    out = pd.concat([df.reset_index(drop=True), feats.reset_index(drop=True)], axis=1)
    if {"Team1_Goals", "Team2_Goals"}.issubset(out.columns):
        g1, g2 = out["Team1_Goals"], out["Team2_Goals"]
        out[OUTCOME_COL] = np.where(g1 > g2, 3, np.where(g1 == g2, 1, 0))
    elif "Result" in out.columns:
        res = out["Result"].astype(str).str.upper().str.strip()
        out[OUTCOME_COL] = res.map({"W": 3, "D": 1, "L": 0})
    return out

def make_unique_columns(df: pd.DataFrame) -> pd.DataFrame:
    cols = list(df.columns)
    seen = {}
    new_cols = []
    for c in cols:
        if c not in seen:
            seen[c] = 0
            new_cols.append(c)
        else:
            seen[c] += 1
            new_cols.append(f"{c}__dup{seen[c]}")
    out = df.copy()
    out.columns = new_cols
    return out
