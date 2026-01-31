from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional, Any

import pandas as pd

from .config import PathsConfig, SimulationConfig
from .formations import parse_formation, available_formations, coords_team1, coords_team2
from .clusters import main_clusters, strip_clusters
from .simulation import Simulator, PerspectiveSimResult
from .hmm_trend import compute_hmm_efficiency_change
from .heatmaps import HeatmapPlotter
from .images import ImageGenerator

def _parse_score_str(s: str) -> Tuple[int, int]:
    try:
        a, b = str(s).split("-")
        return int(a), int(b)
    except Exception:
        return 0, 0

def _weighted_goals_from_topN(score_df: pd.DataFrame) -> Tuple[float, float, int]:
    if score_df is None or len(score_df) == 0:
        return 0.0, 0.0, 0
    total = 0
    sum_g1 = 0
    sum_g2 = 0
    for _, row in score_df.iterrows():
        score = row.get("Score", "0-0")
        cnt = row.get("Count", 0)
        try:
            c = int(cnt)
        except Exception:
            c = 0
        if c <= 0:
            continue
        g1, g2 = _parse_score_str(score)
        sum_g1 += g1 * c
        sum_g2 += g2 * c
        total += c
    if total == 0:
        return 0.0, 0.0, 0
    return (sum_g1 / total), (sum_g2 / total), total

def combine_perspectives(home_sim: PerspectiveSimResult, away_sim: PerspectiveSimResult) -> Dict[str, float]:
    p1 = home_sim.probs
    p2 = away_sim.probs

    home_win_1 = p1["team1_win"]; draw_1 = p1["draw"]; home_loss_1 = p1["team1_loss"]
    # away_sim has team1=away_team. For "home" view: swap win/loss.
    home_win_2 = p2["team1_loss"]; draw_2 = p2["draw"]; home_loss_2 = p2["team1_win"]

    home_win = (home_win_1 + home_win_2) / 2.0
    draw = (draw_1 + draw_2) / 2.0
    home_loss = (home_loss_1 + home_loss_2) / 2.0

    exp_h1, exp_a1, n1 = _weighted_goals_from_topN(home_sim.top5_scores)
    exp_away_as_team1, exp_home_as_team2, n2 = _weighted_goals_from_topN(away_sim.top5_scores)
    exp_h2 = exp_home_as_team2
    exp_a2 = exp_away_as_team1

    if (n1 + n2) > 0:
        exp_home_goals = (exp_h1 * n1 + exp_h2 * n2) / (n1 + n2)
        exp_away_goals = (exp_a1 * n1 + exp_a2 * n2) / (n1 + n2)
    else:
        exp_home_goals = 0.0
        exp_away_goals = 0.0

    headline_home = int(round(exp_home_goals))
    headline_away = int(round(exp_away_goals))

    return {
        "home_win": float(home_win),
        "draw": float(draw),
        "home_loss": float(home_loss),
        "exp_home_goals": float(exp_home_goals),
        "exp_away_goals": float(exp_away_goals),
        "headline_score": f"{headline_home}-{headline_away}",
    }

@dataclass(frozen=True)
class MatchConfig:
    home_team: str
    away_team: str
    home_formation: str
    away_formation: str
    # efficiency adjustments in percent (same semantics as your prototype)
    home_adj_pct: float = 0.0
    away_adj_pct: float = 0.0

@dataclass
class MatchResult:
    home_sim: PerspectiveSimResult
    away_sim: PerspectiveSimResult
    combined: Dict[str, float]
    heatmaps: Dict[str, Path]

class GolOncesiEngine:
    def __init__(self, paths: PathsConfig, sim_cfg: SimulationConfig, verbose: bool = True):
        self.paths = paths
        self.cfg = sim_cfg
        self.verbose = verbose
        self.paths.ensure()

        self.simulator = Simulator(main_folder=self.paths.main_folder, cfg=self.cfg, verbose=verbose)
        self.heatmaps = HeatmapPlotter(self.cfg)
        self.image_gen = ImageGenerator(self.paths.logo_folder)

    def suggest_adjustments_hmm(self, team_name: str) -> Dict[str, float]:
        return compute_hmm_efficiency_change(
            self.paths.main_folder,
            team_name,
            clamp_min=self.cfg.hmm_suggest_min,
            clamp_max=self.cfg.hmm_suggest_max,
            random_state=self.cfg.random_seed
        )

    def run_match(self, m: MatchConfig, draw_heatmaps: bool = True, generate_images: bool = False) -> MatchResult:
        home_form = parse_formation(m.home_formation)
        away_form = parse_formation(m.away_formation)

        # 1) Home perspective: Team1=home team, Team2=away team
        home_sim = self.simulator.run_perspective(
            team1_name=m.home_team,
            team2_name=m.away_team,
            team1_formation=home_form,
            team2_formation=away_form,
            n_sims=self.cfg.n_sims_home_perspective,
            team1_homeaway="Home",
            team1_adj_pct=m.home_adj_pct,
            team2_adj_pct=m.away_adj_pct,
            coords_team1_fn=coords_team1,
            coords_team2_fn=lambda f: coords_team2(f, self.cfg),
        )

        # 2) Away perspective: Team1=away team, Team2=home team (still label Team1 as "Home" within that dataset)
        away_sim = self.simulator.run_perspective(
            team1_name=m.away_team,
            team2_name=m.home_team,
            team1_formation=away_form,
            team2_formation=home_form,
            n_sims=self.cfg.n_sims_away_perspective,
            team1_homeaway="Home",
            team1_adj_pct=m.away_adj_pct,
            team2_adj_pct=m.home_adj_pct,
            coords_team1_fn=coords_team1,
            coords_team2_fn=lambda f: coords_team2(f, self.cfg),
        )

        combined = combine_perspectives(home_sim, away_sim)

        heatmap_paths: Dict[str, Path] = {}
        if draw_heatmaps:
            t1_avgs = home_sim.avg_player_ratings["team1_players"]
            t2_avgs = home_sim.avg_player_ratings["team2_players"]

            player_path = self.paths.output_folder / "player_heatmap.png"
            main_cluster_path = self.paths.output_folder / "main_cluster_heatmap.png"
            strip_cluster_path = self.paths.output_folder / "strip_cluster_heatmap.png"

            heatmap_paths["player"] = self.heatmaps.player_rating_two_panel(
                team1_name=m.home_team,
                team2_name=m.away_team,
                team1_formation=home_form,
                team2_formation=away_form,
                team1_player_avgs=t1_avgs,
                team2_player_avgs=t2_avgs,
                output_path=player_path,
            )
            heatmap_paths["main_clusters"] = self.heatmaps.cluster_two_panel(
                team1_name=m.home_team,
                team2_name=m.away_team,
                team1_formation=home_form,
                team2_formation=away_form,
                team1_player_avgs=t1_avgs,
                team2_player_avgs=t2_avgs,
                clusters=main_clusters(),
                title="Main Cluster Heatmap",
                output_path=main_cluster_path,
            )
            heatmap_paths["strip_clusters"] = self.heatmaps.cluster_two_panel(
                team1_name=m.home_team,
                team2_name=m.away_team,
                team1_formation=home_form,
                team2_formation=away_form,
                team1_player_avgs=t1_avgs,
                team2_player_avgs=t2_avgs,
                clusters=strip_clusters(),
                title="Strip Cluster Heatmap",
                output_path=strip_cluster_path,
            )

        if generate_images:
            self.image_gen.generate(m.home_team, m.away_team, combined)

        return MatchResult(home_sim=home_sim, away_sim=away_sim, combined=combined, heatmaps=heatmap_paths)
