"""
Hidden-form football model (Fenerbahçe vs Galatasaray)
======================================================

What this script does
---------------------
1) Load the two Excel files:
   - Fenerbahçe_Games_Input.xlsx
   - Galatasaray_Games_Input.xlsx
   (Most recent match is the *first* row in both files.)

2) Build match-level features from Team1's perspective:
   - Level features: Team1 stats (goals, shots, passes, possession, etc.)
   - Relative features: diffs and ratios vs Team2 (shots_diff, passes_ratio, etc.)
   - Home/Away flags

3) Fit a per-team hidden-form model:
   - Primary: Gaussian HMM (hmmlearn)
   - Fallback: Gaussian Mixture (scikit-learn) + empirical transition matrix

4) Infer, for each team:
   - State sequence over time
   - Current-state posterior
   - Next-match state distribution (one step ahead)

5) Compute per-state W/D/L tendencies, build a pairwise state grid,
   and marginalize over next-state uncertainty to get final P(F win / Draw / G win).

6) Save all outputs to an Excel workbook: hmm_matchup_fener_gala.xlsx

Requirements
------------
- Python 3.9+
- pandas, numpy, scikit-learn, openpyxl or xlsxwriter
- Optional: hmmlearn (for true HMM). If unavailable, script falls back automatically.

Install (optional HMM):
    pip install hmmlearn

Install others (if needed):
    pip install pandas numpy scikit-learn xlsxwriter openpyxl
"""

from pathlib import Path
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

# -------------------------- Configuration --------------------------

# File paths (adjust if needed)
main_folder = Path("/Users/kagancalikoglu/Library/Mobile Documents/com~apple~CloudDocs/Gol Oncesi/Data/Turkish Super League")

team1_name = input("Enter Team 1 name: ").strip()
team2_name = input("Enter Team 2 name: ").strip()

team1_file = main_folder / team1_name / "mixed-seasons" / f"{team1_name}_Games_Input.xlsx"
team2_file = main_folder / team2_name / "mixed-seasons" / f"{team2_name}_Games_Input.xlsx"

# If your filesystem has trouble with "ç", you can rename the file and set:
# FENER_FILE = Path("Fenerbahce_Games_Input.xlsx")

# Number of latent states (try 2..5; 3 is a good start)
N_STATES = 3

# How many most-recent matches to average for the "current" posterior
LAST_K_FOR_NOW = 2

# Output Excel workbook
OUT_XLSX = Path(f"markov_matchup_{team1_name}_{team2_name}.xlsx")

# Column expected for result points (3/1/0)
POINTS_COL = "win(3)_draw(1)_lose(0)"

# Core features used (Team1 perspective)
CORE_FEATURES = [
    "t1_goals","t1_shots","t1_passes","t1_poss","t1_bigch",
    "t2_shots","t2_passes","t2_poss","t2_bigch",
    "goals_diff","shots_diff","poss_diff","passes_diff","bigch_diff",
    "passes_ratio","shots_ratio","poss_ratio","bigch_ratio",
    "home","away"
]

# -------------------------- Utilities --------------------------

def load_excel(path: Path) -> pd.DataFrame:
    """Load an Excel sheet into a DataFrame and normalize columns."""
    df = pd.read_excel(path)
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    return df

def build_team_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build features from Team1 perspective, using both Team1 and Team2 columns,
    plus relative/ratio features and home/away flags.
    Reverses order to oldest→newest and replaces all NaNs with 0.
    """
    d = df.copy()
    # reverse to chronological order (oldest -> newest)
    d = d.iloc[::-1].reset_index(drop=True)

    # Outcome (W/D/L)
    pts = pd.to_numeric(d.get(POINTS_COL, np.nan), errors="coerce")
    d["wdl"] = np.where(
    pts == 3, "W",
    np.where(pts == 1, "D",
    np.where(pts == 0, "L", "NA"))
)


    # Ensure all expected columns exist
    needed = {
        "team1_goals","team1_bigchances","team1_totalshots","team1_corners",
        "team1_passes","team1_tackels","team1_freekicks","team1_ballposses",
        "team2_goals","team2_bigchances","team2_totalshots","team2_corners",
        "team2_passes","team2_tackels","team2_freekicks","team2_ballposses",
        "team1h_a"
    }
    for col in needed:
        if col not in d.columns:
            d[col] = 0  # add missing column as zeros

    # Force numeric conversion for all numeric columns, replace invalid with 0
    num_cols = [c for c in d.columns if c != "team1h_a"]
    d[num_cols] = d[num_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    # Ratio helper
    def ratio(a, b):
        with np.errstate(divide="ignore", invalid="ignore"):
            r = np.where((a + b) == 0, 0, a / (a + b))
        return r

    feats = pd.DataFrame({
        "t1_goals": d["team1_goals"],
        "t1_bigch": d["team1_bigchances"],
        "t1_shots": d["team1_totalshots"],
        "t1_corners": d["team1_corners"],
        "t1_passes": d["team1_passes"],
        "t1_tackles": d["team1_tackels"],
        "t1_freekicks": d["team1_freekicks"],
        "t1_poss": d["team1_ballposses"],

        "t2_goals": d["team2_goals"],
        "t2_bigch": d["team2_bigchances"],
        "t2_shots": d["team2_totalshots"],
        "t2_corners": d["team2_corners"],
        "t2_passes": d["team2_passes"],
        "t2_tackles": d["team2_tackels"],
        "t2_freekicks": d["team2_freekicks"],
        "t2_poss": d["team2_ballposses"],
    })

    # Derived features (diffs)
    feats["goals_diff"]  = feats["t1_goals"] - feats["t2_goals"]
    feats["shots_diff"]  = feats["t1_shots"] - feats["t2_shots"]
    feats["poss_diff"]   = feats["t1_poss"]  - feats["t2_poss"]
    feats["passes_diff"] = feats["t1_passes"] - feats["t2_passes"]
    feats["bigch_diff"]  = feats["t1_bigch"] - feats["t2_bigch"]

    # Ratios (normalized 0–1)
    feats["passes_ratio"] = ratio(feats["t1_passes"], feats["t2_passes"])
    feats["shots_ratio"]  = ratio(feats["t1_shots"], feats["t2_shots"])
    feats["poss_ratio"]   = ratio(feats["t1_poss"], feats["t2_poss"])
    feats["bigch_ratio"]  = ratio(feats["t1_bigch"], feats["t2_bigch"])

    # Home/Away flags
    ha_raw = d["team1h_a"].astype(str).str.upper().str.strip()
    feats["home"] = (ha_raw.str.startswith("H")).astype(int)
    feats["away"] = (ha_raw.str.startswith("A")).astype(int)

    # Attach outcome
    feats["wdl"] = d["wdl"]

    # Fill any leftover NaN with 0 (final safety)
    feats = feats.fillna(0)

    return feats

def clean_core_rows(feats: pd.DataFrame) -> pd.DataFrame:
    """Drop rows missing any core feature."""
    return feats.dropna(subset=CORE_FEATURES).reset_index(drop=True)

def fit_hmm_or_gmm(X: np.ndarray, n_states=3, seed=42):
    """
    Try to fit a GaussianHMM (hmmlearn). If hmmlearn is unavailable,
    fit a GaussianMixture and estimate a first-order transition matrix from argmax states.
    Returns a dict with common keys: states, posteriors, trans, means, covs, method, model.
    """
    try:
        from hmmlearn.hmm import GaussianHMM
        model = GaussianHMM(n_components=n_states, covariance_type="full", n_iter=300, random_state=seed)
        model.fit(X)
        _, posteriors = model.score_samples(X)         # shape (T, n_states)
        states = model.predict(X)                      # Viterbi states
        trans  = model.transmat_
        means  = model.means_                          # in standardized space
        covs   = model.covars_
        method = "HMM"
        return {"model":model,"method":method,"states":states,"posteriors":posteriors,"trans":trans,"means":means,"covs":covs}
    except Exception:
        from sklearn.mixture import GaussianMixture
        gmm = GaussianMixture(n_components=n_states, covariance_type="full", random_state=seed, n_init=5)
        gmm.fit(X)
        posteriors = gmm.predict_proba(X)
        states = posteriors.argmax(axis=1)
        # Empirical transition matrix with Laplace smoothing
        counts = np.ones((n_states, n_states))
        for a, b in zip(states[:-1], states[1:]):
            counts[a, b] += 1.0
        trans = counts / counts.sum(axis=1, keepdims=True)
        means = gmm.means_
        covs  = gmm.covariances_
        method = "GMM+Markov"
        return {"model":gmm,"method":method,"states":states,"posteriors":posteriors,"trans":trans,"means":means,"covs":covs}

def next_state_distribution(fitobj, last_k=1):
    """
    Average the last_k posterior rows as 'now' distribution, then multiply by transition matrix for one-step 'next'.
    """
    gamma = fitobj["posteriors"]  # (T, K)
    trans = fitobj["trans"]       # (K, K)
    now = gamma[-last_k:, :].mean(axis=0)  # (K,)
    nxt = now @ trans                       # (K,)
    return now, nxt

def per_state_outcome_stats(states, wdl, n_states: int):
    """
    Count W/D/L per state and return Laplace-smoothed probabilities per state.
    """
    df = pd.DataFrame({"state": states, "wdl": wdl})
    tbl = (df.groupby("state")["wdl"]
             .value_counts()
             .unstack(fill_value=0)
             .reindex(range(n_states), fill_value=0))
    for c in ["W","D","L"]:
        if c not in tbl.columns:
            tbl[c] = 0
    # Laplace smoothing to get probs
    probs = (tbl + 1) / (tbl.sum(axis=1).values[:, None] + 3)
    probs = probs[["W","D","L"]]
    return tbl, probs

def pairwise_outcome_grid(F_state_probs: pd.DataFrame, G_state_probs: pd.DataFrame) -> pd.DataFrame:
    """
    For each state pair (i, j), estimate P(F win), P(Draw), P(G win) from the per-state tendencies,
    then renormalize. This is a transparent heuristic you can later replace with a learned model.
    """
    K = F_state_probs.shape[0]
    rows = []
    for i in range(K):
        for j in range(K):
            f_w, f_d, f_l = F_state_probs.loc[i, ["W","D","L"]].values
            g_w, g_d, g_l = G_state_probs.loc[j, ["W","D","L"]].values
            fwin = f_w * (1 - g_w)
            gwin = g_w * (1 - f_w)
            draw = 0.5*(f_d + g_d) * (1 - 0.5*(f_w + g_w))
            vec = np.array([fwin, draw, gwin], dtype=float)
            if not np.isfinite(vec).all() or vec.sum() <= 0:
                vec = np.array([1/3, 1/3, 1/3])
            vec = vec / vec.sum()
            rows.append({"F_state": i, "G_state": j,
                         "P(F win)": vec[0], "P(Draw)": vec[1], "P(G win)": vec[2]})
    return pd.DataFrame(rows)

def matchup_probs(F_next: np.ndarray, G_next: np.ndarray, pair_grid: pd.DataFrame) -> pd.Series:
    """
    Marginalize over both teams' next-state distributions using the pairwise grid.
    Returns a Series: [F win, Draw, G win].
    """
    K = len(F_next)
    # Build (K, K, 3) tensor
    mats = {k: np.zeros((K, K)) for k in ["P(F win)", "P(Draw)", "P(G win)"]}
    for _, row in pair_grid.iterrows():
        i, j = int(row["F_state"]), int(row["G_state"])
        for key in mats:
            mats[key][i, j] = row[key]
    out = np.zeros(3)
    keys = ["P(F win)", "P(Draw)", "P(G win)"]
    for idx, key in enumerate(keys):
        out[idx] = (mats[key] * np.outer(F_next, G_next)).sum()
    out = out / out.sum()
    return pd.Series(out, index=["F win", "Draw", "G win"])

def invert_scaling(means_std: np.ndarray, scaler, feature_names: list[str]) -> pd.DataFrame:
    """
    Convert standardized means back to original feature scale for interpretability.
    """
    mu_orig = means_std * scaler.scale_[None, :] + scaler.mean_[None, :]
    df = pd.DataFrame(mu_orig, columns=feature_names)
    df.insert(0, "state", range(df.shape[0]))
    return df

# -------------------------- Main pipeline --------------------------

def main():
    # Load
    team1 = load_excel(team1_file)
    team2 = load_excel(team2_file)

    # Build features
    team1_feats = build_team_dataset(team1)
    team2_feats = build_team_dataset(team2)

    # Keep rows with full core features
    team1X = clean_core_rows(team1_feats)
    team2X = clean_core_rows(team2_feats)

    # Align outcomes
    team1_wdl = team1X["wdl"].reset_index(drop=True)
    team2_wdl = team2X["wdl"].reset_index(drop=True)

    # Scale features
    from sklearn.preprocessing import StandardScaler
    scaler_1 = StandardScaler().fit(team1X[CORE_FEATURES])
    scaler_2 = StandardScaler().fit(team2X[CORE_FEATURES])
    X_1 = scaler_1.transform(team1X[CORE_FEATURES])
    X_2 = scaler_2.transform(team2X[CORE_FEATURES])

    # Fit models
    M1 = fit_hmm_or_gmm(X_1, n_states=N_STATES, seed=13)
    M2 = fit_hmm_or_gmm(X_2, n_states=N_STATES, seed=37)

    # Now/Next distributions
    M1_now, M1_next = next_state_distribution(M1, last_k=LAST_K_FOR_NOW)
    M2_now, M2_next = next_state_distribution(M2, last_k=LAST_K_FOR_NOW)

    # Per-state WDL tendencies
    M1_counts, M1_state_probs = per_state_outcome_stats(M1["states"], team1_wdl, N_STATES)
    M2_counts, M2_state_probs = per_state_outcome_stats(M2["states"], team2_wdl, N_STATES)

    # Pairwise grid and final probabilities
    pair_grid = pairwise_outcome_grid(M1_state_probs, M2_state_probs)
    final = matchup_probs(M1_next, M2_next, pair_grid)

    # State means (original scale)
    M1_state_means = invert_scaling(M1["means"], scaler_1, CORE_FEATURES)
    M2_state_means = invert_scaling(M2["means"], scaler_2, CORE_FEATURES)

    # -------- Print summary --------
    print("\n=== Per-team model summary ===")
    print(f"{team1_name} model: {M1['method']}")
    print(f"{team2_name} model: {M2['method']}")

    print("\n=== Current state posteriors ===")
    print(f"{team1_name} now:  {np.round(M1_now, 3)}")
    print(f"{team2_name} now:  {np.round(M2_now, 3)}")

    print("\n=== Next-match state distributions ===")
    print(f"{team1_name} next: {np.round(M1_next, 3)}")
    print(f"{team2_name} next: {np.round(M2_next, 3)}")

    print("\n=== Final matchup probabilities ===")
    print(final.to_string())

    # -------- Save outputs --------
    """
    with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as writer:
        pd.DataFrame({f"{team1_name}_state": M1["states"], "wdl": team1_wdl}) \
            .to_excel(writer, sheet_name=f"{team1_name}_states", index=False)
    
        pd.DataFrame({f"{team2_name}_state": M2["states"], "wdl": team2_wdl}) \
            .to_excel(writer, sheet_name=f"{team2_name}_states", index=False)
    
        M1_state_probs.reset_index().rename(columns={"index": f"{team1_name}_state"}) \
            .to_excel(writer, sheet_name=f"{team1_name}_state_WDL", index=False)
    
        M2_state_probs.reset_index().rename(columns={"index": f"{team2_name}_state"}) \
            .to_excel(writer, sheet_name=f"{team2_name}_state_WDL", index=False)
    
        M1_state_means.to_excel(writer, sheet_name=f"{team1_name}_state_means", index=False)
        M2_state_means.to_excel(writer, sheet_name=f"{team2_name}_state_means", index=False)
    
        pair_grid.to_excel(writer, sheet_name="Pair_grid", index=False)
    
        pd.DataFrame({
            "Team": [team1_name, team2_name],
            "Method": [M1["method"], M2["method"]],
            "Now_posterior": [list(np.round(M1_now, 4)), list(np.round(M2_now, 4))],
            "Next_state": [list(np.round(M1_next, 4)), list(np.round(M2_next, 4))],
        }).to_excel(writer, sheet_name="Posteriors", index=False)
    
        final.to_frame(name="Probability").reset_index().rename(columns={"index": "Outcome"}) \
             .to_excel(writer, sheet_name="Final_matchup_probs", index=False)
             
    print(f"\nSaved workbook to: {OUT_XLSX.resolve()}")
    """


if __name__ == "__main__":
    main()
