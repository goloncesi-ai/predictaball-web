#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Jan 30 17:42:17 2026

@author: kagancalikoglu
"""

from pathlib import Path

from gol_oncesi_engine import PathsConfig, SimulationConfig, GolOncesiEngine, MatchConfig
from gol_oncesi_engine.formations import available_formations

def main():
    # TODO: update these 3 paths to your machine
    paths = PathsConfig(
        main_folder=Path('/Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League'),
        output_folder=Path('/Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Algorithm/PredictaBall/Outputs'),
        logo_folder=Path('/Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Algorithm/PredictaBall/Logos'),
    )
    cfg = SimulationConfig(n_sims_home_perspective=25, n_sims_away_perspective=25)

    engine = GolOncesiEngine(paths, cfg, verbose=True)

    home_team = "Karagümrük" #input("Enter HOME team name: ").strip()
    away_team = "Fenerbahçe" #input("Enter AWAY team name: ").strip()

    print("\nAvailable formations:\n" + ", ".join(available_formations()))
    home_form = "4-4-2" #input(f"Enter formation for {home_team}: ").strip()
    away_form = "4-3-2-1" #input(f"Enter formation for {away_team}: ").strip()

    # HMM suggestions (optional)
    t_home = engine.suggest_adjustments_hmm(home_team)
    t_away = engine.suggest_adjustments_hmm(away_team)
    print("\nHMM suggested mean adjustments:")
    print(f"  {home_team}: {t_home['suggested_adj_pct']:+.1f}% (avg change {t_home['avg_change_pct']:+.1f}%)")
    print(f"  {away_team}: {t_away['suggested_adj_pct']:+.1f}% (avg change {t_away['avg_change_pct']:+.1f}%)")

    # choose adjustments (here: apply the suggested ones)
    m = MatchConfig(
        home_team=home_team,
        away_team=away_team,
        home_formation=home_form,
        away_formation=away_form,
        home_adj_pct= 10,  #float(t_home["suggested_adj_pct"]),
        away_adj_pct= -20 #float(t_away["suggested_adj_pct"]),
    )

    result = engine.run_match(m, draw_heatmaps=True, generate_images=True)

    print("\n========================")
    print("RESULTS (combined)")
    print("========================")
    print(f"Home win: {result.combined['home_win']*100:.2f}%")
    print(f"Draw    : {result.combined['draw']*100:.2f}%")
    print(f"Away win: {result.combined['home_loss']*100:.2f}%")
    print(f"Expected goals: {result.combined['exp_home_goals']:.2f} - {result.combined['exp_away_goals']:.2f}")
    print(f"Headline scoreline: {result.combined['headline_score']}")
    if result.heatmaps:
        print("\nHeatmaps saved:")
        for k, p in result.heatmaps.items():
            print(f"  {k}: {p}")

if __name__ == "__main__":
    main()

#testest