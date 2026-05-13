import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Webinar Analyzer PRO+", layout="wide")

st.title("🚀 Webinar Analyzer PRO+")

# ==================================================
# FILE UPLOADER
# ==================================================
uploaded_file = st.file_uploader(
    "Upload File",
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

            return pd.read_csv(
                file,
                header=header,
                sep=None,
                engine="python",
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


# ==================================================
# HEADER DETECTION
# ==================================================
def find_header_row(df):

    keywords = [
        "email",
        "mail",
        "name",
        "join",
        "leave",
        "duration",
        "time",
        "minutes"
    ]

    for i in range(min(len(df), 20)):

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
# AUTO COLUMN DETECTION
# ==================================================
def auto_map_columns(df):

    mapping = {}

    for col in df.columns:

        c = str(col).lower()

        if any(k in c for k in ["email", "mail"]):
            mapping[col] = "email"

        elif any(k in c for k in ["name", "user"]):
            mapping[col] = "name"

        elif any(k in c for k in ["join", "start", "login"]):
            mapping[col] = "join_time"

        elif any(k in c for k in ["leave", "end", "logout"]):
            mapping[col] = "leave_time"

        elif any(k in c for k in ["duration", "minutes", "mins"]):
            mapping[col] = "session_time"

    return mapping


# ==================================================
# MAIN LOGIC
# ==================================================
if uploaded_file:

    # RAW FILE
    raw_df = read_file(uploaded_file, header=None)

    if raw_df is None or raw_df.empty:
        st.stop()

    # HEADER DETECTION
    header_row = find_header_row(raw_df)

    st.sidebar.success(f"✅ Header Row: {header_row}")

    # FINAL READ
    df = read_file(uploaded_file, header=header_row)

    if df is None or df.empty:
        st.stop()

    # ==================================================
    # CLEANING
    # ==================================================
    df.dropna(how="all", inplace=True)

    df.columns = (
        df.columns
        .astype(str)
        .str.strip()
        .str.lower()
    )

    # AUTO MAP
    col_map = auto_map_columns(df)

    df.rename(columns=col_map, inplace=True)

    st.sidebar.write("Detected Columns")
    st.sidebar.write(col_map)

    # ==================================================
    # EMAIL FALLBACK
    # ==================================================
    if "email" not in df.columns:

        for col in df.columns:

            try:

                if df[col].astype(str).str.contains("@").any():

                    df.rename(
                        columns={col: "email"},
                        inplace=True
                    )

                    break

            except:
                pass

    # STILL NO EMAIL
    if "email" not in df.columns:

        df["email"] = df.index.astype(str)

        st.warning(
            "⚠️ Email not found. Using row index."
        )

    # REMOVE EMPTY EMAILS
    df = df[df["email"].notna()]

    # ==================================================
    # DATE HANDLING
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

    # NUMERIC FIX
    df["session_time"] = pd.to_numeric(
        df["session_time"],
        errors="coerce"
    ).fillna(0)

    # EXTRA COLUMNS
    if "join_time" in df.columns:

        df["hour"] = df["join_time"].dt.hour
        df["date"] = df["join_time"].dt.date

    else:

        df["hour"] = 0
        df["date"] = None

    # ==================================================
    # USER AGGREGATION
    # ==================================================
    agg_dict = {
        "session_time": "sum"
    }

    if "name" in df.columns:
        agg_dict["name"] = "first"

    if "join_time" in df.columns:
        agg_dict["join_time"] = "count"

    user_df = (
        df.groupby("email")
        .agg(agg_dict)
        .reset_index()
    )

    # RENAME
    if "join_time" in user_df.columns:

        user_df.rename(
            columns={
                "join_time": "join_count"
            },
            inplace=True
        )

    user_df.rename(
        columns={
            "session_time": "total_time"
        },
        inplace=True
    )

    # ==================================================
    # METRICS
    # ==================================================
    unique_users = df["email"].nunique()

    total_joins = len(df)

    avg_time = round(
        df["session_time"].mean(),
        1
    )

    engagement_rate = round(
        (
            len(
                user_df[
                    user_df["total_time"] > 50
                ]
            )
            / len(user_df)
        ) * 100,
        1
    ) if len(user_df) > 0 else 0

    peak_hour = (
        df["hour"].mode()[0]
        if not df["hour"].mode().empty
        else "N/A"
    )

    # ==================================================
    # DASHBOARD
    # ==================================================
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("👥 Users", unique_users)
    c2.metric("🔁 Joins", total_joins)
    c3.metric("⏱ Avg Time", avg_time)
    c4.metric("🔥 Engagement", f"{engagement_rate}%")

    st.info(f"⏰ Peak Hour: {peak_hour}:00")

    # ==================================================
    # USER TABLE
    # ==================================================
    st.subheader("📋 User Report")

    st.dataframe(
        user_df.sort_values(
            "total_time",
            ascending=False
        ),
        use_container_width=True
    )

    # ==================================================
    # CHART
    # ==================================================
    st.subheader("📊 Top Users")

    fig = px.bar(
        user_df.head(10),
        x="email",
        y="total_time"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    # ==================================================
    # DOWNLOAD
    # ==================================================
    st.download_button(
        "📥 Download Report",
        user_df.to_csv(index=False),
        "webinar_report.csv"
    )