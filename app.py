import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import timedelta
import os

# -----------------------------
# Настройки страницы
# -----------------------------
st.set_page_config(layout="wide")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.markdown("## 📊 Прогнозы")

# -----------------------------
# Инструменты + кнопка загрузки
# -----------------------------
data_root = "data"
available_instruments = [
    d for d in os.listdir(data_root)
    if os.path.isdir(os.path.join(data_root, d))
]

col1, col2 = st.sidebar.columns([4, 1])

with col1:
    instrument = st.selectbox("Выберите инструмент:", available_instruments)

with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    load_clicked = st.button("🔄", help="Загрузить данные")

# -----------------------------
# Пути
# -----------------------------
instr_dir = os.path.join(data_root, instrument)
data_file = os.path.join(instr_dir, "data.csv")
pred_dir = os.path.join(instr_dir, "predictions")

# -----------------------------
# Загрузка данных
# -----------------------------
if load_clicked or "df" not in st.session_state or st.session_state.get("instrument") != instrument:
    try:
        df = pd.read_csv(data_file)

        if "<DATE>" in df.columns:
            df["date"] = pd.to_datetime(
                df["<DATE>"].astype(str) + " " + df["<TIME>"].astype(str) + ":00:00"
            )
        else:
            df["date"] = pd.to_datetime(df["date"])

        st.session_state.df = df
        st.session_state.instrument = instrument

    except FileNotFoundError:
        st.sidebar.error("Файл data.csv не найден!")
        st.stop()
else:
    df = st.session_state.df

# -----------------------------
# Даты
# -----------------------------
max_date = df["date"].max().date()
min_date = df["date"].min().date()
default_start = max_date - timedelta(days=150)

c1, c2 = st.sidebar.columns(2)
with c1:
    start_date = st.date_input("Начало", value=default_start, min_value=min_date, max_value=max_date)
with c2:
    end_date = st.date_input("Конец", value=max_date, min_value=min_date, max_value=max_date)

st.sidebar.markdown(
    "<hr style='margin:5px 0; border:1px solid #ddd;'>",
    unsafe_allow_html=True
)

# -----------------------------
# Прогнозы (нативный label)
# -----------------------------
prediction_dirs = []
if os.path.exists(pred_dir):
    prediction_dirs = [
        d for d in os.listdir(pred_dir)
        if os.path.isdir(os.path.join(pred_dir, d))
    ]

selected_preds = st.sidebar.multiselect(
    "Выберите прогнозы:",
    prediction_dirs
)

st.sidebar.markdown(
    "<hr style='margin:5px 0; border:1px solid #ddd;'>",
    unsafe_allow_html=True
)

# -----------------------------
# Скользящие средние (нативный label)
# -----------------------------
ma_options = [6, 12, 20, 30, 50, 100, 150, 200]

ma_periods = st.sidebar.multiselect(
    "Выберите периоды MA:",
    ma_options,
    default=[6]
)

# фиксированная палитра
ma_palette = [
    "#FF0000",
    "#00AAFF",
    "#00CC66",
    "#FF9900",
    "#AA00FF",
    "#00CCCC",
    "#FF66CC",
    "#999999"
]

ma_colors = {}
for i, period in enumerate(ma_periods):
    ma_colors[period] = ma_palette[i % len(ma_palette)]

# -----------------------------
# Фильтрация данных
# -----------------------------
filtered = df[
    (df["date"] >= pd.to_datetime(start_date)) &
    (df["date"] <= pd.to_datetime(end_date))
].copy()

# -----------------------------
# График
# -----------------------------
fig = go.Figure()

# Факт
fig.add_trace(
    go.Scatter(
        x=filtered["date"],
        y=filtered["<CLOSE>"],
        mode="lines",
        line=dict(width=2),
        name="Close"
    )
)

# Скользящие средние
for period in ma_periods:
    ma = filtered["<CLOSE>"].rolling(period).mean().shift(-period // 2)

    fig.add_trace(
        go.Scatter(
            x=filtered["date"],
            y=ma,
            mode="lines",
            line=dict(color=ma_colors[period], width=2),
            name=f"MA {period}"
        )
    )

# Прогнозы
descriptions = []

for pred in selected_preds:
    try:
        pred_path = os.path.join(pred_dir, pred, "data.csv")
        pred_df = pd.read_csv(pred_path)
        pred_df["date"] = pd.to_datetime(pred_df["date"])

        color = "#000000"

        fig.add_trace(
            go.Scatter(
                x=pred_df["date"],
                y=pred_df["prediction"],
                mode="lines",
                line=dict(dash="dash", width=2, color=color),
                name=pred
            )
        )

        # описание
        desc_file = os.path.join(pred_dir, pred, "description.txt")
        if os.path.exists(desc_file):
            with open(desc_file, "r", encoding="utf-8") as f:
                text = f.read()
                descriptions.append((pred, text, color))

    except Exception:
        st.sidebar.error(f"Ошибка в {pred}")

# -----------------------------
# Настройки графика
# -----------------------------
fig.update_layout(
    height=580,
    margin=dict(l=10, r=10, t=10, b=10),
    xaxis_title="Дата",
    yaxis=dict(title="Цена", side="right"),
    hovermode="x unified",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Описания прогнозов
# -----------------------------
for name, text, color in descriptions:
    st.markdown(
        f"<b style='color:{color}'>{name}</b><br>{text}",
        unsafe_allow_html=True
    )