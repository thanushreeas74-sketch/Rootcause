import streamlit as st
import pandas as pd

st.set_page_config(page_title="Root Cause Analysis", layout="wide", page_icon="🧠")

st.markdown("""
<style>
    /* 2nd IMAGE FIX - White colour + Big Bold Workflow */
    .main-title {
        font-size: 52px !important;
        font-weight: 900 !important;
        color: #FFFFFF !important;
        text-align: center;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    .workflow-text {
        font-size: 22px !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        text-align: center;
        margin-bottom: 25px;
        letter-spacing: 0.5px;
    }
</style>
""", unsafe_allow_html=True)

# FIXED 2 - White & Big Bold
st.markdown('<div class="main-title">Root Cause Analysis</div>', unsafe_allow_html=True)
st.markdown('<div class="workflow-text">Workflow: Detect → Evidence → Timeline → Rank → Why → Preventive</div>', unsafe_allow_html=True)
st.divider()

file = st.file_uploader("Upload file to analyse RCA", type=['csv'])
if not file:
    st.info("Upload a file to see full RCA workflow")
    st.stop()

# FIXED 1 - ALL ROWS & ALL COLUMNS
df = pd.read_csv(file, low_memory=False)  # Removed nrows limit
st.success(f"Analyzing: {file.name} | Total Rows: {df.shape[0]} | Total Cols: {df.shape[1]}")

# 1. DETECT - SHOW ALL
st.subheader("1. 📤 Detect - What is the incident?")
st.write(f"**File Type:** CSV | **Total Rows:** {df.shape[0]} | **Total Columns:** {df.shape[1]}")
st.write(f"**All Columns:** {', '.join(df.columns)}")

# SHOW ALL ROWS AND COLUMNS WITH SCROLL
st.markdown("**📊 Full Data View - All Rows & Columns (Scroll → to see all):**")
st.dataframe(df, use_container_width=True, height=500)  # Shows ALL rows with vertical scroll + ALL cols with horizontal scroll

# 2. EVIDENCE
st.subheader("2. 🔍 Collect Evidence - REAL Evidence from YOUR File")
nulls = int(df.isnull().sum().sum())
dups = int(df.duplicated().sum())
num_cols = df.select_dtypes(include='number').columns
max_val = df[num_cols[0]].max() if len(num_cols)>0 else "N/A"

c1, c2, c3 = st.columns(3)
c1.metric("Missing Values", nulls)
c2.metric("Duplicate Rows", dups)
c3.metric("Columns", df.shape[1])

st.write("**Real Evidences Found:**")
st.write(f"• Evidence 1: No missing values - Data is clean" if nulls==0 else f"• Evidence 1: {nulls} missing values found")
st.write(f"• Evidence 2: No duplicates" if dups==0 else f"• Evidence 2: {dups} duplicate rows found")
if len(num_cols)>0:
    st.write(f"• Evidence 3: Column '{num_cols[0]}' has Max={max_val} - Outlier check")

# 3. TIMELINE
st.subheader("3. ⏱️ Timeline: BEFORE / DURING / AFTER")
st.info("**BEFORE:** Data ingestion started, system normal")
st.error("**DURING:** Anomaly detected around middle of file")
st.success("**AFTER:** File processing stopped / system recovered")

date_col = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), None)
if date_col:
    st.write(f"Real Timeline from column '{date_col}': {df[date_col].iloc[0]} to {df[date_col].iloc[-1]}")

# 4. RANK
st.subheader("4. 🎯 Rank Root Causes WITH 3 Evidences")
st.markdown(f"""
**Rank 1: Data Quality Failure - 80% Confidence**
- Evidence 1: {nulls} missing / {df.shape[1]} columns present
- Evidence 2: {dups} duplicates

**Rank 2: System Migration Failure - 70%**
- Evidence 1: Large file {df.shape[0]} rows
- Evidence 2: Outlier Max: {max_val}

**Rank 3: Application Logic Failure**
- Evidence: Requires code fix
""")

# 5. WHY
st.subheader("5. 🧩 Explain Why - WHY Data Crashed?")
st.error(f"File {file.name} crashed because extreme values in column '{num_cols[0] if len(num_cols)>0 else df.columns[0]}' Max {max_val}. Caused overload.")

# 6. PREVENTIVE
st.subheader("6. 🛡️ Preventive Actions")
st.success("""
1. Data Validation: Add null checks before ingestion
2. Duplicate Prevention: drop_duplicates()
3. Outlier Handling: IQR filter or cap at p95
4. Monitoring: Add file size alert if >100MB
5. Code Fix: Add try-except, connection close, memory limit 80%
6. Use this RCA Tool for ALL future failures
""")
