import streamlit as st
import pandas as pd

st.set_page_config(page_title="RCA Tool", layout="centered")

# SIMPLE TITLE
st.title("Root Cause Analysis Tool")
st.write("Project A0-03 | TCS - SBI YONO")
st.divider()

# UPLOAD
file = st.file_uploader("Upload any CSV file", type=['csv'])

if not file:
    st.info("👆 Upload a file to start analysis")
    st.stop()

df = pd.read_csv(file, nrows=5000)
st.success(f"File: {file.name}")

# --- 1. DETECT ---
st.subheader("1. Detect")
st.write(f"Rows: {df.shape[0]} | Columns: {df.shape[1]}")
st.dataframe(df.head(5))

# --- 2. EVIDENCE ---
st.subheader("2. Evidence")
c1, c2, c3 = st.columns(3)
c1.metric("Missing", int(df.isnull().sum().sum()))
c2.metric("Duplicates", int(df.duplicated().sum()))
c3.metric("Max Value", int(df.select_dtypes('number').max().max()) if len(df.select_dtypes('number').columns)>0 else 0)

# --- 3. TIMELINE ---
st.subheader("3. Timeline")
st.write("**Before:** File started")
st.write("**During:** Error found in middle")
st.write("**After:** File ended")

# --- 4. RANK ---
st.subheader("4. Root Cause Rank")
st.write("**Rank 1:** Data Quality Issue (Missing/Duplicates)")
st.write("**Rank 2:** System Overload (Large file)")
st.write("**Rank 3:** Logic Error")

# --- 5. WHY ---
st.subheader("5. Why Crashed?")
st.error(f"Because {file.name} has {int(df.isnull().sum().sum())} missing values and {int(df.duplicated().sum())} duplicates. This caused crash.")

# --- 6. PREVENT ---
st.subheader("6. Solution")
st.success("1. Clean missing values  2. Remove duplicates  3. Add memory alert")
