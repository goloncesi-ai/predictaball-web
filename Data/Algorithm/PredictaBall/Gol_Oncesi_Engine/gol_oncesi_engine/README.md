# Gol Öncesi Engine (modular refactor)

This folder contains a clean, multi-file refactor of your single-file script
(`gol_oncesi_combined_v4.py`). The goal is simple: **each file does one job**,
so you can extend/replace parts without growing one giant script forever.

## What lives where

- `config.py`  
  Paths + simulation settings (500 home sims + 500 away sims = 1000 total)

- `formations.py`  
  Formation templates, parsing, Team2 mirroring

- `clusters.py`  
  Cluster rectangles + mirroring for Team2

- `data_io.py`  
  Reading Excel files, numeric conversion, mean/std helpers

- `features.py`  
  Cluster feature engineering + competition ratios

- `models.py`  
  Multinomial ridge (W/D/L) + random forests for goals/targets

- `simulation.py`  
  Simulation generator + “run perspective” (team1 vs team2)

- `hmm_trend.py`  
  HMM (Markov) trend logic used only for the mean-adjustment suggestion

- `heatmaps.py`  
  Readable two-panel heatmaps:
  - per-player rating heatmap
  - main cluster heatmap
  - strip cluster heatmap  
  Team2 clusters are mirrored so **Goalkeeper_Zone** etc. line up correctly.

- `images.py`  
  Thin wrapper around your existing local modules:
  `KimKazanır.create_probability_image` and `tahmini_skor.create_match_image`

- `engine.py`  
  The orchestrator (`GolOncesiEngine`) that runs:
  - 500 sims home perspective
  - 500 sims away perspective
  - combine results
  - draw heatmaps once (home perspective)
  - optionally generate images

## Quick start

Copy this folder into your project, so imports look like:

```python
from gol_oncesi_engine import PathsConfig, SimulationConfig, GolOncesiEngine, MatchConfig
```

Then run the example:

```bash
python -m gol_oncesi_engine.run_match_example
```

Update the 3 paths in `run_match_example.py` to match your machine.

## Minimal usage (no prompts)

```python
from pathlib import Path
from gol_oncesi_engine import PathsConfig, SimulationConfig, GolOncesiEngine, MatchConfig

paths = PathsConfig(
    main_folder=Path(".../Turkish Super League"),
    output_folder=Path(".../Outputs"),
    logo_folder=Path(".../Logos"),
)
cfg = SimulationConfig(n_sims_home_perspective=500, n_sims_away_perspective=500)

engine = GolOncesiEngine(paths, cfg)

m = MatchConfig(
    home_team="Galatasaray",
    away_team="Fenerbahçe",
    home_formation="4-2-3-1",
    away_formation="4-3-3",
    home_adj_pct=0.0,
    away_adj_pct=0.0,
)

result = engine.run_match(m, draw_heatmaps=True, generate_images=False)
print(result.combined)
print(result.heatmaps)
```

## Notes / gotchas

- The `images.py` module expects your project to already have `KimKazanır.py`
  and `tahmini_skor.py` available on the Python path.
- Heatmaps are drawn **once** using the **home perspective** sim, as requested.
