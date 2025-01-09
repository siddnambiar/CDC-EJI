import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from config import INDICATOR_DESCRIPTIONS

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

def get_all_variables():
    all_vars = {}
    for group_content in EJI_VARIABLE_GROUPS.values():
        if isinstance(group_content, dict):
            for subgroup_content in group_content.values():
                if isinstance(subgroup_content, dict):
                    all_vars.update(subgroup_content)
                else:
                    if isinstance(group_content, dict):
                        all_vars.update({k: v for k, v in group_content.items() 
                                      if not isinstance(v, dict)})
        else:
            if not isinstance(group_content, dict):
                all_vars[group_content] = group_content
    return all_vars

@st.cache_data
def load_data():
    df = pd.read_csv('data/CDC_EJI_US.csv')
    df = df.replace(-999, np.nan)
    
    numeric_columns = [col for col, desc in INDICATOR_DESCRIPTIONS.items() 
                      if col in df.columns and col.startswith(('E_', 'EP_', 'EPL_', 'SPL_', 'RPL_', 'F_'))]
    
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df['county_id'] = df['StateDesc'] + '_' + df['COUNTY']
    
    groupby_cols = ['county_id', 'COUNTY', 'StateDesc']
    
    agg_cols = [col for col in numeric_columns if col in df.columns]
    
    agg_dict = {col: 'mean' for col in agg_cols}
    
    county_df = df.groupby(groupby_cols, as_index=False)[agg_cols].agg(agg_dict)
    
    return county_df

def render_variable_selector():
    st.sidebar.header("Select Variables to Display")
    
    selected_vars = {'COUNTY': 'County'}
    
    if st.sidebar.checkbox("Select All Variables", False):
        selected_vars.update(get_all_variables())
    else:
        for group_name, group_content in EJI_VARIABLE_GROUPS.items():
            st.sidebar.subheader(group_name)
            
            if isinstance(group_content, dict):
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

df = load_data()

st.title("CDC Environmental Justice Index State Explorer")
st.markdown("Explore county-level environmental justice indicators across states.")

states = sorted(df['StateDesc'].unique())
selected_state = st.selectbox("Select a State", states)

selected_vars = render_variable_selector()

state_data = df[df['StateDesc'] == selected_state].copy()

available_vars = {k: v for k, v in selected_vars.items() if k in state_data.columns}

if len(available_vars) > 1:
    tab1, tab2 = st.tabs(["📊 All Counties Overview", "🔍 County Comparison"])
    
    with tab1:
        display_df = state_data[list(available_vars.keys())].copy()
        display_df.columns = list(available_vars.values())
        
        for col in display_df.columns:
            if col != 'County' and col in display_df.columns:
                display_df[col] = pd.to_numeric(display_df[col], errors='coerce') * 100
                display_df[col] = display_df[col].round(1)
        
        column_config = {
            "County": st.column_config.TextColumn(
                "County",
                width="medium"
            )
        }
        
        for col in display_df.columns:
            if col != 'County':
                column_config[col] = st.column_config.ProgressColumn(
                    col,
                    help=INDICATOR_DESCRIPTIONS.get(
                        next(k for k, v in selected_vars.items() if v == col), 
                        ""
                    ),
                    format="%d%%",
                    min_value=0,
                    max_value=100,
                )
        
        st.dataframe(
            display_df.sort_values(next(iter(display_df.columns)), ascending=False),
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )
    
    with tab2:
        selected_counties = st.multiselect(
            "Select counties to compare (max 10)",
            options=sorted(state_data['COUNTY'].unique()),
            default=[state_data['COUNTY'].iloc[0]],
            max_selections=10,
            help="Compare environmental justice indicators across different counties to understand relative risk levels"
        )
        
        if selected_counties:
            comparison_df = display_df[display_df['County'].isin(selected_counties)]
            
            if 'Overall Environmental Justice Index' in comparison_df.columns:
                st.subheader("Key Metrics")
                cols = st.columns(len(selected_counties))
                for idx, county in enumerate(selected_counties):
                    county_data = comparison_df[comparison_df['County'] == county]
                    with cols[idx]:
                        st.metric(
                            f"{county} County",
                            f"{county_data['Overall Environmental Justice Index'].iloc[0]:.1f}%",
                            help="Overall Environmental Justice Index Percentile"
                        )
            
            st.subheader("Comparative Analysis")
            
            comparison_long = comparison_df.melt(
                id_vars=['County'],
                var_name='Indicator',
                value_name='Percentile'
            )
            
            # Calculate dynamic height based on number of counties
            bar_height = max(40, min(80, 400 / len(selected_counties)))
            
            chart = alt.Chart(comparison_long).mark_bar().encode(
                y=alt.Y('County:N', 
                       title=None,  # Removed 'County' label
                       axis=alt.Axis(labelLimit=200, labelAngle=0)),
                x=alt.X('Percentile:Q', 
                       title='Risk Level (percentile)', 
                       scale=alt.Scale(domain=[0, 100])),
                color=alt.Color('County:N', 
                              legend=alt.Legend(
                                  title="Selected Areas",
                                  orient="top",
                                  columns=3
                              )),
                row=alt.Row('Indicator:N', 
                          title=None,
                          header=alt.Header(labelAngle=0, labelAlign='left', labelLimit=300)),
                tooltip=['County', 'Indicator', 
                        alt.Tooltip('Percentile:Q', 
                                  title='Risk Level', 
                                  format='.1f')]
            ).properties(
                width=700,
                height=bar_height
            )
            
            st.altair_chart(chart)
            
            csv = comparison_df.to_csv(index=False)
            st.download_button(
                label="Download Comparison Data (CSV)",
                data=csv,
                file_name=f"{selected_state}_county_comparison.csv",
                mime="text/csv"
            )
    
    st.markdown("---")
    st.markdown("""
    **Methodology Notes:**
    - All percentile values range from 0-100, where higher values indicate greater potential for environmental justice concerns
    - The Overall EJ Index combines environmental, social, and health vulnerability indicators
    - Counties with "N/A" values lack sufficient data for that indicator
    """)
else:
    st.warning("Please select at least one variable to display from the sidebar.")