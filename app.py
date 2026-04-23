import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# ML
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

st.set_page_config(page_title="Webinar Analyzer PRO+", layout="wide")
st.title("🚀 Webinar Analyzer PRO+ (AI Powered)")

file = st.file_uploader("Upload Excel", type=["xlsx"])

# ==============================
# HEADER DETECTION
# ==============================
def find_header_row(df):
    for i in range(len(df)):
        row_str = ' '.join([str(x).lower() for x in df.iloc[i]])
        if 'email' in row_str and ('join' in row_str or 'time' in row_str):
            return i
    return None


if file:
    raw_df = pd.read_excel(file, header=None)

    header_row = find_header_row(raw_df)

    if header_row is None:
        st.error("❌ Could not detect header row")
        st.stop()

    df = pd.read_excel(file, header=header_row)

    # ==============================
    # CLEAN DATA
    # ==============================
    df.columns = df.columns.str.lower().str.strip()

    df.rename(columns={
        'user email': 'email',
        'email address': 'email',
        'name': 'name',
        'join time': 'join_time',
        'leave time': 'leave_time',
        'duration (minutes)': 'session_time',
        'time in session': 'session_time'
    }, inplace=True)

    df = df[df['email'].notna()]
    df = df[df['email'].astype(str).str.contains('@')]

    # ==============================
    # TIME HANDLING
    # ==============================
    df['join_time'] = pd.to_datetime(df['join_time'], errors='coerce')
    df['leave_time'] = pd.to_datetime(df['leave_time'], errors='coerce')

    if 'session_time' not in df.columns or df['session_time'].isna().all():
        df['session_time'] = (
            (df['leave_time'] - df['join_time'])
            .dt.total_seconds() / 60
        )

    df['hour'] = df['join_time'].dt.hour

    # ==============================
    # USER LEVEL DATA
    # ==============================
    user_df = df.groupby('email').agg({
        'name': 'first',
        'session_time': 'sum',
        'join_time': 'count'
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

    engaged_users = user_df[user_df['total_time'] > 60]
    engagement_rate = (len(engaged_users) / len(user_df)) * 100 if len(user_df) > 0 else 0

    peak_hour = df['hour'].mode()[0] if not df['hour'].mode().empty else "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Users", unique_users)
    col2.metric("🔁 Joins", total_joins)
    col3.metric("⏱ Avg Time", round(avg_time, 1))
    col4.metric("🔥 Engagement %", f"{round(engagement_rate,1)}%")

    st.info(f"⏰ Peak Join Time: {peak_hour}:00 hrs")

    # ==============================
    # FILTERS
    # ==============================
    st.sidebar.header("Filters")

    min_time = st.sidebar.slider("Minimum Time", 0, 200, 0)

    filtered_users = user_df[user_df['total_time'] >= min_time]

    # ==============================
    # SEARCH
    # ==============================
    search = st.text_input("🔍 Search User")

    if search:
        filtered_users = filtered_users[
            filtered_users['email'].str.contains(search, case=False, na=False)
        ]

    # ==============================
    # ML MODEL (SAFE VERSION)
    # ==============================
    ml_df = user_df.copy()

    if len(ml_df) > 5:  # avoid crash on small data

        ml_df['high_engagement'] = (ml_df['total_time'] > 60).astype(int)

        X = ml_df[['total_time', 'join_count']]
        y = ml_df['high_engagement']

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

        model = RandomForestClassifier()
        model.fit(X_train, y_train)

        ml_df['engagement_prob'] = model.predict_proba(X)[:, 1]
        ml_df['engagement_score'] = (ml_df['engagement_prob'] * 100).round(1)

    else:
        ml_df['engagement_score'] = 0

    # ==============================
    # TABLE
    # ==============================
    st.markdown("### 📋 User Report")

    display_df = filtered_users.merge(
        ml_df[['email', 'engagement_score']],
        on='email',
        how='left'
    )

    st.dataframe(
        display_df.sort_values(by='total_time', ascending=False),
        use_container_width=True
    )

    # ==============================
    # CHARTS
    # ==============================
    st.markdown("### 📊 Top Users")

    fig1 = px.bar(
        display_df.head(10),
        x='email',
        y='total_time',
        title="Top Users by Time"
    )
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### 📈 Session Distribution")

    fig2 = px.histogram(
        df,
        x='session_time',
        nbins=30,
        title="Session Time Distribution"
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### ⏰ Hourly Joins")

    hourly = df['hour'].value_counts().sort_index()

    fig3 = px.line(
        x=hourly.index,
        y=hourly.values,
        markers=True,
        title="Joins by Hour"
    )
    st.plotly_chart(fig3, use_container_width=True)

    # ==============================
    # DOWNLOAD
    # ==============================
    st.download_button(
        "📥 Download Report",
        display_df.to_csv(index=False),
        "webinar_report.csv"
    )