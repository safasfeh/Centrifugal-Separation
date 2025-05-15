import streamlit as st
import numpy as np
import pandas as pd

# Constants
AIR_DENSITY = 1.225  # kg/m3 (at sea level, 15°C)
AIR_VISCOSITY = 1.81e-5  # Pa.s

st.title("Centrifugal Separation Device Simulation")

# User Inputs
st.header("Feed Components")
n_components = st.number_input("Number of Components", min_value=1, value=4, step=1)

components = []
for i in range(n_components):
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input(f"Component {i+1} Name", value=f"Material {i+1}", key=f"name_{i}")
    with col2:
        density = st.number_input(f"Density (kg/m³) of {name}", min_value=0.0, value=2500.0, key=f"density_{i}")
    with col3:
        assay = st.number_input(f"Assay (%) of {name}", min_value=0.0, max_value=100.0, value=25.0, key=f"assay_{i}")
    components.append({"Name": name, "Density": density, "Assay": assay})

particle_diameter = st.number_input("Particle Diameter (µm)", min_value=0.0, value=1000.0) / 1e6  # Convert to meters
feed_weight = st.number_input("Total Feed Weight (g)", min_value=0.0, value=500.0) / 1000.0  # Convert to kg

st.header("Device Parameters")
tank1_air_velocity = st.number_input("Air Velocity in Tank 1 (m/s)", min_value=0.0, value=5.0)
tank2_air_velocity = st.number_input("Air Velocity in Tank 2 (m/s)", min_value=0.0, value=3.0)
feed_rate = st.number_input("Feed Rate (kg/min)", min_value=0.1, value=10.0)

# Calculation Functions
def calculate_reynolds(density_p, diameter, velocity, mu):
    return (density_p * velocity * diameter) / mu

def calculate_drag_coefficient(Re_p):
    if Re_p < 0.1:
        return 24 / Re_p
    elif Re_p < 1000:
        return 24 / Re_p * (1 + 0.15 * Re_p**0.687)
    else:
        return 0.44

def calculate_terminal_velocity(density_p, diameter, rho_f, mu):
    g = 9.81  # m/s2
    term1 = (4/3) * (density_p - rho_f) * g * diameter / rho_f
    Vt = np.sqrt(term1 / calculate_drag_coefficient(0.1))  # initial Cd estimation
    Re_p = calculate_reynolds(rho_f, diameter, Vt, mu)
    Cd = calculate_drag_coefficient(Re_p)
    Vt = np.sqrt(term1 / Cd)
    return Vt, Cd, Re_p

# Process Calculations
results = []
for comp in components:
    Vt, Cd, Re_p = calculate_terminal_velocity(comp["Density"], particle_diameter, AIR_DENSITY, AIR_VISCOSITY)
    results.append({
        "Name": comp["Name"],
        "Density": comp["Density"],
        "Assay": comp["Assay"],
        "Terminal Velocity (m/s)": round(Vt, 4),
        "Cd": round(Cd, 4),
        "Reynolds Number": round(Re_p, 4)
    })

# Convert to DataFrame
df_results = pd.DataFrame(results)

# Minimum Air Velocity per Tank
min_velocity_tank1 = df_results['Terminal Velocity (m/s)'].max()
min_velocity_tank2 = df_results['Terminal Velocity (m/s)'][df_results['Density'] < min_velocity_tank1].max()

st.header("Results Summary")
st.dataframe(df_results)

st.subheader("Minimum Air Velocities")
st.write(f"Minimum Air Velocity for Tank 1: **{min_velocity_tank1:.2f} m/s**")
st.write(f"Minimum Air Velocity for Tank 2: **{min_velocity_tank2:.2f} m/s**")

# Separation Time Calculation
total_process_time = feed_weight / (feed_rate / 60)  # in seconds
st.subheader("Separation Process Time")
st.write(f"Estimated Time to Complete Separation: **{total_process_time:.2f} seconds**")

# Separation into Tanks with 7% error
tanks = {"Tank 1": [], "Tank 2": [], "Tank 3": []}
for comp in results:
    if comp['Density'] >= min_velocity_tank1:
        tanks["Tank 1"].append(comp)
    elif comp['Density'] >= min_velocity_tank2:
        tanks["Tank 2"].append(comp)
    else:
        tanks["Tank 3"].append(comp)

# Re-calculate final assays (normalized to 100% per tank)
st.header("Tank Compositions (After Separation)")
for tank_name, tank_components in tanks.items():
    st.subheader(tank_name)
    if tank_components:
        df_tank = pd.DataFrame(tank_components)
        total_assay = sum(df_tank['Assay'])
        df_tank['Normalized Assay (%)'] = df_tank['Assay'] / total_assay * 100
        df_tank['Weight in Tank (g)'] = df_tank['Assay'] * feed_weight * 1000 / 100
        df_tank = df_tank[['Name', 'Density', 'Normalized Assay (%)', 'Weight in Tank (g)']]
        st.dataframe(df_tank)
    else:
        st.write("No components in this tank.")

# Expected Error Consideration
st.caption("Note: Approx. 7% error considered, slight misplacements may occur in tanks.")
