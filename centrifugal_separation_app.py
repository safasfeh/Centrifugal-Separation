
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# Functions for physics calculations
def reynolds_number(density_air, velocity, diameter, viscosity):
    return (density_air * velocity * diameter) / viscosity

def drag_coefficient(Re):
    if Re == 0:
        return np.inf
    elif Re < 0.5:
        return 24 / Re
    elif Re < 1000:
        return 24 / Re * (1 + 0.15 * Re**0.687)
    else:
        return 0.44

def terminal_velocity(d_p, rho_p, rho_air, mu_air, g=9.81):
    Vt_guess = 0.01
    for _ in range(100):
        Re = reynolds_number(rho_air, Vt_guess, d_p, mu_air)
        Cd = drag_coefficient(Re)
        Vt_new = np.sqrt((4 * (rho_p - rho_air) * g * d_p) / (3 * rho_air * Cd))
        if abs(Vt_new - Vt_guess) < 1e-6:
            break
        Vt_guess = Vt_new
    return Vt_guess

def minimum_air_velocity(Vt):
    return 1.2 * Vt  # Empirical safety factor

# Updated tank assignment logic
def assign_to_tanks(densities, assay_percentages, error_rate=0.07):
    sorted_data = sorted(zip(densities, assay_percentages), key=lambda x: -x[0])
    n = len(sorted_data)

    tanks = {1: {}, 2: {}, 3: {}}

    clusters = []
    threshold = 0.15  # 15% relative difference

    current_cluster = [sorted_data[0]]
    for i in range(1, n):
        if abs(sorted_data[i][0] - current_cluster[-1][0]) / current_cluster[-1][0] < threshold:
            current_cluster.append(sorted_data[i])
        else:
            clusters.append(current_cluster)
            current_cluster = [sorted_data[i]]
    clusters.append(current_cluster)

    for idx, cluster in enumerate(clusters):
        tank_id = idx + 1
        for density, assay in cluster:
            tanks[tank_id][density] = assay

    for tank_id in [1, 2]:
        for density, assay in list(tanks[tank_id].items()):
            misplaced = assay * error_rate
            tanks[tank_id][density] -= misplaced
            if tank_id + 1 <= 3:
                tanks[tank_id + 1][density] = tanks[tank_id + 1].get(density, 0) + misplaced

    for tank_id in [3, 2]:
        for density, assay in list(tanks[tank_id].items()):
            misplaced = assay * error_rate
            tanks[tank_id][density] -= misplaced
            if tank_id - 1 >= 1:
                tanks[tank_id - 1][density] = tanks[tank_id - 1].get(density, 0) + misplaced

    for tank_id in tanks:
        total = sum(tanks[tank_id].values())
        if total > 0:
            for density in tanks[tank_id]:
                tanks[tank_id][density] = (tanks[tank_id][density] / total) * 100

    return tanks

# Streamlit app
st.title("Centrifugal Separation Device Simulation")

with st.expander("Feed Components"):
    feed_data = []
    num_components = st.number_input("Number of Components", min_value=1, value=4)
    for i in range(num_components):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input(f"Component {i+1} Name", value=f"Comp{i+1}")
        with col2:
            density = st.number_input(f"Density of {name} (kg/m³)", min_value=0.0, value=2500.0 + i*500)
        with col3:
            assay = st.number_input(f"Assay % of {name}", min_value=0.0, max_value=100.0, value=25.0)
        feed_data.append((name, density, assay))

d_p = st.number_input("Particle Diameter (micrometer)", min_value=0.0, value=1000.0) * 1e-6
rho_air = 1.2  # kg/m³
mu_air = 1.8e-5  # Pa.s (kg/m.s)

st.divider()

# Calculation section
results = []
densities = [d[1] for d in feed_data]
assays = [d[2] for d in feed_data]

for name, rho_p, assay in feed_data:
    Vt = terminal_velocity(d_p, rho_p, rho_air, mu_air)
    Vmin = minimum_air_velocity(Vt)
    Re = reynolds_number(rho_air, Vt, d_p, mu_air)
    Cd = drag_coefficient(Re)
    results.append({
        'Component': name,
        'Density': rho_p,
        'Assay (%)': assay,
        'Terminal Velocity (m/s)': Vt,
        'Min Air Velocity (m/s)': Vmin,
        'Reynolds Number': Re,
        'Drag Coefficient': Cd
    })

df_results = pd.DataFrame(results)
st.subheader("Component Calculations")
st.dataframe(df_results.style.format({"Terminal Velocity (m/s)": "{:.4f}", "Min Air Velocity (m/s)": "{:.4f}", "Reynolds Number": "{:.2f}", "Drag Coefficient": "{:.2f}"}))

# Calculate Tank Compositions
tanks = assign_to_tanks(densities, assays)

st.subheader("Tank Compositions After Separation")
cols = st.columns(3)
for i, col in enumerate(cols, start=1):
    tank_data = [{"Component": comp, "Assay (%)": assay} for comp, assay in sorted(tanks[i].items(), key=lambda x: -x[1])]
    df_tank = pd.DataFrame(tank_data)
    col.markdown(f"### Tank {i}")
    col.dataframe(df_tank.style.format({"Assay (%)": "{:.2f}"}))

# Sankey Diagram
st.subheader("Separation Sankey Diagram")
labels = [d[0] for d in feed_data] + ["Tank 1", "Tank 2", "Tank 3"]
source = []
target = []
values = []
hovertexts = []

for i, d in enumerate(feed_data):
    for t in range(1, 4):
        assay_in_tank = tanks[t].get(d[1], 0)
        if assay_in_tank > 0:
            source.append(i)
            target.append(len(feed_data) + t - 1)
            values.append(assay_in_tank)
            hovertexts.append(f"{d[0]} to Tank {t}: {assay_in_tank:.2f}%")

fig = go.Figure(go.Sankey(
    node=dict(
        pad=15,
        thickness=20,
        line=dict(color="black", width=0.5),
        label=labels,
    ),
    link=dict(
        source=source,
        target=target,
        value=values,
        customdata=hovertexts,
        hovertemplate="%{customdata}<extra></extra>",
    )
))

st.plotly_chart(fig, use_container_width=True)
