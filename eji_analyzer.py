import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from config import INDICATOR_DESCRIPTIONS

st.set_page_config(page_title="CDC Environmental Justice Index State Explorer", layout="wide")

st.markdown("""<style>h1,h2,h3{color:#0071BC}.stDownloadButton>button{background-color:#0071BC;color:white;border:none;padding:.5em 1em;cursor:pointer}.stDownloadButton>button:hover{background-color:#00518f}.streamlit-expanderHeader{background-color:#f0f2f6;border-radius:5px}div[data-testid="stCheckbox"]{padding:2px 0}.stSidebar [data-testid="stMarkdownContainer"]{font-size:14px}</style>""", unsafe_allow_html=True)

OVERALL_INDICES = {
    "RPL_EJI": "Overall Environmental Justice Index",
    "RPL_SER": "Social and Environmental Risk Index"
}

EJI_VARIABLE_GROUPS = {
    "Environmental Burden (EBM)": {
        "Air Quality": {"EPL_OZONE": "Ozone Level", "EPL_PM": "Particulate Matter (PM2.5)", "EPL_DSLPM": "Diesel Particulate Matter", "EPL_TOTCR": "Air Toxics Cancer Risk"},
        "Proximity to Risk Sites": {"EPL_NPL": "Proximity to Superfund Sites", "EPL_TRI": "Proximity to Toxic Release Sites", "EPL_RMP": "Proximity to Risk Management Facilities", "EPL_TSDF": "Proximity to Treatment/Storage/Disposal Facilities"},
        "Built Environment": {"EPL_PARK": "Access to Green Space", "EPL_HOUAGE": "Lead Paint Indicators (Pre-1960s Housing)", "EPL_WLKIND": "Walkability Index"}
    },
    "Social Vulnerability (SVM)": {
        "Demographic Indicators": {"EPL_MINRTY": "Minority Population", "EPL_AGE65": "Population 65 and Older", "EPL_AGE17": "Population 17 and Younger"},
        "Socioeconomic Indicators": {"EPL_POV200": "Population Below 200% Poverty Level", "EPL_UNEMP": "Unemployment Rate", "EPL_NOHSDP": "No High School Diploma"},
        "Housing and Infrastructure": {"EPL_RENTER": "Renter-Occupied Housing", "EPL_MOBILE": "Mobile Homes", "EPL_NOINT": "No Internet Access"}
    },
    "Health Vulnerability (HVM)": {
        "Health Conditions": {"EPL_ASTHMA": "Asthma Rate", "EPL_CANCER": "Cancer Rate", "EPL_BPHIGH": "High Blood Pressure", "EPL_DIABETES": "Diabetes Rate", "EPL_MHLTH": "Poor Mental Health"}
    }
}

def get_all_variables():
    all_vars = {}
    for g_content in EJI_VARIABLE_GROUPS.values():
        if isinstance(g_content, dict):
            for s_content in g_content.values():
                if isinstance(s_content, dict): all_vars.update(s_content)
                else: all_vars.update({k: v for k, v in g_content.items() if not isinstance(v, dict)})
        else: all_vars[g_content] = g_content
    return all_vars

@st.cache_data
def load_data():
    df = pd.read_csv('data/CDC_EJI_US.csv').replace(-999, np.nan)
    numeric_cols = [col for col in df.columns if col.startswith(('E_', 'EP_', 'EPL_', 'SPL_', 'RPL_', 'F_'))]
    for col in numeric_cols: df[col] = pd.to_numeric(df[col], errors='coerce')
    df['county_id'] = df['StateDesc'] + '_' + df['COUNTY']
    return df.groupby(['county_id', 'COUNTY', 'StateDesc'], as_index=False)[numeric_cols].mean()

def render_variable_selector():
    st.sidebar.header("Select Variables to Display")
    selected_vars = {'COUNTY': 'County'}
    
    # Add overall indices by default
    selected_vars.update(OVERALL_INDICES)
    
    if st.sidebar.checkbox("Select All Variables", False): 
        return {**selected_vars, **get_all_variables()}
    
    for group_name, group_content in EJI_VARIABLE_GROUPS.items():
        with st.sidebar.expander(f"📊 {group_name}", False):
            if isinstance(group_content, dict):
                for subgroup_name, variables in group_content.items():
                    st.markdown(f"**🔍 {subgroup_name}**")
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
                        elif st.checkbox(variables, key=subgroup_name):
                            selected_vars[subgroup_name] = variables
            elif st.checkbox(group_content, key=group_name):
                selected_vars[group_name] = group_content
        st.sidebar.markdown("---")
    
    # Create summary of selected variables
    default_vars = list(OVERALL_INDICES.values())
    additional_vars = [v for k, v in selected_vars.items() 
                      if k not in ['COUNTY'] + list(OVERALL_INDICES.keys())]
    
    summary_md = """<div style='padding:10px;background-color:#f0f2f6;border-radius:5px'>
        <p style='margin:0;font-weight:bold'>Selected Variables:</p>
        <p style='margin:5px 0;font-size:0.9em;opacity:0.8'>Default indices (always shown):</p>
        <ul style='margin:0;padding-left:20px;font-size:0.9em'>"""
    
    for var in default_vars:
        summary_md += f"<li>{var}</li>"
    
    if additional_vars:
        summary_md += """</ul>
        <p style='margin:5px 0;font-size:0.9em;opacity:0.8'>Additional selected:</p>
        <ul style='margin:0;padding-left:20px;font-size:0.9em'>"""
        for var in additional_vars:
            summary_md += f"<li>{var}</li>"
    
    summary_md += "</ul></div>"
    
    st.sidebar.markdown(summary_md, unsafe_allow_html=True)
    return selected_vars

df = load_data()
st.title("CDC Environmental Justice Index State Explorer")
st.markdown("Explore county-level environmental justice indicators across states.")
selected_state = st.selectbox("Select a State", sorted(df['StateDesc'].unique()))
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
                display_df[col] = (pd.to_numeric(display_df[col], errors='coerce') * 100).round(1)
        
        column_config = {"County": st.column_config.TextColumn("County", width="medium")}
        column_config.update({col: st.column_config.ProgressColumn(col, help=INDICATOR_DESCRIPTIONS.get(next(k for k, v in selected_vars.items() if v == col), ""), format="%d%%", min_value=0, max_value=100) for col in display_df.columns if col != 'County'})
        
        st.dataframe(display_df.sort_values(next(iter(display_df.columns)), ascending=False), column_config=column_config, hide_index=True, use_container_width=True)
    
    with tab2:
        selected_counties = st.multiselect("Select counties to compare (max 10)", options=sorted(state_data['COUNTY'].unique()), default=[state_data['COUNTY'].iloc[0]], max_selections=10)
        
        if selected_counties:
            comparison_df = display_df[display_df['County'].isin(selected_counties)]
            
            if 'Overall Environmental Justice Index' in comparison_df.columns:
                st.subheader("Key Metrics")
                cols = st.columns(len(selected_counties))
                for idx, county in enumerate(selected_counties):
                    with cols[idx]:
                        st.metric(f"{county} County", f"{comparison_df[comparison_df['County'] == county]['Overall Environmental Justice Index'].iloc[0]:.1f}%")
            
            st.subheader("Comparative Analysis")
            comparison_long = comparison_df.melt(id_vars=['County'], var_name='Indicator', value_name='Percentile')
            chart = alt.Chart(comparison_long).mark_bar().encode(
                y=alt.Y('County:N', title=None, axis=alt.Axis(labelLimit=200, labelAngle=0)),
                x=alt.X('Percentile:Q', title='Risk Level (percentile)', scale=alt.Scale(domain=[0, 100])),
                color=alt.Color('County:N', legend=alt.Legend(title="Selected Areas", orient="top", columns=3)),
                row=alt.Row('Indicator:N', title=None, header=alt.Header(labelAngle=0, labelAlign='left', labelLimit=300)),
                tooltip=['County', 'Indicator', alt.Tooltip('Percentile:Q', title='Risk Level', format='.1f')]
            ).properties(width=700, height=max(40, min(80, 400/len(selected_counties))))
            
            st.altair_chart(chart)
            st.download_button("Download Comparison Data (CSV)", comparison_df.to_csv(index=False), f"{selected_state}_county_comparison.csv", "text/csv")
    
    st.markdown("---\n**Methodology Notes:**\n- All percentile values range from 0-100, where higher values indicate greater potential for environmental justice concerns\n- The Overall EJ Index combines environmental, social, and health vulnerability indicators\n- Counties with \"N/A\" values lack sufficient data for that indicator")
else:
    st.warning("Please select at least one variable to display from the sidebar.")