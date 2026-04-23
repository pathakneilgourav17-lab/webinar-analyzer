import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler

st.set_page_config(page_title="Webinar Analyzer PRO++", layout="wide")
st.title("🚀 Webinar Analyzer PRO++ (AI + Retention Intelligence)")

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
    # CLEANING
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
    df['date'] = df['join_time'].dt.date

    # ==============================
    # USER LEVEL AGG
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

    user_df['avg_time'] = user_df['total_time'] / user_df['join_count']

    # ==============================
    # RETENTION FEATURE
    # ==============================
    user_df['active_days'] = df.groupby('email')['date'].nunique().values

    # Dropout label (Low engagement)
    user_df['dropout'] = (user_df['total_time'] < 30).astype(int)

    features = ['total_time', 'join_count', 'avg_time', 'active_days']

    # ==============================
    # ML MODEL
    # ==============================
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(user_df[features], user_df['dropout'])

    dropout_prob = model.predict_proba(user_df[features])[:, 1]

    scaler = MinMaxScaler()
    user_df['dropout_risk'] = scaler.fit_transform(dropout_prob.reshape(-1,1)) * 100
    user_df['dropout_risk'] = user_df['dropout_risk'].round(0)

    # Engagement Score (inverse of dropout)
    user_df['engagement_score'] = 100 - user_df['dropout_risk']

    # Segmentation
    def segment(score):
        if score > 70:
            return "High"
        elif score > 40:
            return "Medium"
        else:
            return "Low"

    user_df['segment'] = user_df['engagement_score'].apply(segment)

    # ==============================
    # METRICS
    # ==============================
    unique_users = df['email'].nunique()
    total_joins = len(df)
    avg_time = df['session_time'].mean()
    retention_rate = (user_df['active_days'] > 1).mean() * 100
    dropout_rate = (user_df['dropout'] == 1).mean() * 100

    peak_hour = df['hour'].mode()[0]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("👥 Users", unique_users)
    col2.metric("🔁 Joins", total_joins)
    col3.metric("📈 Retention %", round(retention_rate,1))
    col4.metric("⚠️ Dropout %", round(dropout_rate,1))

    st.info(f"⏰ Peak Join Time: {peak_hour}:00 hrs")

    # ==============================
    # FILTER
    # ==============================
    st.sidebar.header("Filters")

    min_score = st.sidebar.slider("Min Engagement Score", 0, 100, 0)

    filtered = user_df[user_df['engagement_score'] >= min_score]

    # ==============================
    # SEARCH
    # ==============================
    search = st.text_input("🔍 Search User")
    if search:
        filtered = filtered[
            filtered['email'].str.contains(search, case=False)
        ]

    # ==============================
    # TABLE
    # ==============================
    st.markdown("### 📋 User Report")
    st.dataframe(filtered.sort_values('engagement_score', ascending=False),
                 use_container_width=True)

    # ==============================
    # CHARTS
    # ==============================

    st.markdown("### 📊 Engagement vs Dropout")
    fig1 = px.scatter(user_df,
                      x='total_time',
                      y='dropout_risk',
                      color='segment',
                      hover_data=['email'])
    st.plotly_chart(fig1, use_container_width=True)

    st.markdown("### 🎯 Segment Distribution")
    fig2 = px.pie(user_df, names='segment')
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("### 🔥 Dropout Risk Distribution")
    fig3 = px.histogram(user_df, x='dropout_risk', nbins=20)
    st.plotly_chart(fig3, use_container_width=True)

    # ==============================
    # DOWNLOAD
    # ==============================
    st.download_button(
        "📥 Download Report",
        filtered.to_csv(index=False),
        "webinar_ai_advanced_report.csv"
    )