from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

import numpy as np
import pandas as pd

from .config import SimulationConfig
from .data_io import TEAM1_PLAYERS, TEAM2_PLAYERS, safe_mean_std, read_team_df
from .formations import parse_formation
from .features import engineer_dataset, make_unique_columns
from .models import ModelTrainer, ensure_feature_columns, OUTCOME_BASE_FEATURES, OUTCOME_COL, FEATURES_ALL, FEATURES_GOALS_T1, FEATURES_GOALS_T2, TARGET_COLS_LINEAR

@dataclass
class PerspectiveSimResult:
    team1: str
    team2: str
    team1_formation: str
    team2_formation: str
    team1_homeaway: str
    simulated_matches: int
    avg_team_ratings: Dict[str, float]
    avg_player_ratings: Dict[str, Dict[str, float]]
    probs: Dict[str, float]
    top_score: str
    top5_scores: pd.DataFrame
    adjustments: Dict[str, float]

class Simulator:
    def __init__(self, main_folder, cfg: SimulationConfig, verbose: bool = True):
        self.main_folder = main_folder
        self.cfg = cfg
        self.verbose = verbose
        np.random.seed(cfg.random_seed)
        self.trainer = ModelTrainer(random_state=cfg.random_seed, verbose=verbose)

    def generate_team_test(
        self,
        team1_df: pd.DataFrame,
        team2_df: pd.DataFrame,
        team1_name: str,
        team2_name: str,
        team1_homeaway: str,
        team1_formation: str,
        team2_formation: str,
        n_sims: int,
        team1_adj_pct: float = 0.0,
        team2_adj_pct: float = 0.0,
    ) -> pd.DataFrame:
        team1_formation = parse_formation(team1_formation)
        team2_formation = parse_formation(team2_formation)

        team1_stats = {col: safe_mean_std(team1_df[col]) for col in TEAM1_PLAYERS if col in team1_df.columns}
        # NOTE: historical files store opponent as Team2Player*, but your earlier logic mapped using Team1Player in team2_df
        team2_stats = {
            f"Team2Player{i}": safe_mean_std(team2_df[f"Team1Player{i}"])
            for i in range(1, 12)
            if f"Team1Player{i}" in team2_df.columns
        }

        mult1 = 1.0 + (team1_adj_pct / self.cfg.mean_adj_denominator)
        mult2 = 1.0 + (team2_adj_pct / self.cfg.mean_adj_denominator)

        rows = []
        for _ in range(int(n_sims)):
            row = {
                "Team1": team1_name,
                "Team2": team2_name,
                "Team1H_A": team1_homeaway,
                "Team1Formation": team1_formation,
                "Team2Formation": team2_formation,
            }
            for i in range(1, 12):
                m1, s1 = team1_stats.get(f"Team1Player{i}", (5.0, 1.0))
                v = np.clip(np.random.normal(m1 * mult1, s1), self.cfg.rating_min, self.cfg.rating_max)
                row[f"Team1Player{i}"] = round(float(v), 2)

            for i in range(1, 12):
                m2, s2 = team2_stats.get(f"Team2Player{i}", (5.0, 1.0))
                v = np.clip(np.random.normal(m2 * mult2, s2), self.cfg.rating_min, self.cfg.rating_max)
                row[f"Team2Player{i}"] = round(float(v), 2)

            rows.append(row)

        return pd.DataFrame(rows)

    def run_perspective(
        self,
        team1_name: str,
        team2_name: str,
        team1_formation: str,
        team2_formation: str,
        n_sims: int,
        team1_homeaway: str,
        team1_adj_pct: float = 0.0,
        team2_adj_pct: float = 0.0,
        coords_team1_fn=None,
        coords_team2_fn=None,
    ) -> PerspectiveSimResult:
        def sanitize_inference_features(
            X_test: pd.DataFrame,
            X_train_reference: pd.DataFrame,
        ) -> pd.DataFrame:
            """
            Ensure inference matrices are finite for sklearn estimators.
            Fill strategy:
            1) train medians per feature
            2) sensible defaults by feature family
            3) final global zero fallback
            """
            X = X_test.copy().replace([np.inf, -np.inf], np.nan)
            X_ref = X_train_reference.copy().replace([np.inf, -np.inf], np.nan)

            medians = X_ref.median(numeric_only=True)
            X = X.fillna(medians)

            for col in X.columns:
                if col.startswith("Comp_"):
                    X[col] = X[col].fillna(1.0)
                elif col.endswith("_Cluster_Goalkeeper_Zone_Avg"):
                    X[col] = X[col].fillna(5.0)
                elif col.endswith("_Cnt"):
                    X[col] = X[col].fillna(0.0)
                elif col.endswith("_Avg"):
                    X[col] = X[col].fillna(5.0)

            X = X.fillna(0.0)
            return X

        team1_df = read_team_df(self.main_folder, team1_name)
        team2_df = read_team_df(self.main_folder, team2_name)

        test_df = self.generate_team_test(
            team1_df, team2_df,
            team1_name, team2_name,
            team1_homeaway=team1_homeaway,
            team1_formation=team1_formation,
            team2_formation=team2_formation,
            n_sims=n_sims,
            team1_adj_pct=team1_adj_pct,
            team2_adj_pct=team2_adj_pct,
        )

        team1_player_avgs = test_df[TEAM1_PLAYERS].apply(pd.to_numeric, errors="coerce").mean(axis=0).to_dict()
        team2_player_avgs = test_df[TEAM2_PLAYERS].apply(pd.to_numeric, errors="coerce").mean(axis=0).to_dict()

        avg_t1_rating = float(test_df[TEAM1_PLAYERS].mean().mean())
        avg_t2_rating = float(test_df[TEAM2_PLAYERS].mean().mean())

        if coords_team1_fn is None or coords_team2_fn is None:
            raise ValueError("coords_team1_fn and coords_team2_fn must be provided")

        eng_train = engineer_dataset(team1_df, coords_team1_fn, coords_team2_fn)
        eng_train = make_unique_columns(eng_train)
        eng_train = ensure_feature_columns(eng_train)
        models = self.trainer.fit(eng_train)

        eng_test = engineer_dataset(test_df, coords_team1_fn, coords_team2_fn)
        eng_test = ensure_feature_columns(eng_test)
        eng_test = make_unique_columns(eng_test)

        X_all_train = eng_train[FEATURES_ALL]
        X_t1_goal_train = eng_train[FEATURES_GOALS_T1]
        X_t2_goal_train = eng_train[FEATURES_GOALS_T2]
        X_outcome_train = eng_train[OUTCOME_BASE_FEATURES].copy()

        X_all_test = sanitize_inference_features(eng_test[FEATURES_ALL], X_all_train)
        X_t1_goal_test = sanitize_inference_features(eng_test[FEATURES_GOALS_T1], X_t1_goal_train)
        X_t2_goal_test = sanitize_inference_features(eng_test[FEATURES_GOALS_T2], X_t2_goal_train)
        X_outcome_test = sanitize_inference_features(eng_test[OUTCOME_BASE_FEATURES].copy(), X_outcome_train)

        if models.outcome_model is not None:
            proba = models.outcome_model.predict_proba(X_outcome_test)
            class_labels = models.outcome_model.named_steps["clf"].classes_
            for c_idx, c_val in enumerate(class_labels):
                eng_test[f"PredP_{OUTCOME_COL}_{c_val}"] = proba[:, c_idx]
            eng_test[f"Pred_{OUTCOME_COL}"] = models.outcome_model.predict(X_outcome_test)

        for t in TARGET_COLS_LINEAR:
            if t in models.rf_targets:
                eng_test[f"Pred_{t}"] = models.rf_targets[t].predict(X_all_test)

        if "Team1_Goals" in models.rf_goals:
            eng_test["Pred_Team1_Goals"] = np.clip(models.rf_goals["Team1_Goals"].predict(X_t1_goal_test), 0, None)
        if "Team2_Goals" in models.rf_goals:
            eng_test["Pred_Team2_Goals"] = np.clip(models.rf_goals["Team2_Goals"].predict(X_t2_goal_test), 0, None)

        total = len(eng_test)
        if total == 0:
            raise RuntimeError("No simulated matches produced.")

        win_prob = float((eng_test[f"Pred_{OUTCOME_COL}"] == 3).sum() / total)
        draw_prob = float((eng_test[f"Pred_{OUTCOME_COL}"] == 1).sum() / total)
        lose_prob = float((eng_test[f"Pred_{OUTCOME_COL}"] == 0).sum() / total)

        score_counts = pd.DataFrame(columns=["Score", "Count"])
        if {"Pred_Team1_Goals", "Pred_Team2_Goals", f"Pred_{OUTCOME_COL}"}.issubset(eng_test.columns):
            df_scores = eng_test.copy()

            def predict_final_score(row):
                g1, g2, outcome = row["Pred_Team1_Goals"], row["Pred_Team2_Goals"], row[f"Pred_{OUTCOME_COL}"]
                if pd.isna(g1) or pd.isna(g2) or pd.isna(outcome):
                    return np.nan
                if outcome == 3:
                    return f"{int(np.ceil(g1))}-{int(np.floor(g2))}"
                if outcome == 0:
                    return f"{int(np.floor(g1))}-{int(np.ceil(g2))}"
                if abs(g1 - g2) < 1:
                    return f"{int(np.floor(g1))}-{int(np.floor(g2))}"
                hi, lo = int(np.floor(max(g1, g2))), int(np.ceil(min(g1, g2)))
                return f"{hi}-{lo}"

            df_scores["Predicted_Final_Score"] = df_scores.apply(predict_final_score, axis=1)
            score_counts = df_scores["Predicted_Final_Score"].value_counts().reset_index()
            score_counts.columns = ["Score", "Count"]

        top_score = str(score_counts.iloc[0]["Score"]) if not score_counts.empty else "0-0"
        top5 = score_counts.head(5).copy()

        return PerspectiveSimResult(
            team1=team1_name,
            team2=team2_name,
            team1_formation=parse_formation(team1_formation),
            team2_formation=parse_formation(team2_formation),
            team1_homeaway=team1_homeaway,
            simulated_matches=int(total),
            avg_team_ratings={"team1": avg_t1_rating, "team2": avg_t2_rating},
            avg_player_ratings={
                "team1_players": {k: float(v) for k, v in team1_player_avgs.items()},
                "team2_players": {k: float(v) for k, v in team2_player_avgs.items()},
            },
            probs={"team1_win": win_prob, "draw": draw_prob, "team1_loss": lose_prob},
            top_score=top_score,
            top5_scores=top5,
            adjustments={"team1_adj_pct": float(team1_adj_pct), "team2_adj_pct": float(team2_adj_pct)},
        )
