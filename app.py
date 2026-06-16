import streamlit as st
import plotly.express as px
import pandas as pd
from datetime import datetime, timedelta
from structure import load_all_operations, Hybrid_ITLBO_GRASP

# Set page config
st.set_page_config(layout="wide", page_title="Maintenance Schedule Optimizer")

st.title("Maintenance Schedule Optimizer Gantt Chart")

# Sidebar for parameters
st.sidebar.header("Optimization Parameters")
pop_size = st.sidebar.number_input("Population Size", min_value=1, max_value=100, value=2, step=1)
max_generations = st.sidebar.number_input("Max Generations", min_value=1, max_value=200, value=2, step=10)
alpha = st.sidebar.slider("GRASP Alpha", min_value=0.0, max_value=1.0, value=0.3, step=0.1)

# Run button
if st.button("Run Optimization"):
    with st.spinner("Running Optimization... This may take a while."):
        try:
            # Load data
            operations = load_all_operations('data/Case 1.xlsx', ['RRU', 'HQL', 'ITP', 'ISS', 'TLU'])

            # Run optimizer
            optimizer = Hybrid_ITLBO_GRASP(operations, pop_size=pop_size, max_generations=max_generations, alpha=alpha)
            best_makespan, best_plv, best_schedule, history = optimizer.optimize()

            st.success(f"Optimization Complete! Makespan: {best_makespan:.0f} mins | PLV: {best_plv:.2f}")

            if not best_schedule:
                st.warning("No schedule generated.")
            else:
                # Transform data for Plotly
                base_date = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0)

                df_data = []
                for entry in best_schedule:
                    op = entry['operation']
                    start_min = entry['start']
                    finish_min = entry['finish']

                    start_time = base_date + timedelta(minutes=start_min)
                    finish_time = base_date + timedelta(minutes=finish_min)

                    df_data.append({
                        "Task": f"Task {op.task_id}",
                        "Operation": f"Op {op.op_id}",
                        "Machine": op.machine,
                        "Start": start_time,
                        "Finish": finish_time,
                        "Duration (mins)": finish_min - start_min,
                        "Technicians": ", ".join(entry['technicians']) if entry['technicians'] else "None",
                        "Task_Op": f"T{op.task_id}-O{op.op_id}"
                    })

                df = pd.DataFrame(df_data)

                # Create Gantt chart using Plotly Express
                fig = px.timeline(
                    df,
                    x_start="Start",
                    x_end="Finish",
                    y="Machine",
                    color="Task",
                    hover_data=["Task_Op", "Duration (mins)", "Technicians"],
                    title="Interactive Dynamic Gantt Chart"
                )

                # Ensure machines are displayed logically and separated
                fig.update_yaxes(categoryorder="total ascending")

                # Make it scrollable and dynamic
                num_machines = len(df["Machine"].unique())
                fig.update_layout(
                    height=max(400, num_machines * 100), # Dynamic height
                    xaxis_title="Time",
                    yaxis_title="Machines",
                    margin=dict(l=20, r=20, t=50, b=20)
                )

                # Display the chart
                st.plotly_chart(fig, use_container_width=True)

        except Exception as e:
            st.error(f"Error during optimization: {e}")
