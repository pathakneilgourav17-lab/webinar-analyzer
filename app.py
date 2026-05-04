import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Webinar Analyzer PRO+", layout="wide")
st.title("🚀 Webinar Analyzer PRO+")

file = st.file_uploader(
    "Upload File",
    type=["xlsx", "xls", "csv", "tsv", "txt"]
)

# ==============================
# HEADER DETECTION (SMART)
# ==============================
def find_header_row(df):
    keywords = ['email', 'mail', 'name', 'join', 'time', 'duration']

    for i in range(len(df)):
        row = df.iloc[i].astype(str).str.lower()
        match_count = sum(any(k in cell for k in keywords) for cell in row)

        if match_count >= 2:
            return i

    return None


# ==============================
# SMART FILE READER
# ==============================
def read_file(file, header=None):
    try:
        df = pd.read_csv(
            file,
            header=header,
            sep=None,
            engine="python",
            encoding="utf-8",
            on_bad_lines="skip"
        )
        return df

    except Exception:
        file.seek(0)
        try:
            return pd.read_excel(file, header=header)
        except Exception:
            return None


# ==============================
# 🔥 AUTO COLUMN DETECTION
# ==============================
def auto_map_columns(df):
    col_map = {}

    for col in df.columns:
        c = col.lower()

        if any(k in c for k in ['email', 'mail']):
            col_map[col] = 'email'

        elif any(k in c for k in ['name', 'user']):
            col_map[col] = 'name'

        elif any(k in c for k in ['join', 'login', 'start']):
            col_map[col] = 'join_time'

        elif any(k in c for k in ['leave', 'logout', 'end']):
            col_map[col] = 'leave_time'

        elif any(k in c for k in ['duration', 'time', 'minutes']):
            col_map[col] = 'session_time'

    return col_map


# ==============================
# MAIN LOGIC
# ==============================
if file:

    raw_df = read_file(file, header=None)

    if raw_df is None or raw_df.empty:
        st.error("❌ File could not be parsed")
        st.stop()

    header_row = find_header_row(raw_df)

    if header_row is None:
        header_row = 0
        st.warning("⚠️ Header not detected, using first row")

    file.seek(0)

    df = read_file(file, header=header_row)

    if df is None or df.empty:
        st.error("❌ File parsing failed")
        st.stop()

    # ==============================
    # CLEANING
    # ==============================
    df = df.dropna(how='all')
    df.columns = df.columns.astype(str).str.lower().str.strip()

    # 🔥 AUTO MAP COLUMNS
    col_map = auto_map_columns(df)
    df.rename(columns=col_map, inplace=True)

    st.sidebar.write("🔍 Detected Columns:", col_map)

    # ==============================
    # EMAIL FALLBACK
    # ==============================
    if 'email' not in df.columns:
        for col in df.columns:
            if df[col].astype(str).str.contains('@').any():
                df.rename(columns={col: 'email'}, inplace=True)
                break

    if 'email' not in df.columns:
        df['email'] = df.index.astype(str)
        st.warning("⚠️ Email not found, using row index as identifier")

    df = df[df['email'].notna()]
    df = df[df['email'].astype(str).str.len() > 0]

    # ==============================
    # TIME HANDLING
    # ==============================
    if 'join_time' in df.columns:
        df['join_time'] = pd.to_datetime(df['join_time'], errors='coerce')

    if 'leave_time' in df.columns:
        df['leave_time'] = pd.to_datetime(df['leave_time'], errors='coerce')

    if 'session_time' not in df.columns or df['session_time'].isna().all():
        if 'join_time' in df.columns and 'leave_time' in df.columns:
            df['session_time'] = (
                (df['leave_time'] - df['join_time'])
                .dt.total_seconds() / 60
            )

    if 'session_time' not in df.columns:
        df['session_time'] = 0

    df['hour'] = df['join_time'].dt.hour if 'join_time' in df.columns else 0
    df['date'] = df['join_time'].dt.date if 'join_time' in df.columns else None

    # ==============================
    # USER LEVEL AGG
    # ==============================
    user_df = df.groupby('email').agg({
        'name': 'first' if 'name' in df.columns else 'count',
        'session_time': 'sum',
        'join_time': 'count' if 'join_time' in df.columns else 'size'
    }).reset_index()

    user_df.rename(columns={
        'session_time': 'total_time',
        'join_time': 'join_count'
    }, inplace=True)

    # ==============================
    # METRICS
    # ==============================
    unique_users = df['email'].nunique()
    total_joins = len(df)
    avg_time = df['session_time'].mean()

    engaged_users = user_df[user_df['total_time'] > 50]
    engagement_rate = (len(engaged_users) / len(user_df)) * 100 if len(user_df) > 0 else 0

    peak_hour = df['hour'].mode()[0] if not df['hour'].mode().empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Users", unique_users)
    col2.metric("🔁 Joins", total_joins)
    col3.metric("⏱ Avg Time", round(avg_time, 1) if pd.notna(avg_time) else 0)
    col4.metric("🔥 Engagement %", f"{round(engagement_rate,1)}%")

    st.info(f"⏰ Peak Join Time: {peak_hour}:00 hrs")

    # ==============================
    # FILTERS
    # ==============================
    st.sidebar.header("Filters")

    min_time = st.sidebar.slider("Min Session Time", 0, 200, 0)
    selected_hour = st.sidebar.multiselect(
        "Filter by Hour",
        sorted(df['hour'].dropna().unique())
    )

    filtered_df = df.copy()

    if selected_hour:
        filtered_df = filtered_df[filtered_df['hour'].isin(selected_hour)]

    filtered_users = user_df[user_df['total_time'] >= min_time]

    # ==============================
    # SEARCH
    # ==============================
    search = st.text_input("🔍 Search User")
    if search:
        filtered_users = filtered_users[
            filtered_users['email'].astype(str).str.contains(search, case=False, na=False)
        ]

    # ==============================
    # TABLE
    # ==============================
    st.markdown("### 📋 User Report")
    st.dataframe(
        filtered_users.sort_values('total_time', ascending=False),
        use_container_width=True
    )

    # ==============================
    # CHARTS
    # ==============================
    st.markdown("### 📊 Top Users")
    fig1 = px.bar(
        filtered_users.head(10),
        x='email',
        y='total_time',
        title="Top 10 Users by Engagement Time"
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### ⏰ Hourly Join Distribution")
    hourly = df['hour'].value_counts().sort_index()

    fig2 = px.line(
        x=hourly.index,
        y=hourly.values,
        markers=True,
        title="Joins by Hour"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 📈 Session Time Distribution")
    fig3 = px.histogram(
        df,
        x='session_time',
        nbins=30,
        title="Session Duration Distribution"
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.markdown("### 🧠 Cohort Analysis")
    if 'join_time' in df.columns:
        df['cohort'] = df.groupby('email')['join_time'].transform('min').dt.date
        cohort_data = df.groupby(['cohort', 'date']).size().reset_index(name='users')

        fig4 = px.line(
            cohort_data,
            x='date',
            y='users',
            color='cohort',
            title="User Retention Over Time"
        )
        st.plotly_chart(fig4, use_container_width=True)

    st.markdown("### 🔥 Engagement Heatmap")
    if 'hour' in df.columns and 'date' in df.columns:
        heatmap = df.pivot_table(
            index='hour',
            columns='date',
            values='email',
            aggfunc='count'
        )

        fig5 = px.imshow(
            heatmap,
            aspect="auto",
            title="Hourly Engagement Heatmap"
        )
        st.plotly_chart(fig5, use_container_width=True)

    # ==============================
    # DOWNLOAD
    # ==============================
    st.download_button(
        "📥 Download Report",
        filtered_users.to_csv(index=False),
        "webinar_report.csv"
    )