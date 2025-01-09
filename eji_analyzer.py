import streamlit as st
import pandas as pd
import numpy as np
from config import INDICATOR_DESCRIPTIONS

# --- STYLING ---
st.set_page_config(page_title="CDC Environmental Justice Index State Explorer", layout="wide")

st.markdown("""
    <style>
        .main { background-color: #f5f5f5; }
        h1, h2, h3 { color: #0071BC; }
        [data-testid="stSidebar"] { background-color: #e0e0e0; }
        [data-testid="stHeader"] { background-color: transparent; }
        [data-testid="stToolbar"] { display: none; }
        .stDownloadButton > button {
            background-color: #0071BC;
            color: white;
            border: none;
            padding: 0.5em 1em;
            cursor: pointer;
        }
        .stDownloadButton > button:hover { background-color: #00518f; }
    </style>
""", unsafe_allow_html=True)

# --- VARIABLE GROUPINGS ---
EJI_VARIABLE_GROUPS = {
    "Overall Indices": {
        "RPL_EJI": "Overall Environmental Justice Index",
        "RPL_SER": "Social and Environmental Risk Index",
    },
    "Environmental Burden (EBM)": {
        "Air Quality": {
            "EPL_OZONE": "Ozone Level",
            "EPL_PM": "Particulate Matter (PM2.5)",
            "EPL_DSLPM": "Diesel Particulate Matter",
            "EPL_TOTCR": "Air Toxics Cancer Risk",
        },
        "Proximity to Risk Sites": {
            "EPL_NPL": "Proximity to Superfund Sites",
            "EPL_TRI": "Proximity to Toxic Release Sites",
            "EPL_RMP": "Proximity to Risk Management Facilities",
            "EPL_TSDF": "Proximity to Treatment/Storage/Disposal Facilities",
        },
        "Built Environment": {
            "EPL_PARK": "Access to Green Space",
            "EPL_HOUAGE": "Lead Paint Indicators (Pre-1960s Housing)",
            "EPL_WLKIND": "Walkability Index",
        },
    },
    "Social Vulnerability (SVM)": {
        "Demographic Indicators": {
            "EPL_MINRTY": "Minority Population",
            "EPL_AGE65": "Population 65 and Older",
            "EPL_AGE17": "Population 17 and Younger",
        },
        "Socioeconomic Indicators": {
            "EPL_POV200": "Population Below 200% Poverty Level",
            "EPL_UNEMP": "Unemployment Rate",
            "EPL_NOHSDP": "No High School Diploma",
        },
        "Housing and Infrastructure": {
            "EPL_RENTER": "Renter-Occupied Housing",
            "EPL_MOBILE": "Mobile Homes",
            "EPL_NOINT": "No Internet Access",
        },
    },
    "Health Vulnerability (HVM)": {
        "Health Conditions": {
            "EPL_ASTHMA": "Asthma Rate",
            "EPL_CANCER": "Cancer Rate",
            "EPL_BPHIGH": "High Blood Pressure",
            "EPL_DIABETES": "Diabetes Rate",
            "EPL_MHLTH": "Poor Mental Health",
        }
    }
}

# --- DATA LOADING ---
@st.cache_data
def load_data():
    """Load and preprocess the EJI data, aggregating to county level."""
    df = pd.read_csv('data/CDC_EJI_US.csv')
    df = df.replace(-999, np.nan)
    
    # Convert relevant columns to numeric
    numeric_columns = [col for col, desc in INDICATOR_DESCRIPTIONS.items() 
                      if col in df.columns and col.startswith(('E_', 'EP_', 'EPL_', 'SPL_', 'RPL_', 'F_'))]
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create a unique county identifier combining state and county
    df['county_id'] = df['StateDesc'] + '_' + df['COUNTY']
    
    # Group by the unique county identifier
    groupby_cols = ['county_id', 'COUNTY', 'StateDesc']
    
    # Get all numeric columns for aggregation
    agg_cols = [col for col in numeric_columns if col in df.columns]
    
    # Create aggregation dictionary (mean for all numeric columns)
    agg_dict = {col: 'mean' for col in agg_cols}
    
    # Aggregate to county level
    county_df = df.groupby(groupby_cols, as_index=False)[agg_cols].agg(agg_dict)
    
    print(f"Number of rows after aggregation: {len(county_df)}")
    print(f"Number of unique counties: {len(county_df['COUNTY'].unique())}")
    
    return county_df

# --- VARIABLE SELECTION INTERFACE ---
def render_variable_selector():
    """Render the hierarchical variable selection interface."""
    st.sidebar.header("Select Variables to Display")
    
    selected_vars = {'COUNTY': 'County'}  # Always include county
    
    def get_all_variables():
        """Extract all variable codes and names from the nested structure."""
        all_vars = {}
        for group_content in EJI_VARIABLE_GROUPS.values():
            if isinstance(group_content, dict):
                for subgroup_content in group_content.values():
                    if isinstance(subgroup_content, dict):
                        all_vars.update(subgroup_content)
                    else:
                        # Handle any direct key-value pairs in the first level of nesting
                        if isinstance(group_content, dict):
                            all_vars.update({k: v for k, v in group_content.items() 
                                          if not isinstance(v, dict)})
            else:
                # Handle any direct key-value pairs at the top level
                if not isinstance(group_content, dict):
                    all_vars[group_content] = group_content
        return all_vars

    # Add "Select All" option
    if st.sidebar.checkbox("Select All Variables", False):
        selected_vars.update(get_all_variables())
    else:
        # Iterate through main groups
        for group_name, group_content in EJI_VARIABLE_GROUPS.items():
            st.sidebar.subheader(group_name)
            
            if isinstance(group_content, dict):
                # Handle nested subgroups
                for subgroup_name, variables in group_content.items():
                    if isinstance(variables, dict):
                        st.sidebar.markdown(f"**{subgroup_name}**")
                        for var_code, var_name in variables.items():
                            if st.sidebar.checkbox(f"{var_name}", key=var_code):
                                selected_vars[var_code] = var_name
                    else:
                        if st.sidebar.checkbox(f"{variables}", key=subgroup_name):
                            selected_vars[subgroup_name] = variables
            else:
                if st.sidebar.checkbox(f"{group_content}", key=group_name):
                    selected_vars[group_name] = group_content
    
    return selected_vars

# --- MAIN APP ---
try:
    df = load_data()
    
    st.title("CDC Environmental Justice Index State Explorer")
    st.markdown("Explore county-level environmental justice indicators across states.")
    
    # State selection in main area
    states = sorted(df['StateDesc'].unique())
    selected_state = st.selectbox("Select a State", states)
    
    # Variable selection in sidebar
    selected_vars = render_variable_selector()
    
    # Filter data for selected state
    state_data = df[df['StateDesc'] == selected_state].copy()
    print(f"\nNumber of rows for {selected_state}: {len(state_data)}")
    print(f"Number of unique counties in {selected_state}: {len(state_data['COUNTY'].unique())}")
    
    # Additional check for duplicates
    duplicates = state_data.groupby('COUNTY').size()
    if any(duplicates > 1):
        print("\nDuplicate counties found:")
        print(duplicates[duplicates > 1])
    
    # Create display dataframe with selected variables
    available_vars = {k: v for k, v in selected_vars.items() if k in state_data.columns}
    
    if len(available_vars) > 1:  # More than just County
        display_df = state_data[list(available_vars.keys())].copy()
        display_df.columns = list(available_vars.values())
        
        # Convert percentiles from 0-1 to 0-100
        for col in display_df.columns:
            if col != 'County' and col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce') * 100
                display_df[col] = display_df[col].round(1)
        
        # Display summary statistics
        st.subheader(f"Environmental Justice Summary for {selected_state}")
        
        # Display county data table with progress columns
        st.subheader("County-Level Data")
        
        # Create column configs
        column_config = {
            "County": st.column_config.TextColumn(
                "County",
                width="medium"
            )
        }
        
        # Add progress columns for percentile values
        for col in display_df.columns:
            if col != 'County':
                column_config[col] = st.column_config.ProgressColumn(
                    col,
                    help=INDICATOR_DESCRIPTIONS.get(next(k for k, v in selected_vars.items() if v == col), ""),
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                )
        
        # Display the dataframe
        st.dataframe(
            display_df.sort_values(next(iter(display_df.columns)), ascending=False),
            column_config=column_config,
            hide_index=True,
            use_container_width=True
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
        st.warning("Please select at least one variable to display from the sidebar.")

except Exception as e:
    st.error(f"Error loading data: {str(e)}")
    st.info("Please ensure the CDC EJI data file is located at 'data/CDC_EJI_US.csv'")