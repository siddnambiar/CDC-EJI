import streamlit as st
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from typing import List, Dict
import io
from config import INDICATOR_DESCRIPTIONS  # Import from config.py
from scipy import stats

# --- CONSTANTS ---
NO_DATA_VALUE = -999
CDC_PRIMARY_COLOR = '#0071BC'
CDC_SECONDARY_COLOR = '#666666'

# --- DATA LOADING AND PREPROCESSING ---
@st.cache_data
def load_and_preprocess_data(file_path: str) -> pd.DataFrame:
    """Loads and preprocesses the EJI data."""
    try:
        df = pd.read_csv(file_path)
    except FileNotFoundError:
        st.error(f"File not found at: {file_path}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"An error occurred while reading the file: {e}")
        return pd.DataFrame()

    # Replace no data value with NaN
    df = df.replace(NO_DATA_VALUE, np.nan)

    # Convert relevant columns to numeric, handling non-numeric data
    columns_to_convert = list(INDICATOR_DESCRIPTIONS.keys())
    for col in columns_to_convert:
        if col in df.columns:
              df[col] = pd.to_numeric(df[col], errors='coerce') # Coerce errors to NaN
    return df

def normalize_data(df: pd.DataFrame, selected_indicators: List[str]) -> pd.DataFrame:
    """Normalizes selected indicator data using min-max scaling."""
    if not selected_indicators:
        return pd.DataFrame()

    scaler = MinMaxScaler()
    try:
         df[selected_indicators] = scaler.fit_transform(df[selected_indicators])
    except Exception as e:
         st.error(f"An error occurred during normalization: {e}")
         return pd.DataFrame()

    return df

# --- TOPSIS ALGORITHM ---
def topsis(df: pd.DataFrame, selected_indicators: List[str]) -> pd.DataFrame:
    """Applies the TOPSIS algorithm with equal weights."""

    if not selected_indicators:
        return pd.DataFrame()

    if not all(indicator in df.columns for indicator in selected_indicators):
        st.error("One or more selected indicators are not found in the data.")
        return pd.DataFrame()

     # Handle case where all values are NaN (after filtering). Prevents errors.
    if df[selected_indicators].isnull().all().all():
        st.error("All values are missing for the selected indicators")
        return df.assign(topsis_score=np.nan, topsis_rank=np.nan)


    try:
        # Apply equal weights to all selected indicators.
        weights = {indicator: 1 for indicator in selected_indicators}

        # Calculate weighted normalized matrix
        weighted_matrix = df[selected_indicators].mul(list(weights.values()))

        # Determine ideal best and worst
        ideal_best = weighted_matrix.max(axis=0)
        ideal_worst = weighted_matrix.min(axis=0)

        # Euclidean Distance calculation
        distance_to_best = np.sqrt(((weighted_matrix - ideal_best)**2).sum(axis=1))
        distance_to_worst = np.sqrt(((weighted_matrix - ideal_worst)**2).sum(axis=1))

        # Calculate TOPSIS score
        topsis_score = distance_to_worst / (distance_to_best + distance_to_worst)

        # Add score and rank columns
        df = df.assign(topsis_score=topsis_score)
        df = df.assign(topsis_rank=df['topsis_score'].rank(ascending=False, method='dense', pct=True)*100)

    except Exception as e:
         st.error(f"An error occurred during TOPSIS calculation: {e}")
         return df.assign(topsis_score=np.nan, topsis_rank=np.nan)
    return df


# --- DISPLAY RESULTS ---
def display_results(df: pd.DataFrame, selected_indicators: List[str]):
    """Displays the results in a sortable table."""

    if df.empty or 'topsis_rank' not in df.columns:
        st.warning("No results to display. Please select indicators and click Calculate.")
        return

    st.subheader("Environmental Justice Risk Assessment")


    # Ensure that only relevant columns are shown
    columns_to_display = ['GEOID', 'COUNTY', 'StateDesc', 'topsis_score', 'topsis_rank'] + selected_indicators
    columns_to_display = [col for col in columns_to_display if col in df.columns]

    st.dataframe(df[columns_to_display].sort_values(by='topsis_rank', ascending = False).reset_index(drop=True),
                    column_config={
                        "topsis_rank": st.column_config.NumberColumn(
                           "Environmental Justice Risk Percentile",
                            help = "County's percentile rank based on calculated environmental justice risk, higher percentile indicates higher risk",
                            format = "%.2f%%"
                        ),
                        "topsis_score": st.column_config.NumberColumn(
                            "Risk Score",
                             help = "TOPSIS score, higher the score, the more environmental risk",
                            format="%.4f"
                           ),
                        "COUNTY": "County Name",
                        "StateDesc": "State",
                         "GEOID": "County GEOID"
                    },
                    hide_index = True
                )

    # Add export to CSV function
    csv_buffer = io.StringIO()
    df[columns_to_display].to_csv(csv_buffer, index=False)
    st.download_button("Download Results (CSV)", csv_buffer.getvalue(), "eji_analysis_results.csv")


    # Add export to Excel function
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df[columns_to_display].to_excel(writer, sheet_name='EJI Results', index=False)
    st.download_button("Download Results (Excel)", excel_buffer.getvalue(), "eji_analysis_results.xlsx")

# --- MAIN STREAMLIT APP ---
def main():
    st.set_page_config(
        page_title = "CDC Environmental Justice Index Analyzer",
        layout = "wide"
    )
    st.markdown(
        """
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
             background-color: #0071BC;
           }
           [data-testid="stToolbar"]{
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

             div.css-1r46382 e1nz1j5b1 > div {
                 color: black;
             }

          div.css-12oz5v7 e1nz1j5b1 {
               color: #0071BC;
           }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.title("CDC Environmental Justice Index Analyzer")
    st.markdown("A tool for analyzing county-level environmental justice risks based on the CDC Environmental Justice Index.")
    st.markdown("---")

    file_path = st.file_uploader("Upload your EJI data (CSV)", type=['csv'], help = "Upload the CDC Environmental Justice Index Data in CSV format.")
    if file_path is not None:
        df = load_and_preprocess_data(file_path)
        if not df.empty:
            # Create UI
            indicator_names = [name for name in INDICATOR_DESCRIPTIONS if name in df.columns]

             # Filter out columns with all NaN values before displaying for selection
            available_indicators = [
                indicator for indicator in indicator_names
                if not df[indicator].isnull().all()
            ]

            # Pre-select indicators based on analysis above
            default_indicators = ['SPL_EBM_THEME2','SPL_SVM_DOM2', 'F_HVM', 'EPL_PM', 'EPL_DSLPM', 'EPL_TOTCR','EPL_UNEMP', 'EPL_MINRTY']
            default_indicators = [indicator for indicator in default_indicators if indicator in available_indicators ]
            selected_indicators_names = [INDICATOR_DESCRIPTIONS.get(name, name) for name in available_indicators]
            selected_indicators_ui = st.multiselect("Select EJI Indicators",
                                                options=selected_indicators_names,
                                                default=[INDICATOR_DESCRIPTIONS.get(name, name) for name in default_indicators],
                                                help = "Select indicators to rank by"
                                                )

            selected_indicators = [name for name, desc in INDICATOR_DESCRIPTIONS.items() if desc in selected_indicators_ui]

            if st.button("Calculate", help = "Click to compute the environmental justice scores"):
                with st.spinner("Running Analysis..."):
                    normalized_df = normalize_data(df.copy(), selected_indicators)
                    topsis_df = topsis(normalized_df, selected_indicators)
                    display_results(topsis_df, selected_indicators)

            st.markdown("---")
            st.markdown("""
            **Methodology:**
            This tool utilizes the Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS)
            to rank counties based on environmental justice risks. Each indicator is min-max normalized, equally weighted, then combined to calculate a final risk score. The final rank is
             presented in percentiles.

            **Disclaimer:** This tool provides an estimated environmental risk based on user-defined inputs and weighting.
              The results should be used as part of a comprehensive analysis and may not reflect the exact conditions in
             every county.
            """)

if __name__ == "__main__":
    main()