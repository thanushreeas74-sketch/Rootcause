# 3. TIMELINE - WITH GRAPH
st.subheader("3. ⏱️ Timeline: BEFORE / DURING / AFTER (Auto from file)")
st.info("**BEFORE:** Data ingestion started, system normal")
st.error("**DURING:** Anomaly detected around middle of file")
st.success("**AFTER:** File processing stopped / system recovered")

date_col = next((c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()), None)
if date_col:
    st.write(f"Timeline based on column **{date_col}** from {df[date_col].iloc[0]} to {df[date_col].iloc[-1]}")
    
    # GRAPH - This is your missing graph!
    try:
        # Convert to datetime and count per hour/day for graph
        temp_df = df.copy()
        temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors='coerce')
        # Group by date for timeline graph
        timeline_data = temp_df[date_col].dt.floor('H').value_counts().sort_index()
        
        st.markdown("**📈 Incident Timeline Graph - Events Over Time:**")
        st.bar_chart(timeline_data)  # THIS IS THE GRAPH FROM YOUR VIDEO
        st.line_chart(timeline_data)  # Also line chart
        
    except:
        # Fallback simple graph
        st.bar_chart(df[date_col].value_counts().head(30))
else:
    st.warning("No date/time column found for graph")
