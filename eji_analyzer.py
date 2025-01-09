import streamlit as st
import pandas as pd
import numpy as np
from config import INDICATOR_DESCRIPTIONS

# --- STYLING ---
st.set_page_config(page_title="CDC Environmental Justice Index State Explorer", layout="wide")

st.markdown("""
    <style>
        .main {
            background-color: #f5f5f5;
        }
        h1, h2, h3 {
            color: #0071BC;
        }
        [data-testid="stSidebar"] {
            background-color: #e0e0e0;
        }
        [data-testid="stHeader"] {
            background-color: transparent;
        }
        [data-testid="stToolbar"] {
            display: none;
        }
        .stDownloadButton > button {
            background-color: #0071BC;
            color: white;
            border: none;
            padding: 0.5em 1em;
            cursor: pointer;
        }
        .stDownloadButton > button:hover {
            background-color: #00518f;
        }
    </style>
""", unsafe_allow_html=True)

# --- DATA LOADING ---
@st.cache_data
def load_data():
    """Load and preprocess the EJI data."""
    df = pd.read_csv('data/CDC_EJI_US.csv')
    
    # Replace -999 with NaN
    df = df.replace(-999, np.nan)
    
    # Convert relevant columns to numeric
    numeric_columns = [col for col, desc in INDICATOR_DESCRIPTIONS.items() 
                      if col in df.columns and col.startswith(('E_', 'EP_', 'EPL_', 'SPL_', 'RPL_', 'F_'))]
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    return df

# --- APP HEADER ---
st.title("CDC Environmental Justice Index State Explorer")
st.markdown("Explore county-level environmental justice indicators across states.")

# Load data directly
try:
    df = load_data()
    
    # State selection
    states = sorted(df['StateDesc'].unique())
    selected_state = st.selectbox("Select a State", states)
    
    # Filter data for selected state
    state_data = df[df['StateDesc'] == selected_state].copy()
    
    # Select columns to display
    display_columns = {
        'COUNTY': 'County',
        'EPL_MINRTY': 'Minority Population Percentile',
        'EPL_POV200': 'Population Below 200% Poverty Percentile',
        'EPL_UNEMP': 'Unemployment Percentile',
        'EPL_DSLPM': 'Diesel Particulate Matter Percentile',
        'EPL_CANCER': 'Cancer Risk Percentile',
        'EPL_RESP': 'Respiratory Hazard Percentile',
        'RPL_EJI': 'Overall EJ Index Percentile'
    }
    
    # Only include columns that exist in the dataset
    available_columns = {k: v for k, v in display_columns.items() if k in state_data.columns}
    
    if available_columns:
        # Create display dataframe
        display_df = state_data[list(available_columns.keys())].copy()
        display_df.columns = list(available_columns.values())
        
        # Convert percentile values from 0-1 to 0-100 and format them
        for col in display_df.columns:
            if 'Percentile' in col and col != 'County':
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce') * 100
                display_df[col] = display_df[col].round(1)
        
        # Display summary statistics
        st.subheader(f"Environmental Justice Summary for {selected_state}")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Number of Counties",
                len(state_data)
            )
        
        with col2:
            avg_eji = state_data['RPL_EJI'].mean() * 100
            st.metric(
                "Average EJ Index Percentile",
                f"{avg_eji:.1f}%" if pd.notnull(avg_eji) else "N/A"
            )
        
        with col3:
            high_risk_counties = len(state_data[state_data['RPL_EJI'] > 0.80])
            st.metric(
                "High Risk Counties (>80th percentile)",
                high_risk_counties
            )
        
        # Display county data table
        st.subheader("County-Level Data")
        
        # Configure the dataframe display
        st.dataframe(
            display_df.sort_values('Overall EJ Index Percentile', ascending=False),
            hide_index=True,
            use_container_width=True,
            column_config={
                "County": st.column_config.TextColumn(
                    "County",
                    width="medium"
                ),
                "Minority Population Percentile": st.column_config.ProgressColumn(
                    "Minority Population",
                    help="Percentile rank of minority population percentage",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "Population Below 200% Poverty Percentile": st.column_config.ProgressColumn(
                    "Poverty Level",
                    help="Percentile rank of population below 200% poverty level",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "Unemployment Percentile": st.column_config.ProgressColumn(
                    "Unemployment",
                    help="Percentile rank of unemployment rate",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "Diesel Particulate Matter Percentile": st.column_config.ProgressColumn(
                    "Diesel Pollution",
                    help="Percentile rank of diesel particulate matter concentration",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "Cancer Risk Percentile": st.column_config.ProgressColumn(
                    "Cancer Risk",
                    help="Percentile rank of cancer risk",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
                "Overall EJ Index Percentile": st.column_config.ProgressColumn(
                    "Overall EJ Index",
                    help="Overall Environmental Justice Index percentile",
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                ),
            }
        )
        
        # Add download button
        csv = display_df.to_csv(index=False)
        st.download_button(
            label="Download Data (CSV)",
            data=csv,
            file_name=f"{selected_state}_EJI_data.csv",
            mime="text/csv"
        )
        
        # Add methodology note
        st.markdown("---")
        st.markdown("""
        **Methodology Notes:**
        - All percentile values range from 0-100, where higher values indicate greater potential for environmental justice concerns
        - The Overall EJ Index combines environmental, social, and health vulnerability indicators
        - Counties with "N/A" values lack sufficient data for that indicator
        """)
    else:
        st.error("Required columns not found in the dataset. Please ensure you're using the correct CDC EJI data format.")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please ensure the CDC EJI data file is located at 'data/CDC_EJI_US.csv'")