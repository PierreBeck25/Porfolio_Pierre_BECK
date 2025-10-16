import pandas as pd, numpy as np, plotly.express as px
from pathlib import Path

root = Path(__file__).resolve().parents[1]
csv = root / "data" / "raw" / "applications.csv"
df = pd.read_csv(csv, parse_dates=["applied_at","screened_at","interviewed_at","offered_at","hired_at"])

apply = len(df)
screen = df["screened_at"].notna().sum()
interview = df["interviewed_at"].notna().sum()
offer = df["offered_at"].notna().sum()
hire = df["hired_at"].notna().sum()

f_offered = df[df["offered_at"].notna()]
f_hired   = df[df["hired_at"].notna()].copy()
f_hired["TTH"] = (f_hired["hired_at"] - f_hired["applied_at"]).dt.days

kpis = {
    "Candidatures": apply,
    "Hires": hire,
    "Offer acceptance (%)": round(100*len(f_hired)/len(f_offered),1) if len(f_offered) else 0.0,
    "TTH médiane (j)": int(np.nanmedian(f_hired["TTH"])) if len(f_hired) else None,
    "TTH P90 (j)": int(np.nanpercentile(f_hired["TTH"], 90)) if len(f_hired) else None,
    "SLA screen 72h (%)": round(100*df["sla_screen_72h"].mean(),1) if "sla_screen_72h" in df else None,
}

funnel_counts = pd.DataFrame({
    "Étape": ["Apply","Screen","Interview","Offer","Hire"],
    "Volume": [apply,screen,interview,offer,hire]
})
fig_funnel = px.funnel(funnel_counts, x="Volume", y="Étape", title="Funnel Apply → Hire")

if not f_hired.empty:
    fig_tth = px.box(f_hired, x="job_family", y="TTH", points="suspectedoutliers",
                     title="Time-to-Hire par famille de poste")
else:
    fig_tth = px.box(pd.DataFrame({"job_family":[],"TTH":[]}), x="job_family", y="TTH", title="Time-to-Hire par famille de poste")

if "recruiter" in df.columns:
    sla = df.groupby("recruiter")["sla_screen_72h"].mean().mul(100).reset_index(name="% SLA 72h")
    fig_sla = px.bar(sla, x="recruiter", y="% SLA 72h", title="Respect SLA — Screen < 72h", text="% SLA 72h")
else:
    fig_sla = px.bar(pd.DataFrame({"recruiter":[],"% SLA 72h":[]}), x="recruiter", y="% SLA 72h", title="Respect SLA — Screen < 72h")

if "recruiter" in df.columns:
    prod = f_hired.groupby("recruiter")["application_id"].count().reset_index(name="Hires")
    fig_prod = px.bar(prod, x="recruiter", y="Hires", title="Hires par recruteur", text="Hires")
else:
    fig_prod = px.bar(pd.DataFrame({"recruiter":[],"Hires":[]}), x="recruiter", y="Hires", title="Hires par recruteur")

mix = df["source"].value_counts(normalize=True).mul(100).reset_index()
mix.columns = ["source","%"]
fig_mix = px.pie(mix, names="source", values="%", title="Mix des sources")

cards = "".join([f"<div class='card'><div class='kpi'>{v if v is not None else '—'}</div><div class='label'>{k}</div></div>" for k,v in kpis.items()])

html = f"""
<html>
<head>
<meta charset="utf-8"/>
<title>Tour de contrôle Recrutement</title>
<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
<style>
  body {{ font-family: Inter, system-ui, -apple-system, Segoe UI; margin: 0; background:#0b1220; color:#eef2ff; }}
  .wrap {{ max-width:1200px; margin: 24px auto; padding: 0 16px; }}
  h1 {{ font-size: 28px; margin: 8px 0 16px; }}
  .kpis {{ display:grid; grid-template-columns: repeat(6, 1fr); gap:12px; }}
  .card {{ background:#111827; border:1px solid #1f2937; border-radius:12px; padding:16px; text-align:center; }}
  .kpi {{ font-size: 22px; font-weight: 800; }}
  .label {{ font-size: 12px; color:#9ca3af; margin-top:4px; }}
  .grid {{ display:grid; grid-template-columns: 1fr 1fr; gap:16px; margin-top:16px; }}
  .full {{ grid-column: 1/-1; }}
  .box {{ background:#0f172a; border:1px solid #1f2937; border-radius:12px; padding:12px; }}
  @media (max-width: 900px) {{
    .kpis {{ grid-template-columns: repeat(2, 1fr); }}
    .grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>
  <div class="wrap">
    <h1>Tour de contrôle Recrutement</h1>
    <div class="kpis">{cards}</div>
    <div class="grid">
      <div class="box" id="funnel"></div>
      <div class="box" id="mix"></div>
      <div class="box full" id="tth"></div>
      <div class="box" id="sla"></div>
      <div class="box" id="prod"></div>
    </div>
  </div>
<script>
  var funnel = {fig_funnel.to_json()};
  Plotly.newPlot('funnel', funnel.data, funnel.layout);

  var mix = {fig_mix.to_json()};
  Plotly.newPlot('mix', mix.data, mix.layout);

  var tth = {fig_tth.to_json()};
  Plotly.newPlot('tth', tth.data, tth.layout);

  var sla = {fig_sla.to_json()};
  Plotly.newPlot('sla', sla.data, sla.layout);

  var prod = {fig_prod.to_json()};
  Plotly.newPlot('prod', prod.data, prod.layout);
</script>
</body>
</html>
"""

out = root.parents[1] / "docs" / "projects" / "kpi-control" / "index.html"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(html, encoding="utf-8")
print("Dashboard écrit:", out)
