import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Webinar Analyzer PRO+", layout="wide")
st.title("🚀 Webinar Analyzer PRO+")

# =========================================
# FILE UPLOAD
# =========================================
file = st.file_uploader(
    "Upload File",
    type=["xlsx", "xls", "csv", "tsv", "txt"]
)

# =========================================
# SMART HEADER DETECTION
# =========================================
def find_header_row(df):

    keywords = [
        'email',
        'mail',
        'name',
        'join',
        'time',
        'duration'
    ]

    for i in range(len(df)):

        row = df.iloc[i].astype(str).str.lower()

        match_count = sum(
            any(k in cell for k in keywords)
            for cell in row
        )

        if match_count >= 2:
            return i

    return 0


# =========================================
# SMART FILE READER
# =========================================
def read_file(file, header=None):

    # -----------------------------
    # TRY CSV / TXT FIRST
    # -----------------------------
    try:

        file.seek(0)

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
        pass

    # -----------------------------
    # TRY EXCEL
    # -----------------------------
    try:

        file.seek(0)

        # OLD XLS SUPPORT
        if file.name.endswith(".xls"):

            df = pd.read_excel(
                file,
                header=header,
                engine="xlrd"
            )

        else:

            df = pd.read_excel(
                file,
                header=header
            )

        return df

    except Exception as e:

        st.error(f"❌ File Read Error: {e}")
        return None


# =========================================
# AUTO COLUMN DETECTION
# =========================================
def auto_map_columns(df):

    col_map = {}

    for col in df.columns:

        c = str(col).lower()

        # EMAIL
        if any(k in c for k in ['email', 'mail']):
            col_map[col] = 'email'

        # NAME
        elif any(k in c for k in ['name', 'user']):
            col_map[col] = 'name'

        # JOIN TIME
        elif any(k in c for k in ['join', 'login', 'start']):
            col_map[col] = 'join_time'

        # LEAVE TIME
        elif any(k in c for k in ['leave', 'logout', 'end']):
            col_map[col] = 'leave_time'

        # SESSION TIME
        elif any(k in c for k in ['duration', 'minutes', 'mins']):
            col_map[col] = 'session_time'

    return col_map


# =========================================
# MAIN APP
# =========================================
if file:

    # =====================================
    # READ RAW FILE
    # =====================================
    raw_df = read_file(file, header=None)

    if raw_df is None or raw_df.empty:
        st.stop()

    # =====================================
    # DETECT HEADER
    # =====================================
    header_row = find_header_row(raw_df)

    st.sidebar.success(f"✅ Header detected at row: {header_row}")

    # =====================================
    # READ FINAL DATA
    # =====================================
    df = read_file(file, header=header_row)

    if df is None or df.empty:
        st.stop()

    # =====================================
    # CLEAN DATA
    # =====================================
    df = df.dropna(how='all')

    df.columns = (
        df.columns
        .astype(str)
        .str.lower()
        .str.strip()
    )

    # =====================================
    # AUTO MAP COLUMNS
    # =====================================
    col_map = auto_map_columns(df)

    df.rename(columns=col_map, inplace=True)

    st.sidebar.write("🔍 Detected Columns")
    st.sidebar.write(col_map)

    # =====================================
    # EMAIL FALLBACK
    # =====================================
    if 'email' not in df.columns:

        for col in df.columns:

            try:

                if df[col].astype(str).str.contains('@').any():

                    df.rename(columns={col: 'email'}, inplace=True)
                    break

            except:
                pass

    # STILL NO EMAIL
    if 'email' not in df.columns:

        df['email'] = df.index.astype(str)

        st.warning(
            "⚠️ Email column not found. Using row number."
        )

    # REMOVE EMPTY EMAILS
    df = df[df['email'].notna()]
    df = df[df['email'].astype(str).str.len() > 0]

    # =====================================
    # DATE TIME CONVERSION
    # =====================================
    if 'join_time' in df.columns:

        df['join_time'] = pd.to_datetime(
            df['join_time'],
            errors='coerce'
        )

    if 'leave_time' in df.columns:

        df['leave_time'] = pd.to_datetime(
            df['leave_time'],
            errors='coerce'
        )

    # =====================================
    # SESSION TIME CALCULATION
    # =====================================
    if (
        'session_time' not in df.columns
        or df['session_time'].isna().all()
    ):

        if (
            'join_time' in df.columns
            and 'leave_time' in df.columns
        ):

            df['session_time'] = (
                (
                    df['leave_time']
                    - df['join_time']
                ).dt.total_seconds() / 60
            )

    # STILL NO SESSION TIME
    if 'session_time' not in df.columns:
        df['session_time'] = 0

    # NUMERIC CONVERSION
    df['session_time'] = pd.to_numeric(
        df['session_time'],
        errors='coerce'
    ).fillna(0)

    # EXTRA COLUMNS
    if 'join_time' in df.columns:

        df['hour'] = df['join_time'].dt.hour
        df['date'] = df['join_time'].dt.date

    else:

        df['hour'] = 0
        df['date'] = None

    # =====================================
    # USER AGGREGATION
    # =====================================
    agg_dict = {
        'session_time': 'sum'
    }

    if 'name' in df.columns:
        agg_dict['name'] = 'first'

    if 'join_time' in df.columns:
        agg_dict['join_time'] = 'count'

    user_df = (
        df.groupby('email')
        .agg(agg_dict)
        .reset_index()
    )

    # RENAME
    if 'join_time' in user_df.columns:
        user_df.rename(
            columns={
                'join_time': 'join_count'
            },
            inplace=True
        )

    user_df.rename(
        columns={
            'session_time': 'total_time'
        },
        inplace=True
    )

    # =====================================
    # METRICS
    # =====================================
    unique_users = df['email'].nunique()

    total_joins = len(df)

    avg_time = round(
        df['session_time'].mean(),
        1
    )

    engaged_users = user_df[
        user_df['total_time'] > 50
    ]

    engagement_rate = round(
        (
            len(engaged_users)
            / len(user_df)
        ) * 100,
        1
    ) if len(user_df) > 0 else 0

    peak_hour = (
        df['hour'].mode()[0]
        if not df['hour'].mode().empty
        else "N/A"
    )

    # =====================================
    # DASHBOARD METRICS
    # =====================================
    col1, col2, col3, col4 = st.columns(4)

    col1.metric("👥 Users", unique_users)
    col2.metric("🔁 Total Joins", total_joins)
    col3.metric("⏱ Avg Time", avg_time)
    col4.metric("🔥 Engagement", f"{engagement_rate}%")

    st.info(f"⏰ Peak Join Time: {peak_hour}:00 hrs")

    # =====================================
    # SIDEBAR FILTERS
    # =====================================
    st.sidebar.header("🎛 Filters")

    min_time = st.sidebar.slider(
        "Minimum Session Time",
        0,
        300,
        0
    )

    selected_hour = st.sidebar.multiselect(
        "Select Hour",
        sorted(df['hour'].dropna().unique())
    )

    filtered_df = df.copy()

    if selected_hour:

        filtered_df = filtered_df[
            filtered_df['hour'].isin(selected_hour)
        ]

    filtered_users = user_df[
        user_df['total_time'] >= min_time
    ]

    # =====================================
    # SEARCH
    # =====================================
    search = st.text_input("🔍 Search User")

    if search:

        filtered_users = filtered_users[
            filtered_users['email']
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )
        ]

    # =====================================
    # USER TABLE
    # =====================================
    st.markdown("## 📋 User Report")

    st.dataframe(
        filtered_users.sort_values(
            by='total_time',
            ascending=False
        ),
        use_container_width=True
    )

    # =====================================
    # TOP USERS CHART
    # =====================================
    st.markdown("## 📊 Top Users")

    fig1 = px.bar(
        filtered_users.head(10),
        x='email',
        y='total_time',
        title="Top 10 Users by Engagement"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # =====================================
    # HOURLY DISTRIBUTION
    # =====================================
    st.markdown("## ⏰ Hourly Join Distribution")

    hourly = (
        df['hour']
        .value_counts()
        .sort_index()
    )

    fig2 = px.line(
        x=hourly.index,
        y=hourly.values,
        markers=True,
        title="Joins by Hour"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================
    # SESSION DISTRIBUTION
    # =====================================
    st.markdown("## 📈 Session Time Distribution")

    fig3 = px.histogram(
        df,
        x='session_time',
        nbins=30,
        title="Session Duration Distribution"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # =====================================
    # COHORT ANALYSIS
    # =====================================
    if 'join_time' in df.columns:

        st.markdown("## 🧠 Cohort Analysis")

        df['cohort'] = (
            df.groupby('email')['join_time']
            .transform('min')
            .dt.date
        )

        cohort_data = (
            df.groupby(['cohort', 'date'])
            .size()
            .reset_index(name='users')
        )

        fig4 = px.line(
            cohort_data,
            x='date',
            y='users',
            color='cohort',
            title="User Retention"
        )

        st.plotly_chart(
            fig4,
            use_container_width=True
        )

    # =====================================
    # HEATMAP
    # =====================================
    if 'hour' in df.columns and 'date' in df.columns:

        st.markdown("## 🔥 Engagement Heatmap")

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

        st.plotly_chart(
            fig5,
            use_container_width=True
        )

    # =====================================
    # DOWNLOAD REPORT
    # =====================================
    st.download_button(
        label="📥 Download Report",
        data=filtered_users.to_csv(index=False),
        file_name="webinar_report.csv",
        mime="text/csv"
    )