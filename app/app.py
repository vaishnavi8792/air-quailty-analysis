import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Air Quality Dashboard", layout="wide")
POLL = ["PM2.5", "PM10", "NO2"]


@st.cache_data
def load():
    df = pd.read_csv("data/clean/clean.csv", parse_dates=["Date"])
    res = pd.read_csv("data/clean/test_results.csv")
    return df, res


df, res = load()
st.title("Air Quality: Trends, Seasons and Zone Comparison")

st.sidebar.header("Filters")
zones = st.sidebar.multiselect("Zone", sorted(df["Zone"].unique()), default=sorted(df["Zone"].unique()))
cities = st.sidebar.multiselect("City", sorted(df[df["Zone"].isin(zones)]["City"].unique()))
pol = st.sidebar.selectbox("Pollutant", POLL)
seasons = st.sidebar.multiselect("Season", ["Winter", "Summer", "Monsoon", "Post-monsoon"],
                                 default=["Winter", "Summer", "Monsoon", "Post-monsoon"])
dmin, dmax = df["Date"].min().date(), df["Date"].max().date()
dr = st.sidebar.date_input("Date range", (dmin, dmax), min_value=dmin, max_value=dmax)

f = df[df["Zone"].isin(zones) & df["Season"].isin(seasons)]
if cities:
    f = f[f["City"].isin(cities)]
if len(dr) == 2:
    f = f[(f["Date"].dt.date >= dr[0]) & (f["Date"].dt.date <= dr[1])]

c1, c2, c3 = st.columns(3)
c1.metric(f"Mean {pol}", f"{f[pol].mean():.1f} µg/m³")
c2.metric("Max (daily)", f"{f[pol].max():.1f}")
c3.metric("Cities / days", f"{f['City'].nunique()} / {f['Date'].nunique()}")

monthly = f.groupby(["Zone", pd.Grouper(key="Date", freq="MS")])[pol].mean().reset_index()
st.plotly_chart(px.line(monthly, x="Date", y=pol, color="Zone", title=f"Monthly mean {pol} by zone"),
                use_container_width=True)

a, b = st.columns(2)
a.plotly_chart(px.box(f, x="Season", y=pol, color="Season", title="Seasonal distribution",
                      category_orders={"Season": ["Winter", "Summer", "Monsoon", "Post-monsoon"]}),
               use_container_width=True)
zb = f.groupby("Zone")[pol].mean().reset_index()
b.plotly_chart(px.bar(zb, x="Zone", y=pol, color="Zone", title="Mean by zone"),
               use_container_width=True)

st.plotly_chart(px.imshow(f[POLL].corr(), text_auto=".2f", zmin=-1, zmax=1,
                          color_continuous_scale="RdBu_r", title="Pollutant correlation"),
                use_container_width=True)

st.subheader("Statistical test results (Kruskal-Wallis, alpha = 0.05)")
st.dataframe(res[["Pollutant", "Factor", "Test", "H", "p_value", "Effect_size_eps2",
                  "Significant", "Interpretation"]], use_container_width=True)
