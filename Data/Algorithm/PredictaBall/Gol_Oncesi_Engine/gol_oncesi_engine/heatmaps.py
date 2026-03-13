"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from .config import SimulationConfig
from .clusters import Cluster, mirror_cluster_x
from .formations import parse_formation, coords_team1, coords_team2

def _normalize(v: float, vmin: float, vmax: float) -> float:
    if v is None or np.isnan(v):
        return 0.0
    if vmax <= vmin:
        return 0.5
    return float((v - vmin) / (vmax - vmin))

def _draw_base_grid(ax, cfg: SimulationConfig):
    ax.set_xlim(cfg.x_min - 0.5, cfg.x_max + 0.5)
    ax.set_ylim(cfg.y_min - 0.5, cfg.y_max + 0.5)
    ax.set_aspect("equal")
    for x in range(cfg.x_min, cfg.x_max + 1):
        for y in range(cfg.y_min, cfg.y_max + 1):
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, fill=False, linewidth=0.8))
    ax.set_xticks(range(cfg.x_min, cfg.x_max + 1))
    ax.set_yticks(range(cfg.y_min, cfg.y_max + 1))
    ax.set_xlabel("X (1..5)")
    ax.set_ylabel("Y (1..9)")

def _short_cluster_name(name: str) -> str:
    return name.replace("_", "\n")

def compute_cluster_avgs_for_team(
    team_coords: List[Tuple[int, int]],
    team_player_avgs: Dict[str, float],
    team_prefix: str,  # "Team1Player" or "Team2Player"
    clusters: List[Cluster],
) -> Dict[str, float]:
    pts = []
    for i, (x, y) in enumerate(team_coords, start=1):
        key = f"{team_prefix}{i}"
        val = float(team_player_avgs.get(key, np.nan))
        pts.append((x, y, val))

    out: Dict[str, float] = {}
    for c in clusters:
        vals = []
        for x, y, v in pts:
            if np.isnan(v):
                continue
            if c.contains(x, y, margin=0):
                vals.append(v)
        out[c.name] = float(np.mean(vals)) if len(vals) else np.nan
    return out

class HeatmapPlotter:
    def __init__(self, cfg: SimulationConfig):
        self.cfg = cfg

    def player_rating_two_panel(
        self,
        team1_name: str,
        team2_name: str,
        team1_formation: str,
        team2_formation: str,
        team1_player_avgs: Dict[str, float],
        team2_player_avgs: Dict[str, float],
        output_path: Path,
        title: str = "Player Rating Heatmap",
    ) -> Path:
        team1_formation = parse_formation(team1_formation)
        team2_formation = parse_formation(team2_formation)

        coords1 = coords_team1(team1_formation)
        coords2 = coords_team2(team2_formation, self.cfg)

        vals1 = [float(team1_player_avgs.get(f"Team1Player{i}", np.nan)) for i in range(1, 12)]
        vals2 = [float(team2_player_avgs.get(f"Team2Player{i}", np.nan)) for i in range(1, 12)]
        all_vals = [v for v in (vals1 + vals2) if not np.isnan(v)]
        vmin, vmax = (min(all_vals), max(all_vals)) if all_vals else (1.0, 10.0)

        fig, axes = plt.subplots(1, 2, figsize=(14, 8), constrained_layout=True)
        fig.suptitle(f"{title} (min={vmin:.2f}, max={vmax:.2f})", fontsize=16)

        cmap_left = plt.get_cmap("YlOrRd")
        cmap_right = plt.get_cmap("Blues")

        ax = axes[0]
        _draw_base_grid(ax, self.cfg)
        ax.set_title(f"{team1_name} ({team1_formation})")
        for idx, ((x, y), v) in enumerate(zip(coords1, vals1), start=1):
            t = _normalize(v, vmin, vmax)
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=cmap_left(t), alpha=0.9, edgecolor="black", linewidth=1.0))
            ax.text(x, y, f"{idx}\n{v:.2f}", ha="center", va="center", fontsize=9)

        ax = axes[1]
        _draw_base_grid(ax, self.cfg)
        ax.set_title(f"{team2_name} ({team2_formation})")
        for idx, ((x, y), v) in enumerate(zip(coords2, vals2), start=1):
            t = _normalize(v, vmin, vmax)
            ax.add_patch(Rectangle((x - 0.5, y - 0.5), 1, 1, facecolor=cmap_right(t), alpha=0.9, edgecolor="black", linewidth=1.0))
            ax.text(x, y, f"{idx}\n{v:.2f}", ha="center", va="center", fontsize=9)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200)
        plt.close(fig)
        return output_path

    def cluster_two_panel(
        self,
        team1_name: str,
        team2_name: str,
        team1_formation: str,
        team2_formation: str,
        team1_player_avgs: Dict[str, float],
        team2_player_avgs: Dict[str, float],
        clusters: List[Cluster],
        output_path: Path,
        title: str,
    ) -> Path:
        team1_formation = parse_formation(team1_formation)
        team2_formation = parse_formation(team2_formation)

        coords1 = coords_team1(team1_formation)
        coords2 = coords_team2(team2_formation, self.cfg)

        team1_clusters = clusters
        team2_clusters = [mirror_cluster_x(c, self.cfg) for c in clusters]

        cavg1 = compute_cluster_avgs_for_team(coords1, team1_player_avgs, "Team1Player", team1_clusters)
        cavg2 = compute_cluster_avgs_for_team(coords2, team2_player_avgs, "Team2Player", team2_clusters)

        all_vals = [v for v in list(cavg1.values()) + list(cavg2.values()) if not np.isnan(v)]
        vmin, vmax = (min(all_vals), max(all_vals)) if all_vals else (1.0, 10.0)

        fig, axes = plt.subplots(1, 2, figsize=(14, 8), constrained_layout=True)
        fig.suptitle(f"{title} (min={vmin:.2f}, max={vmax:.2f})", fontsize=16)

        cmap_left = plt.get_cmap("YlOrRd")
        cmap_right = plt.get_cmap("Blues")

        ax = axes[0]
        _draw_base_grid(ax, self.cfg)
        ax.set_title(f"{team1_name} ({team1_formation})")
        for c in team1_clusters:
            v = cavg1.get(c.name, np.nan)
            t = _normalize(v, vmin, vmax)
            ax.add_patch(Rectangle((c.x1 - 0.5, c.y1 - 0.5), c.x2 - c.x1 + 1, c.y2 - c.y1 + 1,
                                   facecolor=cmap_left(t), alpha=0.55, edgecolor="black", linewidth=1.2))
            cx = (c.x1 + c.x2) / 2.0
            cy = (c.y1 + c.y2) / 2.0
            label = f"{_short_cluster_name(c.name)}\n{v:.2f}" if not np.isnan(v) else f"{_short_cluster_name(c.name)}\nNA"
            ax.text(cx, cy, label, ha="center", va="center", fontsize=9)

        ax = axes[1]
        _draw_base_grid(ax, self.cfg)
        ax.set_title(f"{team2_name} ({team2_formation})")
        for c in team2_clusters:
            v = cavg2.get(c.name, np.nan)
            t = _normalize(v, vmin, vmax)
            ax.add_patch(Rectangle((c.x1 - 0.5, c.y1 - 0.5), c.x2 - c.x1 + 1, c.y2 - c.y1 + 1,
                                   facecolor=cmap_right(t), alpha=0.55, edgecolor="black", linewidth=1.2))
            cx = (c.x1 + c.x2) / 2.0
            cy = (c.y1 + c.y2) / 2.0
            label = f"{_short_cluster_name(c.name)}\n{v:.2f}" if not np.isnan(v) else f"{_short_cluster_name(c.name)}\nNA"
            ax.text(cx, cy, label, ha="center", va="center", fontsize=9)

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(output_path, dpi=200)
        plt.close(fig)
        return output_path
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .config import SimulationConfig
from .clusters import Cluster, mirror_cluster_x
from .formations import parse_formation, coords_team1, coords_team2


def compute_cluster_avgs_for_team(
    team_coords: List[Tuple[int, int]],
    team_player_avgs: Dict[str, float],
    team_prefix: str,
    clusters: List[Cluster],
) -> Dict[str, float]:
    pts = []
    for i, (x, y) in enumerate(team_coords, start=1):
        key = f"{team_prefix}{i}"
        val = float(team_player_avgs.get(key, np.nan))
        pts.append((x, y, val))

    out: Dict[str, float] = {}
    for c in clusters:
        vals = []
        for x, y, v in pts:
            if np.isnan(v):
                continue
            if c.contains(x, y, margin=0):
                vals.append(v)
        out[c.name] = float(np.mean(vals)) if len(vals) else np.nan
    return out


def _paste_logo(canvas: Image.Image, logo: Image.Image, center_x: int, center_y: int, size: int):
    logo_resized = logo.copy()
    logo_resized.thumbnail((size, size), Image.Resampling.LANCZOS)
    w, h = logo_resized.size
    x = center_x - w // 2
    y = center_y - h // 2
    if logo_resized.mode == "RGBA":
        canvas.paste(logo_resized, (x, y), logo_resized)
    else:
        canvas.paste(logo_resized, (x, y))


def _draw_vertical_text(
    canvas: Image.Image,
    text: str,
    x_center: int,
    y_center: int,
    rotate: int,
    font: ImageFont.FreeTypeFont,
):
    tmp = Image.new("RGBA", (320, 36), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.text((5, 5), text, fill="black", font=font)
    tmp = tmp.rotate(rotate, expand=True)
    canvas.paste(tmp, (x_center - tmp.size[0] // 2, y_center - tmp.size[1] // 2), tmp)


class HeatmapPlotter:
    def __init__(self, cfg: SimulationConfig):
        self.cfg = cfg

    def main_cluster_heatmap(
        self,
        logo_folder_path: Path,
        team1_logo: str,
        team2_logo: str,
        team1_formation: str,
        team2_formation: str,
        team1_player_avgs: Dict[str, float],
        team2_player_avgs: Dict[str, float],
        clusters: List[Cluster],
        output_path: Path,
        base_filename: str = "heat_map_base.png",
    ) -> Path:
        team1_formation = parse_formation(team1_formation)
        team2_formation = parse_formation(team2_formation)

        coords1 = coords_team1(team1_formation)
        coords2 = coords_team2(team2_formation, self.cfg)

        home_clusters = clusters
        away_clusters = [mirror_cluster_x(c, self.cfg) for c in clusters]

        cavg_home = compute_cluster_avgs_for_team(coords1, team1_player_avgs, "Team1Player", home_clusters)
        cavg_away = compute_cluster_avgs_for_team(coords2, team2_player_avgs, "Team2Player", away_clusters)

        canvas = Image.open(logo_folder_path / base_filename).convert("RGBA")

        team1_logo_path = logo_folder_path / team1_logo
        team2_logo_path = logo_folder_path / team2_logo
        logo1 = Image.open(team1_logo_path).convert("RGBA") if team1_logo_path.exists() else None
        logo2 = Image.open(team2_logo_path).convert("RGBA") if team2_logo_path.exists() else None

        # ── Main logos: top-left and top-right header boxes ───────────────────
        if logo1:
            _paste_logo(canvas, logo1, center_x=130,  center_y=95, size=155)
        if logo2:
            _paste_logo(canvas, logo2, center_x=1370, center_y=95, size=155)

        # ── Pitch layout (base 1500x900) ──────────────────────────────────────
        # Pitch starts at y=207, 3 equal rows of 231px each
        # Row y-centers: 322, 553, 784
        # Left half x-center: 500  |  Right half x-center: 1000
        # Logo size: 110px (fits cleanly in 231px tall box)

        LOGO_SIZE = 130
        LEFT_X    = 500
        RIGHT_X   = 1000

        matchups = [
            # (home_cluster,  away_cluster,  left_y, right_y)
            ("Back_Left",  "Wing_Right", 322, 322),
            ("Mid_Def",    "Mid_Att",    553, 553),
            ("Back_Right", "Wing_Left",  784, 784),
        ]

        for home_name, away_name, left_y, right_y in matchups:
            vh = cavg_home.get(home_name, np.nan)
            va = cavg_away.get(away_name, np.nan)

            both_nan = np.isnan(vh) and np.isnan(va)
            home_wins = (not both_nan) and (np.isnan(va) or (not np.isnan(vh) and vh >= va))

            dominant_logo = logo1 if home_wins else logo2

            if dominant_logo:
                _paste_logo(canvas, dominant_logo, LEFT_X,  left_y,  LOGO_SIZE)
                _paste_logo(canvas, dominant_logo, RIGHT_X, right_y, LOGO_SIZE)

        # ── Goalkeeper Zone vertical text ─────────────────────────────────────
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
        except Exception:
            try:
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20)
            except Exception:
                font = ImageFont.load_default()

        gk_home = cavg_home.get("Goalkeeper_Zone", np.nan)
        gk_away = cavg_away.get("Goalkeeper_Zone", np.nan)
        fmt = lambda v: "NA" if np.isnan(v) else f"{v:.2f}"

        _draw_vertical_text(canvas, f"Goalkeeper Zone  {fmt(gk_home)}",
                            x_center=250,   y_center=553, rotate=90,  font=font)
        _draw_vertical_text(canvas, f"Goalkeeper Zone  {fmt(gk_away)}",
                            x_center=1250, y_center=553, rotate=270, font=font)

        # ── Save ──────────────────────────────────────────────────────────────
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        canvas.convert("RGB").save(output_path)
        return output_path
