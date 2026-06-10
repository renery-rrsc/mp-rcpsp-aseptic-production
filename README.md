# mp-rcpsp-aseptic-production (Maintenance Planning Resource-Constrained Project Scheduling Problem)

This repository contains the project developed for a master's academic article in Computational Modeling of Systems.

The work proposes a hybrid metaheuristic algorithm that combines:
- Teaching-Learning Based Optimization (TLBO)
- Greedy Randomized Adaptive Search Procedure (GRASP)
- Serial Schedule Generation Scheme (SSGS)

The algorithm is applied to a multi-objective combinatorial optimization problem in the context of maintenance scheduling for an aseptic production line of filled cartridges.

## Problem Description

The optimization problem is mathematically modeled as a Resource-Constrained Project Scheduling Problem (RCPSP). The objective is to minimize:

1. Total production downtime caused by maintenance activities
2. Variance in technician workload

The application scenario assumes a production line with multiple machines and limited spatial capacity, requiring careful scheduling of maintenance tasks under resource constraints.

## Approach

The proposed hybrid solution integrates:

- **ITLBO**: to guide the population-based learning process and explore the search space.
- **GRASP**: to construct randomized greedy solutions and improve diversification by local search.
- **SSGS**: to build feasible schedules that respect resource, skill and capacity constraints while generating a serial schedule.

This hybridization aims to balance exploration and exploitation while producing robust schedules for a multi-objective maintenance planning problem.

## Project Structure

- `structure.py`: Core implementation scripts for the optimizer and scheduling logic.
- `requirements.txt`: Python dependencies for the project.
- `data/`: Input data for three scenarios - light preventive schedule, hard preventive schedule, medium preventive schedule w/ corrective orders.

## Usage

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Run the main optimization script or relevant experiments.

```bash
python structure.py
```

> Adjust the script invocation depending on the selected dataset or experimental setup.

## Academic Context

This repository supports a master's degree article in Computational Modeling of Systems. It focuses on optimizing maintenance scheduling in pharmaceutical manufacturing, specifically the aseptic production of filled cartridges however it could be generalized to any RCPSP.

## Notes

- The project emphasizes a hybrid metaheuristic approach suitable for multi-objective RCPSP problems.
- The implementation is intended for academic research analysis and further industrial deployment.
