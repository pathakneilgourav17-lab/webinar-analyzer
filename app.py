import streamlit as st
import pandas as pd
import plotly.express as px

# ==================================================
# PAGE CONFIG
# ==================================================
st.set_page_config(
    page_title="Webinar Analyzer PRO+",
    layout="wide"
)

st.title("🚀 Webinar Analyzer PRO+")

# ==================================================
# FILE UPLOAD
# ==================================================
uploaded_file = st.file_uploader(
    "Upload Webinar File",
    type=["xls", "xlsx", "csv", "txt", "tsv"]
)

# ==================================================
# SAFE FILE READER
# ==================================================
def read_file(file, header=None):

    try:

        file.seek(0)

        # CSV / TXT
        if file.name.endswith((".csv", ".txt", ".tsv")):

            df = pd.read_csv(
                file,
                header=header,
                sep=None,
                engine="python",
                encoding="utf-8",
                on_bad_lines="skip"
            )

        # OLD XLS
        elif file.name.endswith(".xls"):

            df = pd.read_excel(
                file,
                header=header,
                engine="xlrd"
            )

        # XLSX
        else:

            df = pd.read_excel(
                file,
                header=header,
                engine="openpyxl"
            )

        return df

    except Exception as e:

        st.error(f"❌ File Read Error: {e}")
        return None


# ==================================================
# FIND HEADER ROW
# ==================================================
def find_header_row(df):

    keywords = [
        "name",
        "email",
        "mail",
        "join",
        "leave",
        "duration",
        "time",
        "minutes",
        "attendee"
    ]

    max_rows = min(len(df), 20)

    for i in range(max_rows):

        try:

            row = (
                df.iloc[i]
                .fillna("")
                .astype(str)
                .str.lower()
            )

            match_count = 0

            for cell in row:

                if any(k in str(cell) for k in keywords):
                    match_count += 1

            if match_count >= 2:
                return i

        except:
            pass

    return 0


# ==================================================
# COLUMN DETECTION
# ==================================================
def auto_map_columns(df):

    mapping = {}

    for col in df.columns:

        c = str(col).lower().strip()

        # EMAIL
        if any(k in c for k in [
            "email",
            "mail",
            "user email"
        ]):
            mapping[col] = "email"

        # NAME
        elif any(k in c for k in [
            "name",
            "participant",
            "attendee"
        ]):
            mapping[col] = "name"

        # JOIN TIME
        elif any(k in c for k in [
            "join time",
            "joined",
            "start time",
            "login"
        ]):
            mapping[col] = "join_time"

        # LEAVE TIME
        elif any(k in c for k in [
            "leave time",
            "left",
            "end time",
            "logout"
        ]):
            mapping[col] = "leave_time"

        # SESSION TIME
        elif any(k in c for k in [
            "duration",
            "watch time",
            "session duration",
            "time in session",
            "minutes"
        ]):
            mapping[col] = "session_time"

    return mapping


# ==================================================
# MAIN APP
# ==================================================
if uploaded_file:

    # ==================================================
    # RAW READ
    # ==================================================
    raw_df = read_file(
        uploaded_file,
        header=None
    )

    if raw_df is None or raw_df.empty:
        st.stop()

    # ==================================================
    # FIND HEADER
    # ==================================================
    header_row = find_header_row(raw_df)

    st.sidebar.success(
        f"✅ Header Row Detected: {header_row}"
    )

    # ==================================================
    # FINAL READ
    # ==================================================
    df = read_file(
        uploaded_file,
        header=header_row
    )

    if df is None or df.empty:
        st.stop()

    # ==================================================
    # CLEANING
    # ==================================================
    df.dropna(how="all", inplace=True)

    # CLEAN COLUMN NAMES
    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # REMOVE DUPLICATE COLUMNS
    df = df.loc[:, ~df.columns.duplicated()]

    # ==================================================
    # AUTO MAP
    # ==================================================
    col_map = auto_map_columns(df)

    df.rename(
        columns=col_map,
        inplace=True
    )

    # REMOVE DUPLICATE COLUMNS AGAIN
    df = df.loc[:, ~df.columns.duplicated()]

    # DEBUG
    st.sidebar.write("Detected Columns")
    st.sidebar.write(df.columns.tolist())

    # ==================================================
    # EMAIL FALLBACK
    # ==================================================
    if "email" not in df.columns:

        for col in df.columns:

            try:

                if (
                    df[col]
                    .astype(str)
                    .str.contains("@")
                    .any()
                ):

                    df.rename(
                        columns={col: "email"},
                        inplace=True
                    )

                    break

            except:
                pass

    # ==================================================
    # DATE CONVERSION
    # ==================================================
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

    # ==================================================
    # SESSION TIME
    # ==================================================
    if "session_time" not in df.columns:

        if (
            "join_time" in df.columns
            and "leave_time" in df.columns
        ):

            df["session_time"] = (
                (
                    df["leave_time"]
                    - df["join_time"]
                ).dt.total_seconds() / 60
            )

        else:

            df["session_time"] = 0

    # FIX SESSION TIME
    df["session_time"] = pd.to_numeric(
        df["session_time"],
        errors="coerce"
    ).fillna(0)

    # ==================================================
    # EXTRA COLUMNS
    # ==================================================
    if "join_time" in df.columns:

        df["hour"] = df["join_time"].dt.hour

    else:

        df["hour"] = 0

    # ==================================================
    # USER IDENTIFIER
    # ==================================================
    if "email" in df.columns:

        df["user_id"] = (
            df["email"]
            .astype(str)
            .str.strip()
        )

    elif "name" in df.columns:

        df["user_id"] = (
            df["name"]
            .astype(str)
            .str.strip()
        )

    else:

        df["user_id"] = df.index.astype(str)

    # REMOVE EMPTY IDS
    df = df[
        df["user_id"]
        .astype(str)
        .str.len() > 0
    ]

    # ==================================================
    # USER AGGREGATION
    # ==================================================
    agg_dict = {
        "session_time": "sum",
        "user_id": "count"
    }

    # NAME
    if "name" in df.columns:
        agg_dict["name"] = "first"

    # JOIN TIME
    if "join_time" in df.columns:
        agg_dict["join_time"] = "min"

    # LEAVE TIME
    if "leave_time" in df.columns:
        agg_dict["leave_time"] = "max"

    user_df = (
        df.groupby("user_id")
        .agg(agg_dict)
        .reset_index()
    )

    # RENAME
    user_df.rename(
        columns={
            "session_time": "total_watch_time",
            "user_id": "join_count",
            "join_time": "first_join",
            "leave_time": "last_leave"
        },
        inplace=True
    )

    # AVG WATCH TIME
    user_df["avg_watch_time"] = (
        user_df["total_watch_time"]
        / user_df["join_count"]
    ).round(1)

    # ENGAGEMENT %
    max_time = (
        user_df["total_watch_time"]
        .max()
    )

    if max_time > 0:

        user_df["engagement_%"] = (
            (
                user_df["total_watch_time"]
                / max_time
            ) * 100
        ).round(1)

    else:

        user_df["engagement_%"] = 0

    # ==================================================
    # METRICS
    # ==================================================
    unique_users = len(user_df)

    total_joins = (
        user_df["join_count"]
        .sum()
    )

    avg_time = round(
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

    # ==================================================
    # DASHBOARD
    # ==================================================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "👥 Users",
        unique_users
    )

    c2.metric(
        "🔁 Total Joins",
        total_joins
    )

    c3.metric(
        "⏱ Avg Watch Time",
        avg_time
    )

    c4.metric(
        "🔥 Avg Engagement",
        f"{avg_engagement}%"
    )

    st.info(
        f"⏰ Peak Join Hour: {peak_hour}:00"
    )

    # ==================================================
    # SEARCH
    # ==================================================
    search = st.text_input(
        "🔍 Search User"
    )

    filtered_users = user_df.copy()

    if search:

        filtered_users = filtered_users[
            filtered_users["join_count"]
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )
            |
            filtered_users.get(
                "name",
                pd.Series(dtype=str)
            )
            .astype(str)
            .str.contains(
                search,
                case=False,
                na=False
            )
        ]

    # ==================================================
    # USER TABLE
    # ==================================================
    st.subheader("📋 User Report")

    st.dataframe(
        filtered_users.sort_values(
            "total_watch_time",
            ascending=False
        ),
        use_container_width=True
    )

    # ==================================================
    # TOP USERS CHART
    # ==================================================
    st.subheader("📊 Top Users")

    fig1 = px.bar(
        filtered_users.head(10),
        x="name" if "name" in filtered_users.columns else "join_count",
        y="total_watch_time",
        title="Top Users by Watch Time"
    )

    st.plotly_chart(
        fig1,
        use_container_width=True
    )

    # ==================================================
    # HOURLY DISTRIBUTION
    # ==================================================
    st.subheader("⏰ Hourly Join Distribution")

    hourly = (
        df["hour"]
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

    # ==================================================
    # DOWNLOAD
    # ==================================================
    st.download_button(
        "📥 Download Report",
        filtered_users.to_csv(index=False),
        "webinar_report.csv",
        mime="text/csv"
    )