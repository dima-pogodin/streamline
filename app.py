import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
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
non_trading_file = os.path.join(instr_dir, "non_trading_days.csv")

# -----------------------------
# Загрузка данных
# -----------------------------
if (
    load_clicked
    or "df" not in st.session_state
    or st.session_state.get("instrument") != instrument
):
    try:
        df = pd.read_csv(data_file)

        df.columns = [c.replace("<", "").replace(">", "") for c in df.columns]

        df.rename(columns={
            "DATE": "date",
            "TIME": "time",
            "OPEN": "open",
            "HIGH": "high",
            "LOW": "low",
            "CLOSE": "close",
            "VOL": "volume",
        }, inplace=True)

        raw_datetime = df["date"].astype(str) + " " + df["time"].astype(str)

        # первая попытка
        parsed = pd.to_datetime(
            raw_datetime,
            format="%Y-%m-%d %H%M%S",
            errors="coerce",
        )

        # альтернатива
        if parsed.isna().all():
            parsed = pd.to_datetime(
                df["date"].astype(str)
                + " "
                + df["time"].astype(str)
                + ":00:00",
                errors="coerce",
            )
        
        df["datetime"] = parsed
        df = df.dropna(subset=["datetime"])
        df = df.sort_values("datetime")

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
max_date = df["datetime"].max().date()
min_date = df["datetime"].min().date()
default_start = max_date - timedelta(hours=500)

c1, c2 = st.sidebar.columns(2)

with c1:
    start_date = st.date_input(
        "Начало",
        value=default_start,
        min_value=min_date,
        max_value=max_date,
    )

with c2:
    end_date = st.date_input(
        "Конец",
        value=max_date,
        min_value=min_date,
        max_value=max_date,
    )

st.sidebar.markdown(
    "<hr style='margin:5px 0; border:1px solid #ddd;'>",
    unsafe_allow_html=True,
)

# -----------------------------
# Прогнозы
# -----------------------------
prediction_dirs = []

if os.path.exists(pred_dir):
    prediction_dirs = [
        d for d in os.listdir(pred_dir)
        if os.path.isdir(os.path.join(pred_dir, d))
    ]

selected_preds = st.sidebar.multiselect(
    "Выберите прогнозы:",
    prediction_dirs,
)

st.sidebar.markdown(
    "<hr style='margin:5px 0; border:1px solid #ddd;'>",
    unsafe_allow_html=True,
)

# -----------------------------
# Скользящие средние
# -----------------------------
ma_options = [6, 12, 20, 30, 50, 100, 150, 200]

ma_periods = st.sidebar.multiselect(
    "Выберите периоды MA:",
    ma_options,
    default=[6],
)

ma_palette = [
    "#FF0000",
    "#00AAFF",
    "#00CC66",
    "#FF9900",
    "#AA00FF",
    "#00CCCC",
    "#FF66CC",
    "#999999",
]

ma_colors = {}

for i, period in enumerate(ma_periods):
    ma_colors[period] = ma_palette[i % len(ma_palette)]

# -----------------------------
# Фильтрация данных
# -----------------------------
filtered = df[
    (df["datetime"] >= pd.to_datetime(start_date))
    & (df["datetime"] <= pd.to_datetime(end_date))
].copy()

filtered = filtered.sort_values("datetime")

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    row_heights=[0.75, 0.25],
    vertical_spacing=0.02
)

fig.update_xaxes(rangeslider_visible=False)

# Свечи
fig.add_trace(
    go.Candlestick(
        x=filtered["datetime"],
        open=filtered["open"],
        high=filtered["high"],
        low=filtered["low"],
        close=filtered["close"],
        name="Цена"
    ),
    row=1, col=1
)

# Объём
fig.add_trace(
    go.Bar(
        x=filtered["datetime"],
        y=filtered["volume"],
        name="Объём"
    ),
    row=2, col=1
)

# MA
for period in ma_periods:
    ma = filtered["close"].rolling(period).mean().shift(-period // 2)

    fig.add_trace(
        go.Scatter(
            x=filtered["datetime"],
            y=ma,
            mode="lines",
            line=dict(color=ma_colors[period], width=2),
            name=f"MA {period}"
        ),
        row=1, col=1
    )

# -----------------------------
# Прогнозы
# -----------------------------
descriptions = []

for pred in selected_preds:
    try:
        pred_path = os.path.join(pred_dir, pred, "data.csv")
        pred_df = pd.read_csv(pred_path)
        pred_df["datetime"] = pd.to_datetime(pred_df["datetime"])

        color = "#000000"

        fig.add_trace(
            go.Scatter(
                x=pred_df["datetime"],
                y=pred_df["prediction"],
                mode="lines",
                line=dict(dash="dash", width=2, color=color),
                name=pred,
            ),
            row=1, col=1
        )

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
    showlegend=False,
)

# -----------------------------
# Rangebreaks (старый вариант)
# -----------------------------
all_days = pd.date_range(
    df["datetime"].min().date(),
    df["datetime"].max().date(),
)

existing_days = df["datetime"].dt.normalize().unique()

missing_days = [
    pd.Timestamp(d) for d in all_days if d not in existing_days
]

# пример: скрыть конкретные даты и часы
skip_times = [
    "2025-12-27 07:00:00",
    "2025-12-27 08:00:00",
    "2025-12-27 19:00:00",
    "2025-12-27 20:00:00",
    "2025-12-27 21:00:00",
    "2025-12-27 22:00:00",
    "2025-12-27 23:00:00",
    "2025-12-28 07:00:00",
    "2025-12-28 08:00:00"
]

# можно конвертировать в pd.Timestamp
skip_times = [pd.Timestamp(t) for t in skip_times]

fig.update_xaxes(
    type="date",
    rangebreaks=[
        dict(values=missing_days),
        dict(values=skip_times),
        dict(bounds=[24, 24], pattern="hour"),
        dict(bounds=[0, 6.9999], pattern="hour"),
    ],
)

# Центрированный заголовок
st.markdown(
    f"<h2 style='text-align:center'>{instrument}</h2>",
    unsafe_allow_html=True
)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# Описания
# -----------------------------
for name, text, color in descriptions:
    st.markdown(
        f"<b style='color:{color}'>{name}</b><br>{text}",
        unsafe_allow_html=True,
    )