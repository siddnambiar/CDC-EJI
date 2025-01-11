import streamlit as st
import pandas as pd
import altair as alt
import numpy as np
import matplotlib.pyplot as plt
import geopandas as gpd
import json
import os
from config import INDICATOR_DESCRIPTIONS

st.set_page_config(page_title="CDC Environmental Justice Index Tract Explorer", layout="wide")

# Enhanced CSS with improved spacing and hierarchy
st.markdown("""
<style>
    h1,h2,h3 { color: #0071BC }
    .stDownloadButton>button {
        background-color: #0071BC;
        color: white;
        border: none;
        padding: .5em 1em;
        cursor: pointer;
    }
    .stDownloadButton>button:hover { background-color: #00518f }
    .streamlit-expanderHeader {
        background-color: #f0f2f6;
        border-radius: 5px;
        margin-top: 0.5rem;
    }
    div[data-testid="stCheckbox"] { 
        padding: 4px 0;
    }
    .stSidebar [data-testid="stMarkdownContainer"] { font-size: 14px }
    .sidebar-category {
        background-color: #f8f9fa;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
        border-left: 4px solid #0071BC;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 16px;
        background-color: #f0f2f6;
        border-radius: 4px;
    }
    .stTabs [data-baseweb="tab-active"] {
        background-color: #0071BC;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

OVERALL_INDICES = {
    "RPL_EJI": "Overall Environmental Justice Index",
    "RPL_SER": "Social and Environmental Risk Index"
}

EJI_VARIABLE_GROUPS = {
    "Environmental Burden (EBM)": {
        "Air Quality": {
            "EPL_OZONE": "Ozone Level", 
            "EPL_PM": "Particulate Matter (PM2.5)", 
            "EPL_DSLPM": "Diesel Particulate Matter", 
            "EPL_TOTCR": "Air Toxics Cancer Risk"
        },
        "Proximity to Risk Sites": {
            "EPL_NPL": "Proximity to Superfund Sites", 
            "EPL_TRI": "Proximity to Toxic Release Sites", 
            "EPL_RMP": "Proximity to Risk Management Facilities", 
            "EPL_TSDF": "Proximity to Treatment/Storage/Disposal Facilities"
        },
        "Built Environment": {
            "EPL_PARK": "Access to Green Space", 
            "EPL_HOUAGE": "Lead Paint Indicators (Pre-1960s Housing)", 
            "EPL_WLKIND": "Walkability Index"
        }
    },
    "Social Vulnerability (SVM)": {
        "Demographic Indicators": {
            "EPL_MINRTY": "Minority Population", 
            "EPL_AGE65": "Population 65 and Older", 
            "EPL_AGE17": "Population 17 and Younger"
        },
        "Socioeconomic Indicators": {
            "EPL_POV200": "Population Below 200% Poverty Level", 
            "EPL_UNEMP": "Unemployment Rate", 
            "EPL_NOHSDP": "No High School Diploma"
        },
        "Housing and Infrastructure": {
            "EPL_RENTER": "Renter-Occupied Housing", 
            "EPL_MOBILE": "Mobile Homes", 
            "EPL_NOINT": "No Internet Access"
        }
    },
    "Health Vulnerability (HVM)": {
        "Health Conditions": {
            "EPL_ASTHMA": "Asthma Rate", 
            "EPL_CANCER": "Cancer Rate", 
            "EPL_BPHIGH": "High Blood Pressure", 
            "EPL_DIABETES": "Diabetes Rate", 
            "EPL_MHLTH": "Poor Mental Health"
        }
    }
}

@st.cache_data
def load_data():
    df = pd.read_csv('data/CDC_EJI_US.csv').replace(-999, np.nan)
    numeric_cols = [col for col in df.columns if col.startswith(('E_', 'EP_', 'EPL_', 'SPL_', 'RPL_', 'F_'))]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df['GEOID'] = df['AFFGEOID'].str[-11:]
    return df

@st.cache_data
def load_and_preprocess_geojson(state_fips):
    try:
        state_dir = f"data/tracts/state_{str(state_fips).zfill(2)}"
        if not os.path.exists(state_dir):
            st.error(f"No boundary data available for this state (FIPS code {state_fips})")
            return None
            
        shapefile = [f for f in os.listdir(state_dir) if f.endswith('.shp')]
        if not shapefile:
            st.error(f"No shapefile found in {state_dir}")
            return None
        shapefile = shapefile[0]
        gdf = gpd.read_file(os.path.join(state_dir, shapefile))
        gdf['id'] = gdf['GEOID']
        return gdf

    except Exception as e:
        st.error(f"Error loading and processing tract boundaries: {str(e)}")
        return None

def get_all_variables():
    all_vars = {}
    for g_content in EJI_VARIABLE_GROUPS.values():
        if isinstance(g_content, dict):
            for s_content in g_content.values():
                if isinstance(s_content, dict): 
                    all_vars.update(s_content)
                else: 
                    all_vars.update({k: v for k, v in g_content.items() if not isinstance(v, dict)})
        else: 
            all_vars[g_content] = g_content
    return all_vars

def create_tract_map(data, var_code, var_name, gdf):
    if gdf is None:
        return None
    
    if not data[var_code].notna().any():
        st.error("No data available to plot for selected variable")
        return None
    
    merged_data = gdf.merge(data, left_on='GEOID', right_on='GEOID')
    
    fig, ax = plt.subplots(1, 1, figsize=(2.5, 1.5))  # Reduced figure size
    merged_data.plot(column=var_code, cmap='YlOrRd', linewidth=0.1, ax=ax, edgecolor='0.8', vmin=0, vmax=1, legend=True)
    ax.set_title(f"{var_name}", fontsize=10)
    ax.set_axis_off()
    
    plt.tight_layout()
    return fig

def render_variable_selector():
    st.sidebar.header("Select Variables to Display")
    selected_vars = {'AFFGEOID': 'Census Tract ID', 'Location': 'Location'}
    selected_vars.update(OVERALL_INDICES)
    
    if st.sidebar.checkbox("Select All Variables", False):
        return {**selected_vars, **get_all_variables()}
    
    for group_name, group_content in EJI_VARIABLE_GROUPS.items():
        with st.sidebar.expander(f"📊 {group_name}", False):
            st.markdown(f'<div class="sidebar-category">', unsafe_allow_html=True)
            if isinstance(group_content, dict):
                for subgroup_name, variables in group_content.items():
                    st.markdown(f"**{subgroup_name}**")
                    cols = st.columns(2)
                    with cols[0]:
                        if isinstance(variables, dict):
                            for var_code, var_name in list(variables.items())[::2]:
                                if st.checkbox(var_name, key=var_code):
                                    selected_vars[var_code] = var_name
                    with cols[1]:
                        if isinstance(variables, dict):
                            for var_code, var_name in list(variables.items())[1::2]:
                                if st.checkbox(var_name, key=var_code):
                                    selected_vars[var_code] = var_name
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown("---")
    return selected_vars

def render_map_tab(state_data, selected_map_var, map_var_options, gdf):
    #st.markdown('<div style="height: 2.5vh; overflow: hidden;">', unsafe_allow_html=True)
    with st.container(border=True):
        fig = create_tract_map(state_data, selected_map_var, map_var_options[selected_map_var], gdf)
        if fig is not None:
            st.pyplot(fig)
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown("""
        **Map Legend:**
        - Darker colors indicate higher percentile values
        - Values represent percentiles (0-100)
        """)
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Top 5 Census Tracts")
        top_tracts = state_data.sort_values(selected_map_var, ascending=False).head(5)
        top_tracts = top_tracts[['Location', selected_map_var]].copy()
        top_tracts.columns = ['Location', 'Risk Level (percentile)']
        st.table(top_tracts)
        
    with col2:
        st.markdown("### Bottom 5 Census Tracts")
        bottom_tracts = state_data.sort_values(selected_map_var, ascending=True).head(5)
        bottom_tracts = bottom_tracts[['Location', selected_map_var]].copy()
        bottom_tracts.columns = ['Location', 'Risk Level (percentile)']
        st.table(bottom_tracts)

# Main app
df = load_data()

st.title("CDC Environmental Justice Index Tract Explorer")
st.markdown("Explore census tract-level environmental justice indicators across states.")
st.markdown("The Environmental Justice Index (EJI) is a composite measure that combines environmental, social, and health vulnerability indicators. Higher percentile values indicate a greater potential for environmental injustice.")

# Enhanced state selector with search
state_options = sorted(df['StateDesc'].unique())
selected_state = st.selectbox(
    "Select a State",
    state_options,
    index=0,
    help="Type to search for a state",
    key="state_selector"
)

selected_vars = render_variable_selector()

state_data = df[df['StateDesc'] == selected_state].copy()
available_vars = {k: v for k, v in selected_vars.items() if k in state_data.columns}
gdf = load_and_preprocess_geojson(state_data['STATEFP'].iloc[0])

if len(available_vars) > 1:
    tab1, tab2, tab3 = st.tabs(["🗺️ Census Tract Map", "📊 Data Table", "🔍 Area Comparison"])
    
    with tab1:
        map_var_options = {k: v for k, v in available_vars.items() if k not in ['AFFGEOID', 'Location']}
        selected_map_var = st.selectbox(
            "Select indicator to display on map",
            options=list(map_var_options.keys()),
            format_func=lambda x: map_var_options[x] if map_var_options else None
        )
        render_map_tab(state_data, selected_map_var, map_var_options, gdf)
    
    with tab2:
        st.markdown("### Census Tract Data Table")
        st.markdown("This table displays the percentile ranking for each selected indicator across all census tracts in the chosen state.")
        display_df = state_data[list(available_vars.keys())].copy()
        display_df.columns = list(available_vars.values())
        
        numeric_cols = [col for col in display_df.columns if col not in ['Census Tract ID', 'Location']]
        for col in numeric_cols:
            display_df[col] = (pd.to_numeric(display_df[col], errors='coerce') * 100).round(1)
        
        column_config = {
            "Location": st.column_config.TextColumn("Location", width="medium"),
            "Census Tract ID": st.column_config.TextColumn("Census Tract ID", width="medium")
        }
        column_config.update({
            col: st.column_config.ProgressColumn(
                col,
                help=INDICATOR_DESCRIPTIONS.get(next(k for k, v in selected_vars.items() if v == col), ""),
                format="%d%%",
                min_value=0,
                max_value=100
            ) for col in numeric_cols
        })
        
        st.dataframe(
            display_df.sort_values(numeric_cols[0], ascending=False),
            column_config=column_config,
            hide_index=True,
            use_container_width=True
        )
    
    with tab3:
        st.markdown("### Area Comparison")
        st.markdown("Select up to 10 census tracts to compare their Environmental Justice Index (EJI) and related indicator values.")
        selected_tracts = st.multiselect(
            "Select census tracts to compare (max 10)",
            options=sorted(state_data['Location'].unique()),
            default=[state_data['Location'].iloc[0]] if not state_data.empty else [],
            max_selections=10
        )
        
        if selected_tracts:
            comparison_df = display_df[display_df['Location'].isin(selected_tracts)]
            
            if 'Overall Environmental Justice Index' in comparison_df.columns:
                st.subheader("Key Metrics")
                cols = st.columns(len(selected_tracts))
                for idx, tract in enumerate(selected_tracts):
                    with cols[idx]:
                        value = comparison_df[comparison_df['Location'] == tract]['Overall Environmental Justice Index'].iloc[0]
                        st.metric(f"Tract", f"{value:.1f}%")
                        st.caption(tract)
            
            st.subheader("Comparative Analysis")
            comparison_long = comparison_df.melt(
                id_vars=['Location'],
                value_vars=[col for col in comparison_df.columns if col not in ['Census Tract ID', 'Location']],
                var_name='Indicator',
                value_name='Percentile'
            )
            
            chart = alt.Chart(comparison_long).mark_bar().encode(
                y=alt.Y('Location:N', title=None, axis=alt.Axis(labelLimit=200, labelAngle=0)),
                x=alt.X('Percentile:Q', title='Risk Level (percentile)', scale=alt.Scale(domain=[0, 100])),
                color=alt.Color('Location:N', legend=alt.Legend(title="Selected Areas", orient="top", columns=3)),
                row=alt.Row('Indicator:N', title=None, header=alt.Header(labelAngle=0, labelAlign='left', labelLimit=300)),
                tooltip=['Location', 'Indicator', alt.Tooltip('Percentile:Q', title='Risk Level', format='.1f')]
            ).properties(width=700, height=max(40, min(80, 400/len(selected_tracts))))
            
            st.altair_chart(chart)
            st.download_button(
                "Download Comparison Data (CSV)",
                comparison_df.to_csv(index=False),
                f"{selected_state}_tract_comparison.csv",
                "text/csv"
            )
        else:
            st.warning("Please select census tracts to compare.")
    
    st.markdown("---\n**Methodology Notes:**\n- All percentile values range from 0-100, where higher values indicate greater potential for environmental justice concerns\n- The Overall EJ Index combines environmental, social, and health vulnerability indicators\n- Census tracts with \"N/A\" values lack sufficient data for that indicator")
else:
    st.warning("Please select at least one variable to display from the sidebar.")