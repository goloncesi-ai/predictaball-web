from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

@dataclass(frozen=True)
class PathsConfig:
    main_folder: Path
    output_folder: Path
    logo_folder: Path

    def ensure(self) -> None:
        self.output_folder.mkdir(parents=True, exist_ok=True)

@dataclass(frozen=True)
class SimulationConfig:
    # perspective split: 500 + 500 = 1000 total
    n_sims_home_perspective: int = 500
    n_sims_away_perspective: int = 500

    # rating sampling bounds
    rating_min: float = 1.0
    rating_max: float = 10.0

    # coordinate grid (pitch matrix)
    x_min: int = 1
    x_max: int = 5
    y_min: int = 1
    y_max: int = 9

    # adjustment clamps
    manual_adj_min: float = -50.0
    manual_adj_max: float = 50.0

    # HMM suggestion clamp (kept conservative)
    hmm_suggest_min: float = -10.0
    hmm_suggest_max: float = 10.0

    # your existing scaling: mean multiplier = 1 + adj/700
    mean_adj_denominator: float = 700.0

    random_seed: int = 42
