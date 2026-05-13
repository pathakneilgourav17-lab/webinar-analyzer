import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Webinar Attendance Analyzer",
    layout="wide"
)

st.title("🚀 Webinar Attendance Analyzer")

# =====================================================
# FILE UPLOAD
# =====================================================
uploaded_file = st.file_uploader(
    "Upload Webinar Attendance File",
    type=["xls", "xlsx", "csv"]
)

# =====================================================
# READ FILE
# =====================================================
def read_file(file, header=None):

    try:

        file.seek(0)

        if file.name.endswith(".csv"):

            return pd.read_csv(
                file,
                header=header,
                encoding="utf-8",
                on_bad_lines="skip"
            )

        elif file.name.endswith(".xls"):

            return pd.read_excel(
                file,
                header=header,
                engine="xlrd"
            )

        else:

            return pd.read_excel(
                file,
                header=header,
                engine="openpyxl"
            )

    except Exception as e:

        st.error(f"❌ Error Reading File: {e}")
        return None


# =====================================================
# FIND ATTENDEE HEADER
# =====================================================
def find_attendee_header(df):

    keywords = [
        "user name",
        "join time",
        "leave time",
        "time in ses"
    ]

    for i in range(min(40, len(df))):

        try:

            row = (
                df.iloc[i]
                .fillna("")
                .astype(str)
                .str.lower()
                .tolist()
            )

            row_text = " ".join(row)

            score = sum(
                keyword in row_text
                for keyword in keywords
            )

            if score >= 3:
                return i

        except:
            pass

    return 0


# =====================================================
# MAIN APP
# =====================================================
if uploaded_file:

    # =====================================================
    # RAW FILE
    # =====================================================
    raw_df = read_file(
        uploaded_file,
        header=None
    )

    if raw_df is None:
        st.stop()

    # =====================================================
    # FIND HEADER
    # =====================================================
    header_row = find_attendee_header(raw_df)

    st.sidebar.success(
        f"✅ Header Found at Row: {header_row}"
    )

    # =====================================================
    # FINAL READ
    # =====================================================
    df = read_file(
        uploaded_file,
        header=header_row
    )

    if df is None or df.empty:
        st.stop()

    # =====================================================
    # CLEAN COLUMNS
    # =====================================================
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # REMOVE DUPLICATE COLUMNS
    df = df.loc[:, ~df.columns.duplicated()]

    # =====================================================
    # COLUMN DETECTION
    # =====================================================
    column_mapping = {}

    for col in df.columns:

        c = str(col).lower()

        # USER NAME
        if "user name" in c:
            column_mapping[col] = "user_name"

        # JOIN TIME
        elif "join time" in c:
            column_mapping[col] = "join_time"

        # LEAVE TIME
        elif "leave time" in c:
            column_mapping[col] = "leave_time"

        # SESSION TIME
        elif (
            "time in ses" in c
            or "time in session" in c
        ):
            column_mapping[col] = "session_time"

    # RENAME
    df.rename(
        columns=column_mapping,
        inplace=True
    )

    # =====================================================
    # REQUIRED COLUMNS CHECK
    # =====================================================
    required_cols = [
        "user_name",
        "session_time"
    ]

    missing_cols = [
        col for col in required_cols
        if col not in df.columns
    ]

    if missing_cols:

        st.error(
            f"❌ Missing Columns: {missing_cols}"
        )

        st.stop()

    # =====================================================
    # CLEAN DATA
    # =====================================================
    df["user_name"] = (
        df["user_name"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    # REMOVE EMPTY USERS
    df = df[
        df["user_name"] != ""
    ]

    # REMOVE GARBAGE VALUES
    bad_values = [
        "yes",
        "approved",
        "guest",
        "india"
    ]

    df = df[
        ~df["user_name"]
        .str.lower()
        .isin(bad_values)
    ]

    # =====================================================
    # SESSION TIME
    # =====================================================
    df["session_time"] = pd.to_numeric(
        df["session_time"],
        errors="coerce"
    ).fillna(0)

    # KEEP VALID WATCH TIMES
    df = df[
        df["session_time"] > 0
    ]

    # =====================================================
    # DATE CONVERSION
    # =====================================================
    if "join_time" in df.columns:

        df["join_time"] = pd.to_datetime(
            df["join_time"],
            errors="coerce"
        )

    if "leave_time" in df.columns:

        df["leave_time"] = pd.to_datetime(
            df["leave_time"],
            errors="coerce"
        )

    # =====================================================
    # USER ANALYTICS
    # =====================================================
    user_df = (
        df.groupby("user_name")
        .agg(
            total_watch_time=(
                "session_time",
                "sum"
            ),

            avg_watch_time=(
                "session_time",
                "mean"
            ),

            join_count=(
                "user_name",
                "count"
            ),

            first_join=(
                "join_time",
                "min"
            ),

            last_leave=(
                "leave_time",
                "max"
            )
        )
        .reset_index()
    )

    # ROUND
    user_df["avg_watch_time"] = (
        user_df["avg_watch_time"]
        .round(1)
    )

    # =====================================================
    # METRICS
    # =====================================================
    total_users = len(user_df)

    total_joins = (
        user_df["join_count"]
        .sum()
    )

    avg_watch = round(
        user_df["total_watch_time"]
        .mean(),
        1
    )

    max_watch = (
        user_df["total_watch_time"]
        .max()
    )

    # =====================================================
    # TOP METRICS
    # =====================================================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👥 Unique Users",
        total_users
    )

    c2.metric(
        "🔁 Total Joins",
        total_joins
    )

    c3.metric(
        "⏱ Avg Watch Time",
        f"{avg_watch} mins"
    )

    c4.metric(
        "🏆 Highest Watch Time",
        f"{max_watch} mins"
    )

    # =====================================================
    # SEARCH
    # =====================================================
    search = st.text_input(
        "🔍 Search User"
    )

    filtered_users = user_df.copy()

    if search:

        filtered_users = filtered_users[
            filtered_users["user_name"]
            .str.contains(
                search,
                case=False,
                na=False
            )
        ]

    # =====================================================
    # TABLE
    # =====================================================
    st.subheader("📋 User Attendance Analytics")

    st.dataframe(
        filtered_users.sort_values(
            "total_watch_time",
            ascending=False
        ),
        use_container_width=True
    )

    # =====================================================
    # TOP USERS CHART
    # =====================================================
    st.subheader("📊 Users With Highest Watch Time")

    top_users = (
        filtered_users
        .sort_values(
            "total_watch_time",
            ascending=False
        )
        .head(15)
    )

    fig = px.bar(
        top_users,
        x="user_name",
        y="total_watch_time",
        title="Top Users by Watch Time"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # =====================================================
    # DOWNLOAD
    # =====================================================
    st.download_button(
        "📥 Download CSV",
        filtered_users.to_csv(index=False),
        "webinar_analytics.csv",
        mime="text/csv"
    )