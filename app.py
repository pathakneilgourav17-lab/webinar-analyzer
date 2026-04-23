import streamlit as st
import pandas as pd

# ==============================
# PAGE SETUP
# ==============================
st.set_page_config(page_title="Webinar Analyzer PRO", layout="wide")
st.title("🚀 Webinar Analyzer PRO")

# ==============================
# FILE UPLOAD
# ==============================
file = st.file_uploader("Upload Excel", type=["xlsx"])

if file:

    # ==============================
    # STEP 1: READ RAW FILE
    # ==============================
    raw_df = pd.read_excel(file, header=None)

    def find_header_row(df):
        for i in range(len(df)):
            row = df.iloc[i]
            row_str = ' '.join([str(x).lower() for x in row])

            if 'email' in row_str and ('join' in row_str or 'time' in row_str):
                return i
        return None

    header_row = find_header_row(raw_df)

    if header_row is None:
        st.error("❌ Could not detect header row")
        st.stop()

    df = pd.read_excel(file, header=header_row)

    # ==============================
    # STEP 2: CLEAN DATA
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

    # Remove invalid rows
    df = df[df['email'].notna()]
    df = df[df['email'].astype(str).str.contains('@')]
    df = df[df['email'] != 'user email']

    # ==============================
    # STEP 3: TIME HANDLING
    # ==============================
    df['join_time'] = pd.to_datetime(df['join_time'], errors='coerce')
    df['leave_time'] = pd.to_datetime(df['leave_time'], errors='coerce')

    if 'session_time' not in df.columns or df['session_time'].isna().all():
        df['session_time'] = (
            (df['leave_time'] - df['join_time'])
            .dt.total_seconds() / 60
        )

    # ==============================
    # STEP 4: METRICS
    # ==============================
    unique_users = df['email'].nunique()
    total_joins = len(df)
    avg_time = df['session_time'].mean()

    result = df.groupby('email').agg({
        'name': 'first',
        'session_time': 'sum',
        'join_time': 'count'
    }).reset_index()

    result.rename(columns={
        'join_time': 'join_count',
        'session_time': 'total_time'
    }, inplace=True)

    result = result.sort_values(by='total_time', ascending=False)

    # ==============================
    # STEP 5: BUSINESS INSIGHTS
    # ==============================
    engaged_users = result[result['total_time'] > 50]
    engagement_rate = (len(engaged_users) / len(result)) * 100 if len(result) > 0 else 0

    df['hour'] = df['join_time'].dt.hour
    peak_hour = df['hour'].mode()[0] if not df['hour'].mode().empty else "N/A"

    # ==============================
    # STEP 6: DISPLAY METRICS
    # ==============================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("👥 Users", unique_users)
    col2.metric("🔁 Joins", total_joins)
    col3.metric("⏱ Avg Time", round(avg_time, 1) if pd.notna(avg_time) else 0)
    col4.metric("🔥 Engagement %", f"{round(engagement_rate,1)}%")

    st.info(f"⏰ Peak Join Time: {peak_hour}:00 hrs")

    # ==============================
    # STEP 7: SEARCH FILTER
    # ==============================
    search = st.text_input("🔍 Search User")

    if search:
        result = result[result['email'].str.contains(search, case=False, na=False)]

    # ==============================
    # STEP 8: TABLE
    # ==============================
    st.markdown("### 📋 User Report")
    st.dataframe(result, use_container_width=True)

    # ==============================
    # STEP 9: CHARTS
    # ==============================
    st.markdown("### 📊 Top 10 Users by Time")
    st.bar_chart(result.head(10).set_index('email')['total_time'])

    st.markdown("### 📈 Join Count Distribution")
    st.bar_chart(result['join_count'].value_counts())

    # ==============================
    # STEP 10: DOWNLOAD
    # ==============================
    st.download_button(
        "📥 Download Report",
        result.to_csv(index=False),
        file_name="webinar_report.csv"
    )