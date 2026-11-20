# Air Quality Analysis

Pipeline that cleans multi-station air-quality data, finds trends and seasonal patterns, tests zone/season differences, and shows a Streamlit dashboard.

## Run
1. `pip install -r requirements.txt`
2. Download Kaggle "Air Quality Data in India (2015-2020)" and put `city_day.csv` in `data/raw/`
3. `python pipeline.py`  (creates `data/clean/`, `figures/`, `report.md`)
4. `streamlit run app/app.py`

## Findings
- North has the highest PM2.5 (mean 95.0 µg/m³) and South the lowest (40.3).
- Winter is the worst season (101.0) and monsoon the best (39.2).
- Differences across zones and seasons are statistically significant (Kruskal-Wallis, p < 0.001).
- Overall PM2.5 shows a significant decreasing trend from 2015 to 2020.
- Live dashboard:https://air-quailty-analysis-2hbvqcckzoqdx3gy8supzw.streamlit.app/
