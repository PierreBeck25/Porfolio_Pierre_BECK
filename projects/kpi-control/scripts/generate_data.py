import numpy as np, pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)

N_JOBS = 35
N_APPLIS = 600

job_families = ["Sales", "Support", "Tech", "Ops", "Marketing"]
recruiters = ["Alice", "Bruno", "Chloé", "Diego"]
sources = ["LinkedIn", "Jobboard A", "Cooptation", "Candidature Spontanée", "Agence"]
source_cost_map = {"LinkedIn": 9, "Jobboard A": 6, "Cooptation": 2, "Candidature Spontanée": 0, "Agence": 18}

def random_dates(start="2024-01-01", end="2025-09-01", n=1):
    s = pd.to_datetime(start); e = pd.to_datetime(end)
    return s + pd.to_timedelta(rng.integers(0, (e-s).days, size=n), unit="D")

jobs = pd.DataFrame({
    "job_id": range(1, N_JOBS+1),
    "job_family": rng.choice(job_families, N_JOBS, p=[.22,.18,.26,.18,.16])
})

applied = random_dates(n=N_APPLIS)
job_ids = rng.choice(jobs["job_id"], N_APPLIS)
df = pd.DataFrame({
    "application_id": range(1, N_APPLIS+1),
    "candidate_id": rng.integers(10000, 99999, N_APPLIS),
    "job_id": job_ids,
    "recruiter": rng.choice(recruiters, N_APPLIS),
    "source": rng.choice(sources, N_APPLIS, p=[.45,.20,.15,.15,.05]),
    "applied_at": applied
}).merge(jobs, on="job_id", how="left")

df["source_cost"] = df["source"].map(source_cost_map)

family_factor = df["job_family"].map({"Tech": .8, "Sales": .75, "Ops": .7, "Support": .7, "Marketing": .72})
p_screen = .65 * family_factor
p_interview = .55 * family_factor
p_offer = .35 * family_factor
p_hire = .25 * family_factor

def advance_dates(base, min_d, max_d, p):
    base = pd.to_datetime(base)
    mask = rng.random(len(base)) < p
    out = pd.Series(pd.NaT, index=base.index)
    deltas = rng.integers(min_d, max_d+1, mask.sum())
    out.loc[mask] = base.loc[mask] + pd.to_timedelta(deltas, unit="D")
    return pd.to_datetime(out)

df["screened_at"]    = advance_dates(df["applied_at"], 1, 6, p_screen)
df["interviewed_at"] = advance_dates(df["screened_at"].fillna(df["applied_at"]), 2, 10, p_interview)
df["offered_at"]     = advance_dates(df["interviewed_at"].fillna(df["applied_at"]), 3, 14, p_offer)
df["hired_at"]       = advance_dates(df["offered_at"].fillna(df["applied_at"]), 1, 10, p_hire)

df["sla_screen_72h"] = ((df["screened_at"] - df["applied_at"]).dt.days <= 3).fillna(False).astype(int)
df["sla_offer_7d"]   = ((df["offered_at"] - df["interviewed_at"]).dt.days <= 7).fillna(False).astype(int)

df["offer_accepted"] = (~df["offered_at"].isna() & ~df["hired_at"].isna()).astype(int)
df["probation_success_90d"] = ((rng.random(len(df)) < .85) & ~df["hired_at"].isna()).astype(int)

def outcome(row):
    if pd.notna(row.hired_at): return "Hired"
    if pd.notna(row.offered_at): return "Offer not accepted"
    if pd.notna(row.interviewed_at): return "Post-interview reject"
    if pd.notna(row.screened_at): return "Post-screen reject"
    return "Rejected/No-show"
df["stage_outcome"] = df.apply(outcome, axis=1)

out = Path(__file__).resolve().parents[1] / "data" / "raw" / "applications.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False)
print(f"OK: {out}")
