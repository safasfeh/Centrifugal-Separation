import streamlit as st
import pandas as pd
import numpy as np

# Constants
rho_air = 1.2  # kg/m³
mu_air = 1.8e-5  # Pa.s
g = 9.81  # m/s²
error_rate = 0.07  # 7% misclassification

st.title("Centrifugal Separation Device Simulator")

# Input: Particle Diameter
dp = st.number_input("Particle Diameter (micrometer)", min_value=1, value=1000) / 1e6  # convert to meters

# Input: Total Feed Weight
total_weight = st.number_input("Total Feed Weight (g)", min_value=1, value=500) / 1000  # convert to kg

# Components Input
st.subheader("Feed Components")
components = []
num_components = st.number_input("Number of Components", min_value=1, value=4, step=1)

for i in range(num_components):
    col1, col2, col3 = st.columns(3)
    with col1:
        density = st.number_input(f"Component {i+1} Density (kg/m³)", min_value=500, value=1500 + i*500)
    with col2:
        assay = st.number_input(f"Component {i+1} Assay (%)", min_value=0.0, max_value=100.0, value=25.0)
    components.append({"density": density, "assay": assay})

# Calculation
results = []
vt_list = []

for comp in components:
    rho_p = comp["density"]
    
    # Initial guess for Vt
    Vt = 0.01  # m/s
    for _ in range(100):
        Re_p = (rho_air * Vt * dp) / mu_air
        Cd = (24 / Re_p) * (1 + 0.15 * Re_p**0.687) if Re_p <= 1000 else 0.44
        Vt_new = np.sqrt((4 * (rho_p - rho_air) * g * dp) / (3 * Cd * rho_air))
        if abs(Vt_new - Vt) < 1e-6:
            break
        Vt = Vt_new
    
    flow_regime = "Laminar" if Re_p < 1000 else "Turbulent"
    results.append({
        "Density (kg/m³)": rho_p,
        "Assay (%)": comp["assay"],
        "Reynolds Number": round(Re_p, 3),
        "Drag Coefficient (Cd)": round(Cd, 3),
        "Terminal Velocity (Vt, m/s)": round(Vt, 3),
        "Flow Regime": flow_regime
    })
    vt_list.append(Vt)

# Minimum Air Velocity (10% above lowest Vt)
Vmin = min(vt_list) * 1.1

# Separation Time Estimation (simple model)
separator_height = 1.0  # meter (assumed device height)
separation_times = [round(separator_height / vt, 2) for vt in vt_list]

# Display Results
df = pd.DataFrame(results)
df["Separation Time (s)"] = separation_times
st.subheader("Component Calculations")
st.dataframe(df)

st.write(f"### Minimum Air Velocity (Vmin): {round(Vmin, 3)} m/s")

# Tank Distribution (with 7% error)
sorted_components = sorted(components, key=lambda x: x["density"], reverse=True)

tank_distribution = {
    "Tank 1 (Heaviest)": [],
    "Tank 2 (Medium)": [],
    "Tank 3 (Lightest)": []
}

# Ideal placement
tank_distribution["Tank 1 (Heaviest)"].append(sorted_components[0])
tank_distribution["Tank 2 (Medium)"].append(sorted_components[1])
tank_distribution["Tank 2 (Medium)"].append(sorted_components[2])
tank_distribution["Tank 3 (Lightest)"].append(sorted_components[3])

# Error adjustment (misplacement)
misplaced = []
if len(sorted_components) > 2:
    misplaced.append({"density": sorted_components[1]["density"], "assay": sorted_components[1]["assay"] * error_rate})
    misplaced.append({"density": sorted_components[2]["density"], "assay": sorted_components[2]["assay"] * error_rate})
    tank_distribution["Tank 3 (Lightest)"].extend(misplaced)

# Tank Results
st.subheader("Tank Composition (after Separation)")

for tank, comps in tank_distribution.items():
    st.write(f"#### {tank}")
    total_tank_weight = 0
    table_data = []
    for comp in comps:
        comp_weight = (comp["assay"] / 100) * total_weight
        table_data.append({
            "Density (kg/m³)": comp["density"],
            "Assay (%)": round(comp["assay"], 2),
            "Weight in Tank (kg)": round(comp_weight, 3)
        })
        total_tank_weight += comp_weight
    
    tank_df = pd.DataFrame(table_data)
    st.dataframe(tank_df)
    st.write(f"**Total Weight in {tank}: {round(total_tank_weight, 3)} kg**")

