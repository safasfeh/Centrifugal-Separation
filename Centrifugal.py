import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from io import BytesIO

st.set_page_config(page_title="Centrifugal Separation Simulator", layout="wide")
# Centered TTU Logo and Header Info
st.image("ttu_logo.png", width=400)
st.markdown("""
    <div style='text-align: center;'>
        <h3 style='color: blue;'>Tafila Technical University</h3>
        <h4 style='color: blue;'>Natural Resources and Chemical Engineering Department</h4>
        <p><strong>Bachelor's Degree Project</strong></p>
    </div>
""", unsafe_allow_html=True)

# Project Info Box
st.markdown("""
    <div style='border: 2px solid #ddd; padding: 15px; border-radius: 10px; margin-top: 10px;'>
        <h2 style='text-align: center;'>Centrifugal Separation Device Simulator</h2>
        
        Ahmad Al-Khalayleh
        Mohammad Al-Khalayleh
        Hebatullh Abuabboud
        Doaa Al-Shoha
        Supervisor:Dr. Ashraf Alsafasfeh
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
# Step 1: Sort by density
sorted_results = sorted(results, key=lambda x: x["Density (kg/m3)"], reverse=True)
n = len(sorted_results)
group_size = n // 3
remainder = n % 3

# Step 2: Assign ideal tank groupings
ideal_tanks = {}
for idx, comp in enumerate(sorted_results):
    if idx < group_size + (1 if remainder > 0 else 0):
        ideal_tanks[comp["Name"]] = "Tank 1"
    elif idx < 2 * group_size + (1 if remainder > 1 else 0):
        ideal_tanks[comp["Name"]] = "Tank 2"
    else:
        ideal_tanks[comp["Name"]] = "Tank 3"

# Step 3: Apply separation logic with 7% error
tanks = {"Tank 1": [], "Tank 2": [], "Tank 3": []}

tank_order = ["Tank 1", "Tank 2", "Tank 3"]
for comp in results:
    ideal_tank = ideal_tanks[comp["Name"]]
    ideal_index = tank_order.index(ideal_tank)

    rand_val = np.random.rand()
    if rand_val < 0.93:
        assigned_tank = ideal_tank
    else:
        # Error shift: move to adjacent tank
        if ideal_index == 0:
            assigned_tank = "Tank 2"
        elif ideal_index == 2:
            assigned_tank = "Tank 2"
        else:
            assigned_tank = np.random.choice(["Tank 1", "Tank 3"])
    tanks[assigned_tank].append(comp)

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
# Sankey Diagram
st.subheader("Separation Sankey Diagram")

# Use component names from the results
labels = [comp["Name"] for comp in results] + ["Tank 1", "Tank 2", "Tank 3"]
source = []
target = []
values = []
hovertexts = []

# Build the flows from components to tanks
for i, comp in enumerate(results):
    for j, tank_name in enumerate(["Tank 1", "Tank 2", "Tank 3"]):
        # Check if this component is in the tank
        for c in tanks[tank_name]:
            if c["Name"] == comp["Name"]:
                source.append(i)
                target.append(len(results) + j)
                values.append(c["Weight (g)"])
                hovertexts.append(f"{c['Name']} to {tank_name}: {c['Weight (g)']:.2f} g")

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
