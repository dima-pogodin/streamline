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
# Sidebar: заголовок
# -----------------------------
st.sidebar.markdown("# 📈 Multi-Asset Dashboard")
st.sidebar.markdown("### Выберите инструмент и настройки")

# -----------------------------
# Выбор инструмента
# -----------------------------
data_root = "data"
available_instruments = [
    d for d in os.listdir(data_root)
    if os.path.isdir(os.path.join(data_root, d))
]

instrument = st.sidebar.selectbox("Выберите инструмент:", available_instruments)

# -----------------------------
# Пути для выбранного инструмента
# -----------------------------
instr_dir = os.path.join(data_root, instrument)
data_file = os.path.join(instr_dir, "data.csv")
pred_dir = os.path.join(instr_dir, "predictions")

# -----------------------------
# Кнопки: объединение и загрузка данных
# -----------------------------
col1, col2 = st.sidebar.columns(2)
with col1:
    combine_clicked = st.button("🔄 Объединить данные")
with col2:
    load_clicked = st.button("📥 Загрузить данные")

# -----------------------------
# Объединение
# -----------------------------
if combine_clicked:
    try:
        combine_data()  # объединяет файлы в data_file
        st.sidebar.success("Данные объединены")
    except Exception as e:
        st.sidebar.error(f"Ошибка объединения: {e}")

# -----------------------------
# Загрузка данных
# -----------------------------
if load_clicked or "df" not in st.session_state or st.session_state.get("instrument") != instrument:
    try:
        df = pd.read_csv(data_file, encoding="utf-8-sig")
        if "<DATE>" in df.columns:
            df["date"] = pd.to_datetime(
                df["<DATE>"].astype(str) + " " + df["<TIME>"].astype(str) + ":00:00"
            )
        elif "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
        else:
            st.sidebar.error("Нет колонки с датой!")
            st.stop()

        st.session_state.df = df
        st.session_state.instrument = instrument
        st.sidebar.success("Данные загружены")
    except FileNotFoundError:
        st.sidebar.error("Файл data.csv не найден!")
        st.stop()
else:
    df = st.session_state.df

# -----------------------------
# Диапазон дат (по умолчанию последние 150 дней)
# -----------------------------
max_date = df["date"].max().date()
min_date = df["date"].min().date()
default_start_date = max_date - timedelta(days=150)

st.sidebar.markdown("### Период")
col1, col2 = st.sidebar.columns(2)
with col1:
    start_date = st.date_input("Начало", value=default_start_date, min_value=min_date, max_value=max_date)
with col2:
    end_date = st.date_input("Конец", value=max_date, min_value=min_date, max_value=max_date)

st.sidebar.markdown("---")

# -----------------------------
# Скользящие средние
# -----------------------------
st.sidebar.header("Moving Averages")
ma_periods = st.sidebar.multiselect(
    "Периоды MA",
    options=[5, 10, 20, 30, 50, 100, 150, 200],
    default=[20, 50]
)

ma_colors = {}
for period in ma_periods:
    ma_colors[period] = st.sidebar.color_picker(f"Цвет MA {period}", "#FF0000")

st.sidebar.markdown("---")

# -----------------------------
# Прогнозы
# -----------------------------
st.sidebar.header("Прогнозы")
prediction_files = []
if os.path.exists(pred_dir):
    prediction_files = [f for f in os.listdir(pred_dir) if f.endswith(".csv")]

selected_preds = st.sidebar.multiselect("Выберите прогнозы", prediction_files)

pred_colors = {}
for file in selected_preds:
    pred_colors[file] = st.sidebar.color_picker(f"Цвет {file}", "#00FF00")

# -----------------------------
# Фильтрация данных по датам
# -----------------------------
filtered = df[
    (df["date"] >= pd.to_datetime(start_date)) &
    (df["date"] <= pd.to_datetime(end_date))
].copy()

# -----------------------------
# Построение графика
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
    ma = filtered["<CLOSE>"].rolling(period).mean()
    ma = ma.shift(-period // 2)
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
for file in selected_preds:
    try:
        pred_path = os.path.join(pred_dir, file)
        pred_df = pd.read_csv(pred_path)
        pred_df["date"] = pd.to_datetime(pred_df["date"])

        fig.add_trace(
            go.Scatter(
                x=pred_df["date"],
                y=pred_df["prediction"],
                mode="lines",
                line=dict(dash="dash", width=2, color=pred_colors[file]),
                name=file
            )
        )
    except Exception:
        st.sidebar.error(f"Ошибка в {file}")

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
