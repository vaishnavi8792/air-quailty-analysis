# Air Quality Analysis: Cleaning, Trends and Statistical Comparison of Pollution Across Zones and Seasons

**Name:** vaishnavi   **Course/Date:** 20/11/26
Live dashboard: https://air-quailty-analysis-2hbvqcckzoqdx3gy8supzw.streamlit.app/

## 1. Introduction
Cities publish large volumes of air-quality readings (PM2.5, PM10, NO2) that are noisy and incomplete. This project builds a pipeline that cleans multi-station sensor data, identifies pollution trends and seasonal patterns, and statistically tests whether pollution differs significantly between zones and seasons. Findings are presented in an interactive Streamlit dashboard.

## 2. Data
The data is the Kaggle dataset "Air Quality Data in India (2015-2020)" (CPCB source), file `city_day.csv`. It contains 29,531 daily records for 26 cities from 2015-01-01 to 2020-07-01. Raw missing values were 15.6% for PM2.5, 37.7% for PM10 and 12.1% for NO2 (Figure 1).

Because the data has no zones, cities were grouped by geographic region into four zones (North, South, East, West) using a lookup table in `pipeline.py`. Seasons were derived from the month: Winter (Dec-Feb), Summer (Mar-May), Monsoon (Jun-Sep), Post-monsoon (Oct-Nov).

## 3. Methodology
**Cleaning.** Dates were parsed and records sorted by city and date. 0 duplicate city-date rows were removed. 0 negative values were set to missing, 256 records where PM2.5 exceeded PM10 were treated as sensor errors and set to missing, and 0 extreme spikes (PM2.5 > 1000, PM10 > 2000, NO2 > 500 µg/m³) were removed. Gaps of up to 3 days were filled by time-based interpolation. Cities with more than 40% missing PM2.5 (Jorapokhar, Mumbai) were dropped. Outliers were flagged with the IQR rule per city (726 PM2.5 values) but kept, since high pollution episodes are real. The clean dataset has 26,353 rows across 24 cities.

**Trend and seasonality.** Monthly means per zone were plotted; seasonal-trend decomposition (STL) was applied to Delhi; pollutant correlations were computed; and a Kendall-tau trend test was run on the overall monthly mean PM2.5.

**Statistical tests.** A Shapiro-Wilk test on a sample of PM2.5 gave W=0.734, p<0.001, so the data is not normal. Non-parametric tests were therefore used: Kruskal-Wallis for differences across zones and across seasons, with Dunn's post-hoc test (Bonferroni-corrected) and epsilon-squared as effect size, at alpha = 0.05.

## 4. Results
**Trend.** Overall monthly PM2.5 shows a decreasing trend (Kendall tau = -0.33, p<0.001), which is statistically significant (Figure 2).  Monthly PM2.5 follows a repeating yearly cycle with a sharp peak every winter, and these peaks are lower in later years than in 2015-2016, which matches the downward trend. The East and North zones reach the highest levels (peaks of roughly 250-300 µg/m³ in the early years), while the South zone stays lowest.

**Zones.** Mean PM2.5 by zone: East 79.8, North 95.0, South 40.3, West 65.1 µg/m³ (Figure 4).

**Seasons.** Mean PM2.5 by season: Monsoon 39.2, Post-monsoon 93.0, Summer 57.0, Winter 101.0 µg/m³ (Figure 3). STL decomposition for Delhi separates the trend from a repeating annual cycle (Figure 6).

**Pollutant relationships.** See the correlation heatmap (Figure 5). PM2.5 and PM10 are strongly correlated (r =0.88), which is expected because both come from similar sources such as dust, vehicles and combustion. NO2 shows a  correlation with PM2.5 (r = 0.35) and PM10 (r = 0.50)

**Statistical tests.**

| Pollutant   | Factor   |       H |   p_value |   Effect_size_eps2 |
|:------------|:---------|--------:|----------:|-------------------:|
| PM2.5       | Zone     | 4261.86 |         0 |              0.176 |
| PM2.5       | Season   | 5898.19 |         0 |              0.244 |
| PM10        | Zone     | 3162.59 |         0 |              0.185 |
| PM10        | Season   | 2894.47 |         0 |              0.17  |
| NO2         | Zone     | 1640.37 |         0 |              0.066 |
| NO2         | Season   | 1831.27 |         0 |              0.074 |

- PM2.5 differs significantly across zones (H=4261.9, p<0.001, effect size 0.18, large); the median is highest in North (69.3) and lowest in South (35.4).
- PM2.5 differs significantly across seasons (H=5898.2, p<0.001, effect size 0.24, large); the median is highest in Winter (74.4) and lowest in Monsoon (31.7).
- PM10 differs significantly across zones (H=3162.6, p<0.001, effect size 0.19, large); the median is highest in North (140.5) and lowest in South (72.4).
- PM10 differs significantly across seasons (H=2894.5, p<0.001, effect size 0.17, large); the median is highest in Winter (128.6) and lowest in Monsoon (61.2).
- NO2 differs significantly across zones (H=1640.4, p<0.001, effect size 0.07, medium); the median is highest in West (41.4) and lowest in East (17.6).
- NO2 differs significantly across seasons (H=1831.3, p<0.001, effect size 0.07, medium); the median is highest in Winter (30.5) and lowest in Monsoon (17.5).

## 5. Conclusion
- Pollution levels differ significantly across zones and seasons. The worst zone is North (mean PM2.5 95.0 µg/m³) and the worst season is Winter (101.0 µg/m³); the best are South (40.3) and Monsoon (39.2).
- The overall PM2.5 trend is decreasing (statistically significant).
- **Limitations:** zones were assigned manually from city locations; gaps were interpolated; daily observations are autocorrelated, so p-values are likely optimistic.
- **Future work:** use station-level data with coordinates, add weather variables, and test with methods that account for time dependence.

## Figures
1. figures/01_missing_heatmap.png  2. figures/02_monthly_trend.png  3. figures/03_season_box.png  4. figures/04_zone_box.png  5. figures/05_correlation.png  6. figures/06_stl.png
