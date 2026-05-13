import streamlit as st
import pandas as pd
import plotly.express as px

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Webinar Attendee Analytics",
    layout="wide"
)

st.title("🚀 Webinar Attendee Analytics")

# =========================================================
# FILE UPLOAD
# =========================================================
uploaded_file = st.file_uploader(
    "Upload Webinar Attendance File",
    type=["xls", "xlsx", "csv"]
)

# =========================================================
# FILE READER
# =========================================================
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


# =========================================================
# FIND ATTENDEE HEADER
# =========================================================
def find_attendee_header(df):

    attendee_section = None

    # FIND "Attendee Details"
    for i in range(len(df)):

        row_text = " ".join(
            df.iloc[i]
            .fillna("")
            .astype(str)
            .str.lower()
            .tolist()
        )

        if "attendee details" in row_text:

            attendee_section = i
            break

    if attendee_section is None:
        return 0

    # FIND HEADER BELOW ATTENDEE DETAILS
    for j in range(
        attendee_section,
        min(attendee_section + 10, len(df))
    ):

        row_text = " ".join(
            df.iloc[j]
            .fillna("")
            .astype(str)
            .str.lower()
            .tolist()
        )

        keywords = [
            "user name",
            "join time",
            "leave time",
            "time in ses"
        ]

        score = sum(
            keyword in row_text
            for keyword in keywords
        )

        if score >= 3:
            return j

    return attendee_section


# =========================================================
# MAIN APP
# =========================================================
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
        f"✅ Attendee Section Found at Row: {header_row}"
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
    # COLUMN MAPPING
    # =====================================================
    column_mapping = {}

    for col in df.columns:

        c = str(col).lower()

        if "user name" in c:
            column_mapping[col] = "user_name"

        elif "first name" in c:
            column_mapping[col] = "first_name"

        elif "last name" in c:
            column_mapping[col] = "last_name"

        elif "join time" in c:
            column_mapping[col] = "join_time"

        elif "leave time" in c:
            column_mapping[col] = "leave_time"

        elif (
            "time in ses" in c
            or "time in session" in c
        ):
            column_mapping[col] = "session_time"

        elif "country" in c:
            column_mapping[col] = "country"

    # RENAME
    df.rename(
        columns=column_mapping,
        inplace=True
    )

    # =====================================================
    # USER NAME CREATION
    # =====================================================
    if "user_name" not in df.columns:

        if (
            "first_name" in df.columns
            and "last_name" in df.columns
        ):

            df["user_name"] = (
                df["first_name"]
                .fillna("")
                .astype(str)
                .str.strip()
                + " " +
                df["last_name"]
                .fillna("")
                .astype(str)
                .str.strip()
            ).str.strip()

        elif "first_name" in df.columns:

            df["user_name"] = (
                df["first_name"]
                .fillna("")
                .astype(str)
            )

    # =====================================================
    # CLEAN USER NAMES
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

    # KEEP ONLY VALID ATTENDEES
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

    # ROUND VALUES
    user_df["avg_watch_time"] = (
        user_df["avg_watch_time"]
        .round(1)
    )

    # =====================================================
    # WEBINAR DURATION
    # =====================================================
    webinar_duration = (
        df["session_time"].max()
    )

    # =====================================================
    # FIX OVERLAPPING WATCH TIME
    # =====================================================
    user_df["total_watch_time"] = (
        user_df["total_watch_time"]
        .clip(upper=webinar_duration)
    )

    # =====================================================
    # QUALITY SCORE
    # =====================================================
    user_df["quality_score"] = (
        user_df["total_watch_time"]
        / user_df["join_count"]
    ).round(1)

    # =====================================================
    # COMPLETION %
    # =====================================================
    user_df["completion_%"] = (
        (
            user_df["total_watch_time"]
            / webinar_duration
        ) * 100
    ).round(1)

    # =====================================================
    # ATTENDANCE STABILITY
    # =====================================================
    def attendance_stability(x):

        if x <= 2:
            return "Stable"

        elif x <= 5:
            return "Moderate Rejoins"

        else:
            return "Unstable"

    user_df["attendance_stability"] = (
        user_df["join_count"]
        .apply(attendance_stability)
    )

    # =====================================================
    # REAL ENGAGEMENT LOGIC
    # =====================================================
    def engagement_level(row):

        watch_time = row["total_watch_time"]
        joins = row["join_count"]

        # HIGHLY ENGAGED
        if (
            watch_time >= 150
            and joins <= 3
        ):

            return "Highly Engaged"

        # MODERATE
        elif (
            watch_time >= 60
        ):

            return "Moderately Engaged"

        # LOW
        else:

            return "Low Engagement"

    user_df["engagement_level"] = (
        user_df
        .apply(
            engagement_level,
            axis=1
        )
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
        user_df["quality_score"]
        .mean(),
        1
    )

    highest_watch = (
        user_df["total_watch_time"]
        .max()
    )

    # =====================================================
    # DASHBOARD KPIs
    # =====================================================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👥 Unique Attendees",
        total_users
    )

    c2.metric(
        "🔁 Total Joins",
        total_joins
    )

    c3.metric(
        "⭐ Avg Quality Score",
        avg_watch
    )

    c4.metric(
        "🏆 Highest Watch Time",
        f"{highest_watch} mins"
    )

    # =====================================================
    # FILTERS
    # =====================================================
    st.sidebar.header("🎛 Filters")

    engagement_filter = st.sidebar.multiselect(
        "Engagement Level",
        user_df["engagement_level"]
        .unique(),
        default=user_df["engagement_level"]
        .unique()
    )

    filtered_users = user_df[
        user_df["engagement_level"]
        .isin(engagement_filter)
    ]

    # =====================================================
    # SEARCH
    # =====================================================
    search = st.text_input(
        "🔍 Search User"
    )

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
    st.subheader("📋 Attendee Analytics")

    st.dataframe(
        filtered_users.sort_values(
            "quality_score",
            ascending=False
        ),
        use_container_width=True
    )

    # =====================================================
    # TOP USERS CHART
    # =====================================================
    st.subheader("📊 Top Quality Attendees")

    top_users = (
        filtered_users
        .sort_values(
            "quality_score",
            ascending=False
        )
        .head(15)
    )

    fig1 = px.bar(
        top_users,
        x="user_name",
        y="quality_score",
        color="attendance_stability",
        title="Top Attendees By Quality Score"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # =====================================================
    # REJOIN CHART
    # =====================================================
    st.subheader("🔁 Rejoin Behaviour")

    fig2 = px.histogram(
        filtered_users,
        x="join_count",
        nbins=20,
        title="User Rejoin Distribution"
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================================
    # ENGAGEMENT DISTRIBUTION
    # =====================================================
    st.subheader("🔥 Engagement Distribution")

    engagement_counts = (
        filtered_users["engagement_level"]
        .value_counts()
        .reset_index()
    )

    engagement_counts.columns = [
        "engagement_level",
        "users"
    ]

    fig3 = px.pie(
        engagement_counts,
        names="engagement_level",
        values="users",
        title="Attendee Engagement Segments"
    )

    st.plotly_chart(
        fig3,
        use_container_width=True
    )

    # =====================================================
    # DOWNLOAD
    # =====================================================
    st.download_button(
        "📥 Download Analytics CSV",
        filtered_users.to_csv(index=False),
        "webinar_attendee_analytics.csv",
        mime="text/csv"
    )