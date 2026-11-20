"""Air-quality pipeline: clean -> aggregate -> trends -> stats tests -> report.md
Run from the project root:  python pipeline.py
Needs data/raw/city_day.csv (Kaggle: Air Quality Data in India 2015-2020).
"""
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

RAW = "data/raw/city_day.csv"
POLL = ["PM2.5", "PM10", "NO2"]
os.makedirs("data/clean", exist_ok=True)
os.makedirs("figures", exist_ok=True)

# ---- Zone lookup (assigned by geographic region; documented in report) ----
ZONES = {
    "North": ["Delhi", "Gurugram", "Chandigarh", "Amritsar", "Jaipur", "Lucknow"],
    "West": ["Ahmedabad", "Mumbai", "Bhopal"],
    "East": ["Kolkata", "Patna", "Guwahati", "Aizawl", "Shillong",
             "Brajrajnagar", "Jorapokhar", "Talcher"],
    "South": ["Bengaluru", "Chennai", "Coimbatore", "Ernakulam", "Hyderabad",
              "Kochi", "Thiruvananthapuram", "Visakhapatnam", "Amaravati"],
}
CITY2ZONE = {c: z for z, cs in ZONES.items() for c in cs}
SEASON = {12: "Winter", 1: "Winter", 2: "Winter", 3: "Summer", 4: "Summer",
          5: "Summer", 6: "Monsoon", 7: "Monsoon", 8: "Monsoon", 9: "Monsoon",
          10: "Post-monsoon", 11: "Post-monsoon"}
CAPS = {"PM2.5": 1000, "PM10": 2000, "NO2": 500}

notes = {}

# ---------------- 1. Load + inspect ----------------
raw = pd.read_csv(RAW)
_d = pd.to_datetime(raw["Date"], format="%d-%m-%Y", errors="coerce")
if _d.isna().mean() > 0.5:  # file uses another date format (e.g. 2015-01-01)
    _d = pd.to_datetime(raw["Date"], errors="coerce")
raw["Date"] = _d
print("[check] unparsed dates:", int(raw["Date"].isna().sum()), "of", len(raw))
df = raw[["City", "Date"] + POLL].copy()
notes["rows_raw"] = len(df)
notes["cities_raw"] = df["City"].nunique()
notes["date_min"] = df["Date"].min().date()
notes["date_max"] = df["Date"].max().date()
notes["missing_pct_raw"] = (df[POLL].isna().mean() * 100).round(1).to_dict()

miss_city = df.groupby("City")[POLL].apply(lambda x: x.isna().mean() * 100)
plt.figure(figsize=(6, 8))
sns.heatmap(miss_city, annot=True, fmt=".0f", cmap="Reds")
plt.title("Missing values (%) by city and pollutant (raw)")
plt.tight_layout()
plt.savefig("figures/01_missing_heatmap.png", dpi=150)
plt.close()

# ---------------- 2. Clean ----------------
df = df.dropna(subset=["Date"]).sort_values(["City", "Date"])
n = len(df)
df = df.drop_duplicates(subset=["City", "Date"])
notes["duplicates"] = n - len(df)

neg = (df[POLL] < 0).sum().sum()
df[POLL] = df[POLL].mask(df[POLL] < 0)
bad_ratio = df["PM2.5"] > df["PM10"]
notes["pm25_gt_pm10"] = int(bad_ratio.sum())
df.loc[bad_ratio, ["PM2.5", "PM10"]] = np.nan
spikes = 0
for c, cap in CAPS.items():
    m = df[c] > cap
    spikes += int(m.sum())
    df.loc[m, c] = np.nan
notes["negatives"] = int(neg)
notes["extreme_spikes"] = spikes

# fill short gaps (<=3 days) per city after reindexing to a full daily grid
frames = []
for city, g in df.groupby("City"):
    g = g.set_index("Date")[POLL].sort_index()
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="D"))
    for c in POLL:
        g[c] = g[c].interpolate(method="time", limit=3)
    g["City"] = city
    g.index.name = "Date"
    frames.append(g.reset_index())
clean = pd.concat(frames, ignore_index=True)
print("[check] rows after reindex/interpolate:", len(clean),
      "| non-missing PM2.5:", int(clean["PM2.5"].notna().sum()))

# drop cities with >40% missing PM2.5
miss = clean.groupby("City")["PM2.5"].apply(lambda x: x.isna().mean())
dropped = miss[miss > 0.40].index.tolist()
print("[check] cities dropped for >40% missing PM2.5:", dropped)
clean = clean[~clean["City"].isin(dropped)]
notes["cities_dropped"] = dropped

# outlier flag (IQR, per city) - flagged, not removed
def iqr_flag(s):
    q1, q3 = s.quantile([0.25, 0.75])
    i = q3 - q1
    return (s < q1 - 1.5 * i) | (s > q3 + 1.5 * i)

clean["PM2.5_outlier"] = clean.groupby("City")["PM2.5"].transform(iqr_flag)
notes["outliers_flagged"] = int(clean["PM2.5_outlier"].sum())

# zones + seasons
clean["Zone"] = clean["City"].map(CITY2ZONE)
print("[check] rows with no zone (dropped):", int(clean["Zone"].isna().sum()),
      "of", len(clean))
clean = clean.dropna(subset=["Zone"])
if clean.empty:
    raise SystemExit("No rows left after cleaning - send the [check] lines above.")
clean["Month"] = clean["Date"].dt.month
clean["Season"] = clean["Month"].map(SEASON)
clean.to_csv("data/clean/clean.csv", index=False)
notes["rows_clean"] = len(clean)
notes["cities_clean"] = clean["City"].nunique()
notes["missing_pct_clean"] = (clean[POLL].isna().mean() * 100).round(1).to_dict()

# ---------------- 3. Aggregate ----------------
monthly_zone = (clean.groupby(["Zone", pd.Grouper(key="Date", freq="MS")])[POLL]
                .mean().reset_index())
monthly_zone.to_csv("data/clean/monthly_zone.csv", index=False)

# ---------------- 4. Trends & seasonality ----------------
plt.figure(figsize=(10, 4))
sns.lineplot(data=monthly_zone, x="Date", y="PM2.5", hue="Zone")
plt.title("Monthly mean PM2.5 by zone")
plt.ylabel("PM2.5 (µg/m³)")
plt.tight_layout()
plt.savefig("figures/02_monthly_trend.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 4))
order = ["Winter", "Summer", "Monsoon", "Post-monsoon"]
sns.boxplot(data=clean, x="Season", y="PM2.5", order=order, showfliers=False)
plt.title("PM2.5 by season")
plt.tight_layout()
plt.savefig("figures/03_season_box.png", dpi=150)
plt.close()

plt.figure(figsize=(8, 4))
sns.boxplot(data=clean, x="Zone", y="PM2.5", showfliers=False)
plt.title("PM2.5 by zone")
plt.tight_layout()
plt.savefig("figures/04_zone_box.png", dpi=150)
plt.close()

plt.figure(figsize=(4.5, 4))
sns.heatmap(clean[POLL].corr(), annot=True, cmap="coolwarm", vmin=-1, vmax=1)
plt.title("Pollutant correlation")
plt.tight_layout()
plt.savefig("figures/05_correlation.png", dpi=150)
plt.close()

stl_city = clean.groupby("City")["PM2.5"].count().idxmax()
notes["stl_city"] = stl_city
try:
    from statsmodels.tsa.seasonal import STL
    s = (clean[clean["City"] == stl_city].set_index("Date")["PM2.5"]
         .resample("MS").mean().interpolate())
    STL(s, period=12).fit().plot()
    plt.suptitle(f"STL decomposition of monthly PM2.5 - {stl_city}")
    plt.tight_layout()
    plt.savefig("figures/06_stl.png", dpi=150)
    plt.close()
except ImportError:
    print("statsmodels not installed - skipping STL plot")

# Kendall-tau trend test on overall monthly mean PM2.5
overall = clean.set_index("Date")["PM2.5"].resample("MS").mean().dropna()
tau, p_tau = stats.kendalltau(np.arange(len(overall)), overall.values)
notes["trend_tau"], notes["trend_p"] = float(tau), float(p_tau)

# ---------------- 5. Statistical tests ----------------
# Shapiro-Wilk on a random sample (limit 5000)
samp = clean["PM2.5"].dropna().sample(min(5000, clean["PM2.5"].notna().sum()),
                                      random_state=1)
W, p_sh = stats.shapiro(samp)
notes["shapiro_W"], notes["shapiro_p"] = float(W), float(p_sh)


def dunn(d, val, grp):
    """Dunn's post-hoc test with tie correction and Bonferroni adjustment."""
    d = d[[val, grp]].dropna().copy()
    d["r"] = d[val].rank()
    N = len(d)
    _, c = np.unique(d[val], return_counts=True)
    tie = (c ** 3 - c).sum() / (12 * (N - 1))
    g = d.groupby(grp)["r"].agg(["mean", "count"])
    labs = list(g.index)
    m = len(labs) * (len(labs) - 1) / 2
    out = pd.DataFrame(1.0, index=labs, columns=labs)
    for i, a in enumerate(labs):
        for b in labs[i + 1:]:
            se = np.sqrt((N * (N + 1) / 12 - tie) *
                         (1 / g.loc[a, "count"] + 1 / g.loc[b, "count"]))
            z = (g.loc[a, "mean"] - g.loc[b, "mean"]) / se
            out.loc[a, b] = out.loc[b, a] = min(1.0, 2 * stats.norm.sf(abs(z)) * m)
    return out


def fmt_p(p):
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def eps_label(e):
    return "small" if e < 0.06 else "medium" if e < 0.14 else "large"


rows = []
for pol in POLL:
    for fac in ["Zone", "Season"]:
        d = clean[[pol, fac]].dropna()
        H, p = stats.kruskal(*[g[pol].values for _, g in d.groupby(fac)])
        N = len(d)
        eps = H * (N + 1) / (N ** 2 - 1)
        med = d.groupby(fac)[pol].median()
        if p < 0.05:
            msg = (f"{pol} differs significantly across {fac.lower()}s "
                   f"(H={H:.1f}, {fmt_p(p)}, effect size {eps:.2f}, {eps_label(eps)}); "
                   f"the median is highest in {med.idxmax()} ({med.max():.1f}) and "
                   f"lowest in {med.idxmin()} ({med.min():.1f}).")
        else:
            msg = (f"No significant difference in {pol} across {fac.lower()}s "
                   f"(H={H:.1f}, {fmt_p(p)}).")
        rows.append({"Pollutant": pol, "Factor": fac, "Test": "Kruskal-Wallis",
                     "H": round(H, 2), "p_value": p, "Effect_size_eps2": round(eps, 3),
                     "Significant": p < 0.05, "Interpretation": msg})
        dunn(d, pol, fac).to_csv(f"data/clean/dunn_{pol}_{fac}.csv")
results = pd.DataFrame(rows)
results.to_csv("data/clean/test_results.csv", index=False)

# ---------------- 6. Auto-filled report ----------------
zone_mean = clean.groupby("Zone")["PM2.5"].mean().round(1)
season_mean = clean.groupby("Season")["PM2.5"].mean().round(1)
trend_dir = "increasing" if tau > 0 else "decreasing"
trend_sig = "statistically significant" if p_tau < 0.05 else "not statistically significant"
tests_md = "\n".join(f"- {r.Interpretation}" for r in results.itertuples())
try:
    table_md = results[["Pollutant", "Factor", "H", "p_value",
                        "Effect_size_eps2"]].round(4).to_markdown(index=False)
except ImportError:
    table_md = results[["Pollutant", "Factor", "H", "p_value",
                        "Effect_size_eps2"]].round(4).to_string(index=False)

report = f"""# Air Quality Analysis: Cleaning, Trends and Statistical Comparison of Pollution Across Zones and Seasons

**Name:** [ADD YOUR NAME]   **Course/Date:** [ADD]

## 1. Introduction
Cities publish large volumes of air-quality readings (PM2.5, PM10, NO2) that are noisy and incomplete. This project builds a pipeline that cleans multi-station sensor data, identifies pollution trends and seasonal patterns, and statistically tests whether pollution differs significantly between zones and seasons. Findings are presented in an interactive Streamlit dashboard.

## 2. Data
The data is the Kaggle dataset "Air Quality Data in India (2015-2020)" (CPCB source), file `city_day.csv`. It contains {notes['rows_raw']:,} daily records for {notes['cities_raw']} cities from {notes['date_min']} to {notes['date_max']}. Raw missing values were {notes['missing_pct_raw']['PM2.5']}% for PM2.5, {notes['missing_pct_raw']['PM10']}% for PM10 and {notes['missing_pct_raw']['NO2']}% for NO2 (Figure 1).

Because the data has no zones, cities were grouped by geographic region into four zones (North, South, East, West) using a lookup table in `pipeline.py`. Seasons were derived from the month: Winter (Dec-Feb), Summer (Mar-May), Monsoon (Jun-Sep), Post-monsoon (Oct-Nov).

## 3. Methodology
**Cleaning.** Dates were parsed and records sorted by city and date. {notes['duplicates']} duplicate city-date rows were removed. {notes['negatives']} negative values were set to missing, {notes['pm25_gt_pm10']} records where PM2.5 exceeded PM10 were treated as sensor errors and set to missing, and {notes['extreme_spikes']} extreme spikes (PM2.5 > 1000, PM10 > 2000, NO2 > 500 µg/m³) were removed. Gaps of up to 3 days were filled by time-based interpolation. Cities with more than 40% missing PM2.5 ({', '.join(notes['cities_dropped']) if notes['cities_dropped'] else 'none'}) were dropped. Outliers were flagged with the IQR rule per city ({notes['outliers_flagged']} PM2.5 values) but kept, since high pollution episodes are real. The clean dataset has {notes['rows_clean']:,} rows across {notes['cities_clean']} cities.

**Trend and seasonality.** Monthly means per zone were plotted; seasonal-trend decomposition (STL) was applied to {notes['stl_city']}; pollutant correlations were computed; and a Kendall-tau trend test was run on the overall monthly mean PM2.5.

**Statistical tests.** A Shapiro-Wilk test on a sample of PM2.5 gave W={notes['shapiro_W']:.3f}, {fmt_p(notes['shapiro_p'])}, so the data is not normal. Non-parametric tests were therefore used: Kruskal-Wallis for differences across zones and across seasons, with Dunn's post-hoc test (Bonferroni-corrected) and epsilon-squared as effect size, at alpha = 0.05.

## 4. Results
**Trend.** Overall monthly PM2.5 shows a {trend_dir} trend (Kendall tau = {notes['trend_tau']:.2f}, {fmt_p(notes['trend_p'])}), which is {trend_sig} (Figure 2). [ADD 1-2 sentences describing what you see in the figure.]

**Zones.** Mean PM2.5 by zone: {', '.join(f'{k} {v}' for k, v in zone_mean.items())} µg/m³ (Figure 4).

**Seasons.** Mean PM2.5 by season: {', '.join(f'{k} {v}' for k, v in season_mean.items())} µg/m³ (Figure 3). STL decomposition for {notes['stl_city']} separates the trend from a repeating annual cycle (Figure 6).

**Pollutant relationships.** See the correlation heatmap (Figure 5). [ADD: which pollutants are strongly correlated.]

**Statistical tests.**

{table_md}

{tests_md}

## 5. Conclusion
- Pollution levels differ across zones and seasons as shown by the tests above. [ADD: name the worst zone and season from the results.]
- The overall PM2.5 trend is {trend_dir} ({trend_sig}).
- **Limitations:** zones were assigned manually from city locations; gaps were interpolated; daily observations are autocorrelated, so p-values are likely optimistic.
- **Future work:** use station-level data with coordinates, add weather variables, and test with methods that account for time dependence.

## Figures
1. figures/01_missing_heatmap.png  2. figures/02_monthly_trend.png  3. figures/03_season_box.png  4. figures/04_zone_box.png  5. figures/05_correlation.png  6. figures/06_stl.png
"""
with open("report.md", "w", encoding="utf-8") as f:
    f.write(report)
print("Done. See report.md, figures/, data/clean/")