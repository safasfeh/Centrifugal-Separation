import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Centrifugal Separation Simulator", layout="wide")
# Centered TTU Logo and Header Info
st.image("ttu_logo.png", width=800)
st.markdown("""
    <div style='text-align: center;'>
        <h3 style='color: green;'>Tafila Technical University</h3>
        <h4 style='color: green;'>Natural Resources and Chemical Engineering Department</h4>
        <p><strong>Bachelor's Degree Project</strong></p>
    </div>
""", unsafe_allow_html=True)

# Project Info Box
st.markdown("""
    <div style='border: 2px solid #ddd; padding: 15px; border-radius: 10px; margin-top: 10px;'>
        <h2 style='text-align: center;'>Modeling Coagulation–Flocculation with Artificial Neural Networks</h2>
        <h4 style='text-align: center;'>Operation Parameters Prediction</h4>
        <br>
        <p><strong>Students:</strong><br>
        Shahad Mohammed Abushamma<br>
        Rahaf Ramzi Al -shakh Qasem<br>
        Duaa Musa Al-Khalafat</p>
        <p><strong>Supervisor:</strong> Dr. Ashraf Alsafasfeh</p>
    </div>
""", unsafe_allow_html=True)

st.title("Centrifugal Separation Device Simulator")

# Constants
rho_air = 1.225  # kg/m3
mu_air = 1.81e-5  # Pa.s (kg/m.s)
g = 9.81  # m/s2

# Helper functions
def reynolds_number(rho_p, d_p, V):
    return (rho_air * V * d_p) / mu_air

def drag_coefficient(Re_p):
    if Re_p < 0.1:
        return 24 / Re_p
    elif Re_p < 1000:
        return 24 / Re_p * (1 + 0.15 * Re_p**0.687)
    else:
        return 0.44

def terminal_velocity(rho_p, d_p):
    Re_guess = 0.1
    error = 1e-5
    for _ in range(100):
        Cd = drag_coefficient(Re_guess)
        Vt = np.sqrt((4 * g * d_p * (rho_p - rho_air)) / (3 * Cd * rho_air))
        Re_new = reynolds_number(rho_p, d_p, Vt)
        if abs(Re_new - Re_guess) < error:
            break
        Re_guess = Re_new
    return Vt, Re_new, Cd

# Input Section
st.sidebar.header("Feed Components")
components = []

num_components = st.sidebar.number_input("Number of Components", min_value=1, max_value=10, value=4)

for i in range(num_components):
    st.sidebar.subheader(f"Component {i+1}")
    name = st.sidebar.text_input(f"Name {i+1}", value=f"Component {i+1}")
    density = st.sidebar.number_input(f"Density (kg/m3) {i+1}", min_value=500, max_value=10000, value=2500, step=50)
    assay = st.sidebar.number_input(f"Assay (%) {i+1}", min_value=0.0, max_value=100.0, value=25.0, step=1.0)
    components.append({"Name": name, "Density": density, "Assay (%)": assay})

particle_diameter = st.sidebar.number_input("Particle Diameter (μm)", min_value=10, max_value=5000, value=1000, step=10) / 1e6
total_feed_weight = st.sidebar.number_input("Total Feed Weight (g)", min_value=10, max_value=5000, value=500, step=10)

# Compute Separation Results
results = []
for comp in components:
    weight = total_feed_weight * (comp["Assay (%)"] / 100)
    Vt, Re_p, Cd = terminal_velocity(comp["Density"], particle_diameter)
    results.append({
        "Name": comp["Name"],
        "Density (kg/m3)": comp["Density"],
        "Assay (%)": comp["Assay (%)"],
        "Weight (g)": weight,
        "Vt (m/s)": Vt,
        "Re_p": Re_p,
        "Cd": Cd
    })

results_df = pd.DataFrame(results)

st.subheader("Calculated Separation Parameters")
st.dataframe(results_df)

# Minimum Air Velocity for Tank 1 & 2
sorted_results = sorted(results, key=lambda x: x["Density (kg/m3)"], reverse=True)
Vmin_tank1 = sorted_results[0]["Vt (m/s)"] * 1.1  # 10% safety margin
Vmin_tank2 = sorted_results[2]["Vt (m/s)"] * 1.1  # next cutoff

st.subheader("Minimum Air Velocity (Vmin)")
st.write(f"Tank 1 Vmin: {Vmin_tank1:.4f} m/s")
st.write(f"Tank 2 Vmin: {Vmin_tank2:.4f} m/s")

# Separation Logic with ~7% error overlap
tanks = {"Tank 1": [], "Tank 2": [], "Tank 3": []}

for comp in results:
    rand_val = np.random.rand()
    if comp["Density (kg/m3)"] >= sorted_results[1]["Density (kg/m3)"]:
        if rand_val < 0.93:
            tanks["Tank 1"].append(comp)
        else:
            tanks["Tank 2"].append(comp)
    elif comp["Density (kg/m3)"] >= sorted_results[2]["Density (kg/m3)"]:
        if rand_val < 0.93:
            tanks["Tank 2"].append(comp)
        else:
            tanks["Tank 3"].append(comp)
    else:
        tanks["Tank 3"].append(comp)

# Final Assay Calculation
tank_tables = {}
for tank_name, comps in tanks.items():
    total_weight = sum([c["Weight (g)"] for c in comps])
    table = []
    for c in comps:
        assay = (c["Weight (g)"] / total_weight * 100) if total_weight else 0
        table.append({
            "Name": c["Name"],
            "Weight (g)": c["Weight (g)"],
            "Final Assay (%)": assay
        })
    tank_tables[tank_name] = pd.DataFrame(table)

# Display Tank Compositions
st.subheader("Tank Compositions after Separation (Final Assay %)")

cols = st.columns(3)
for i, (tank_name, df) in enumerate(tank_tables.items()):
    with cols[i]:
        st.markdown(f"### {tank_name}")
        st.dataframe(df)

# Process Time Estimation (Example)
feed_rate = 50  # grams per minute (adjust as needed)
process_time = total_feed_weight / feed_rate
st.subheader("Estimated Process Time")
st.write(f"Estimated time to finish separation: {process_time:.2f} minutes")

# Sankey Diagram with Hover Tooltips
labels = ["Feed"] + list(tanks.keys())
sources, targets, values, custom_labels = [], [], [], []

for i, (tank_name, comps) in enumerate(tanks.items()):
    tank_weight = sum([c["Weight (g)"] for c in comps])
    sources.append(0)
    targets.append(i + 1)
    values.append(tank_weight)
    tooltip = "<br>".join([f"{c['Name']}: {c['Weight (g)']:.2f} g" for c in comps])
    custom_labels.append(tooltip)

fig = go.Figure(data=[go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
        color=["#636EFA", "#EF553B", "#00CC96", "#AB63FA"]
    ),
    link=dict(
        source=sources,
        target=targets,
        value=values,
        customdata=custom_labels,
        hovertemplate='%{target.label}<br>Total Weight: %{value:.2f} g<br>Components:<br>%{customdata}<extra></extra>',
        color=["rgba(99,110,250,0.6)", "rgba(239,85,59,0.6)", "rgba(0,204,150,0.6)"]
    ))])

st.subheader("Separation Flow Visualization (Sankey Diagram)")
st.plotly_chart(fig, use_container_width=True)

# CSV Export of Final Tank Composition
st.subheader("Download Tank Compositions")

def convert_df_to_csv():
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        for tank_name, df in tank_tables.items():
            df.to_excel(writer, sheet_name=tank_name, index=False)
    output.seek(0)
    return output

csv_file = convert_df_to_csv()
st.download_button(label="Download Tank Compositions as Excel", data=csv_file, file_name="tank_compositions.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
