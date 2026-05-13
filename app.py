import streamlit as st
import pandas as pd
import plotly.express as px

# =====================================================
# PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="Webinar Analyzer PRO+",
    layout="wide"
)

st.title("🚀 Webinar Analyzer PRO+")

# =====================================================
# FILE UPLOAD
# =====================================================
uploaded_file = st.file_uploader(
    "Upload Webinar File",
    type=["xls", "xlsx", "csv"]
)

# =====================================================
# FILE READER
# =====================================================
def read_file(file, header=None):

    try:

        file.seek(0)

        # CSV
        if file.name.endswith(".csv"):

            return pd.read_csv(
                file,
                header=header,
                encoding="utf-8",
                on_bad_lines="skip"
            )

        # XLS
        elif file.name.endswith(".xls"):

            return pd.read_excel(
                file,
                header=header,
                engine="xlrd"
            )

        # XLSX
        else:

            return pd.read_excel(
                file,
                header=header,
                engine="openpyxl"
            )

    except Exception as e:

        st.error(f"❌ File Read Error: {e}")
        return None


# =====================================================
# FIND ACTUAL ATTENDEE HEADER
# =====================================================
def find_attendee_header(df):

    keywords = [
        "first name",
        "last name",
        "join time",
        "leave time",
        "time in ses"
    ]

    max_rows = min(40, len(df))

    for i in range(max_rows):

        try:

            row = (
                df.iloc[i]
                .fillna("")
                .astype(str)
                .str.lower()
                .tolist()
            )

            joined = " ".join(row)

            score = sum(
                keyword in joined
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
        f"✅ Attendee Header Found at Row: {header_row}"
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

        # FIRST NAME
        if "first name" in c:
            column_mapping[col] = "first_name"

        # LAST NAME
        elif "last name" in c:
            column_mapping[col] = "last_name"

        # EMAIL
        elif "email" in c:
            column_mapping[col] = "email"

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

        # COUNTRY
        elif "country" in c:
            column_mapping[col] = "country"

        # APPROVAL
        elif "approval" in c:
            column_mapping[col] = "approval_status"

    # RENAME
    df.rename(
        columns=column_mapping,
        inplace=True
    )

    # =====================================================
    # NAME CREATION
    # =====================================================
    if (
        "first_name" in df.columns
        and "last_name" in df.columns
    ):

        df["full_name"] = (
            df["first_name"]
            .fillna("")
            .astype(str)
            + " "
            + df["last_name"]
            .fillna("")
            .astype(str)
        ).str.strip()

    elif "first_name" in df.columns:

        df["full_name"] = (
            df["first_name"]
            .astype(str)
        )

    else:

        df["full_name"] = "Unknown"

    # =====================================================
    # USER ID
    # =====================================================
    if "email" in df.columns:

        df["user_id"] = (
            df["email"]
            .fillna("")
            .astype(str)
            .str.strip()
        )

        # FALLBACK TO NAME
        df.loc[
            df["user_id"] == "",
            "user_id"
        ] = df["full_name"]

    else:

        df["user_id"] = df["full_name"]

    # =====================================================
    # SESSION TIME FIX
    # =====================================================
    if "session_time" in df.columns:

        df["session_time"] = pd.to_numeric(
            df["session_time"],
            errors="coerce"
        ).fillna(0)

    else:

        df["session_time"] = 0

    # =====================================================
    # DATE CONVERSION
    # =====================================================
    if "join_time" in df.columns:

        df["join_time"] = pd.to_datetime(
            df["join_time"],
            errors="coerce"
        )

        df["hour"] = (
            df["join_time"]
            .dt.hour
        )

    else:

        df["hour"] = 0

    if "leave_time" in df.columns:

        df["leave_time"] = pd.to_datetime(
            df["leave_time"],
            errors="coerce"
        )

    # =====================================================
    # REMOVE BLANK USERS
    # =====================================================
    df = df[
        df["user_id"]
        .astype(str)
        .str.len() > 0
    ]

    # =====================================================
    # JOIN COUNTS
    # =====================================================
    join_counts = (
        df.groupby("user_id")
        .size()
        .reset_index(name="join_count")
    )

    # =====================================================
    # USER AGGREGATION
    # =====================================================
    agg_dict = {
        "session_time": "sum",
        "full_name": "first"
    }

    if "join_time" in df.columns:
        agg_dict["join_time"] = "min"

    if "leave_time" in df.columns:
        agg_dict["leave_time"] = "max"

    if "country" in df.columns:
        agg_dict["country"] = "first"

    if "approval_status" in df.columns:
        agg_dict["approval_status"] = "first"

    user_df = (
        df.groupby("user_id")
        .agg(agg_dict)
        .reset_index()
    )

    # =====================================================
    # MERGE JOIN COUNTS
    # =====================================================
    user_df = user_df.merge(
        join_counts,
        on="user_id",
        how="left"
    )

    # =====================================================
    # RENAME
    # =====================================================
    user_df.rename(
        columns={
            "session_time": "total_watch_time",
            "join_time": "first_join",
            "leave_time": "last_leave"
        },
        inplace=True
    )

    # =====================================================
    # AVG WATCH TIME
    # =====================================================
    user_df["avg_watch_time"] = (
        user_df["total_watch_time"]
        / user_df["join_count"]
    ).round(1)

    # =====================================================
    # ENGAGEMENT %
    # =====================================================
    max_watch = (
        user_df["total_watch_time"]
        .max()
    )

    if max_watch > 0:

        user_df["engagement_%"] = (
            (
                user_df["total_watch_time"]
                / max_watch
            ) * 100
        ).round(1)

    else:

        user_df["engagement_%"] = 0

    # =====================================================
    # DASHBOARD METRICS
    # =====================================================
    unique_users = len(user_df)

    total_joins = (
        user_df["join_count"]
        .sum()
    )

    avg_watch = round(
        user_df["total_watch_time"]
        .mean(),
        1
    )

    avg_engagement = round(
        user_df["engagement_%"]
        .mean(),
        1
    )

    peak_hour = (
        df["hour"].mode()[0]
        if not df["hour"].mode().empty
        else "N/A"
    )

    # =====================================================
    # TOP METRICS
    # =====================================================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👥 Unique Users",
        unique_users
    )

    c2.metric(
        "🔁 Total Joins",
        total_joins
    )

    c3.metric(
        "⏱ Avg Watch Time",
        avg_watch
    )

    c4.metric(
        "🔥 Avg Engagement",
        f"{avg_engagement}%"
    )

    st.info(
        f"⏰ Peak Join Hour: {peak_hour}:00"
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
            filtered_users["full_name"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )
            |
            filtered_users["user_id"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )
        ]

    # =====================================================
    # USER REPORT
    # =====================================================
    st.subheader("📋 Attendee Analytics")

    display_cols = [
        "full_name",
        "user_id",
        "total_watch_time",
        "join_count",
        "avg_watch_time",
        "engagement_%"
    ]

    optional_cols = [
        "first_join",
        "last_leave",
        "country",
        "approval_status"
    ]

    for col in optional_cols:

        if col in filtered_users.columns:
            display_cols.append(col)

    st.dataframe(
        filtered_users[
            display_cols
        ].sort_values(
            "total_watch_time",
            ascending=False
        ),
        use_container_width=True
    )

    # =====================================================
    # TOP USERS CHART
    # =====================================================
    st.subheader("📊 Top Engaged Users")

    top_users = (
        filtered_users
        .sort_values(
            "total_watch_time",
            ascending=False
        )
        .head(10)
    )

    fig1 = px.bar(
        top_users,
        x="full_name",
        y="total_watch_time",
        title="Top Users by Watch Time"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # =====================================================
    # WATCH TIME DISTRIBUTION
    # =====================================================
    st.subheader("📈 Watch Time Distribution")

    fig2 = px.histogram(
        filtered_users,
        x="total_watch_time",
        nbins=30
    )

    st.plotly_chart(
        fig2,
        use_container_width=True
    )

    # =====================================================
    # COUNTRY DISTRIBUTION
    # =====================================================
    if "country" in filtered_users.columns:

        st.subheader("🌍 Country Distribution")

        country_df = (
            filtered_users["country"]
            .value_counts()
            .reset_index()
        )

        country_df.columns = [
            "country",
            "users"
        ]

        fig3 = px.pie(
            country_df.head(10),
            names="country",
            values="users"
        )

        st.plotly_chart(
            fig3,
            use_container_width=True
        )

    # =====================================================
    # HOURLY TREND
    # =====================================================
    st.subheader("⏰ Hourly Join Trend")

    hourly = (
        df["hour"]
        .value_counts()
        .sort_index()
    )

    fig4 = px.line(
        x=hourly.index,
        y=hourly.values,
        markers=True
    )

    st.plotly_chart(
        fig4,
        use_container_width=True
    )

    # =====================================================
    # DOWNLOAD
    # =====================================================
    st.download_button(
        "📥 Download Analytics",
        filtered_users.to_csv(index=False),
        "webinar_analytics.csv",
        mime="text/csv"
    )