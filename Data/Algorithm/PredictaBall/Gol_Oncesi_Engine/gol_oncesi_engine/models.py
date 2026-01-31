from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegressionCV
from sklearn.ensemble import RandomForestRegressor
from sklearn.base import BaseEstimator, TransformerMixin

from .features import make_unique_columns

OUTCOME_COL = "Outcome_3W1D0L"
TARGET_COLS_LINEAR = ["Team1_TotalShots", "Team1_BallPosses", "Team2_TotalShots", "Team2_BallPosses"]

TEAM1_GK = ["Team1_Cluster_Goalkeeper_Zone_Avg"]
TEAM2_GK = ["Team2_Cluster_Goalkeeper_Zone_Avg"]

OUTCOME_XS_T1_MAIN = [
    "Comp_T1_Wing_Right_over_T2_Back_Left",
    "Comp_T1_Wing_Left_over_T2_Back_Right",
    "Comp_T1_Mid_Att_over_T2_Mid_Def",
    "Comp_T1_Mid_Def_over_T2_Mid_Att",
    "Comp_T1_Back_Left_over_T2_Wing_Right",
    "Comp_T1_Back_Right_over_T2_Wing_Left",
]

OUTCOME_INTERACTIONS = [
    ("Comp_T1_Left_Strip_over_T2_Right_Strip", "Comp_T1_Mid_Strip_over_T2_Mid_Strip"),
    ("Comp_T1_Right_Strip_over_T2_Left_Strip", "Comp_T1_Mid_Strip_over_T2_Mid_Strip"),
]

OUTCOME_INTERACTION_BASES = sorted(set([f for pair in OUTCOME_INTERACTIONS for f in pair]))
OUTCOME_BASE_FEATURES = OUTCOME_XS_T1_MAIN + OUTCOME_INTERACTION_BASES

FEATURES_ALL = OUTCOME_BASE_FEATURES
FEATURES_GOALS_T1 = OUTCOME_BASE_FEATURES + TEAM2_GK
FEATURES_GOALS_T2 = OUTCOME_BASE_FEATURES + TEAM1_GK

class AddSpecifiedInteractions(BaseEstimator, TransformerMixin):
    def __init__(self, interactions: List[Tuple[str, str]]):
        self.interactions = interactions

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        if not isinstance(X, pd.DataFrame):
            X = pd.DataFrame(X)
        X = X.copy()
        for a, b in self.interactions:
            name = f"{a}:{b}"
            if a not in X.columns or b not in X.columns:
                X[name] = np.nan
                continue
            xa = X[a]; xb = X[b]
            if isinstance(xa, pd.DataFrame): xa = xa.iloc[:, 0]
            if isinstance(xb, pd.DataFrame): xb = xb.iloc[:, 0]
            X[name] = xa * xb
        return X

def ensure_feature_columns(df: pd.DataFrame) -> pd.DataFrame:
    expected = set(FEATURES_ALL + FEATURES_GOALS_T1 + FEATURES_GOALS_T2)
    expected |= set(OUTCOME_BASE_FEATURES)
    for a, b in OUTCOME_INTERACTIONS:
        expected.add(f"{a}:{b}")
    for col in expected:
        if col not in df.columns:
            df[col] = np.nan
    return df

def _valid_Xy(X: pd.DataFrame, y: pd.Series):
    mask = y.notna() & X.notna().all(axis=1)
    return X[mask], y[mask]

@dataclass
class FittedModels:
    outcome_model: Pipeline | None
    rf_targets: Dict[str, RandomForestRegressor]
    rf_goals: Dict[str, RandomForestRegressor]

class ModelTrainer:
    def __init__(self, random_state: int = 42, verbose: bool = True):
        self.random_state = random_state
        self.verbose = verbose

    def fit(self, df_engineered: pd.DataFrame) -> FittedModels:
        df_engineered = make_unique_columns(df_engineered)
        df_engineered = ensure_feature_columns(df_engineered)

        X_all = df_engineered[FEATURES_ALL]
        X_t1_goal = df_engineered[FEATURES_GOALS_T1]
        X_t2_goal = df_engineered[FEATURES_GOALS_T2]

        outcome_model = None
        if OUTCOME_COL in df_engineered.columns:
            y_outcome = df_engineered[OUTCOME_COL]
            X_outcome = df_engineered[OUTCOME_BASE_FEATURES].copy()
            mask = y_outcome.notna() & X_outcome.notna().all(axis=1)
            X_tr = X_outcome.loc[mask]; y_tr = y_outcome.loc[mask]
            if len(X_tr) > 0:
                outcome_model = Pipeline([
                    ("add_inter", AddSpecifiedInteractions(OUTCOME_INTERACTIONS)),
                    ("scale", StandardScaler()),
                    ("clf", LogisticRegressionCV(
                        Cs=np.logspace(-3, 3, 25),
                        cv=5,
                        penalty="l2",
                        solver="saga",
                        scoring="accuracy",
                        max_iter=5000,
                        n_jobs=-1,
                        refit=True
                    ))

                ])
                outcome_model.fit(X_tr, y_tr)
                if self.verbose:
                    try:
                        print(f"Ridge multinomial CV score: {outcome_model.score(X_tr, y_tr):.3f}")
                    except Exception:
                        pass

        rf_targets: Dict[str, RandomForestRegressor] = {}
        for t in TARGET_COLS_LINEAR:
            if t in df_engineered.columns:
                y = df_engineered[t]
                X_tr, y_tr = _valid_Xy(X_all, y)
                if len(X_tr) > 0:
                    rf = RandomForestRegressor(
                        n_estimators=400,
                        max_depth=None,
                        min_samples_leaf=2,
                        random_state=self.random_state,
                    )
                    rf.fit(X_tr, y_tr)
                    rf_targets[t] = rf

        rf_goals: Dict[str, RandomForestRegressor] = {}
        if "Team1_Goals" in df_engineered.columns:
            y = df_engineered["Team1_Goals"]
            X_tr, y_tr = _valid_Xy(X_t1_goal, y)
            if len(X_tr) > 0:
                rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=self.random_state)
                rf.fit(X_tr, y_tr)
                rf_goals["Team1_Goals"] = rf

        if "Team2_Goals" in df_engineered.columns:
            y = df_engineered["Team2_Goals"]
            X_tr, y_tr = _valid_Xy(X_t2_goal, y)
            if len(X_tr) > 0:
                rf = RandomForestRegressor(n_estimators=400, min_samples_leaf=2, random_state=self.random_state)
                rf.fit(X_tr, y_tr)
                rf_goals["Team2_Goals"] = rf

        return FittedModels(outcome_model=outcome_model, rf_targets=rf_targets, rf_goals=rf_goals)
