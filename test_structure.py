import pytest
import pandas as pd
import numpy as np
import math

from structure import Operation, load_operations, SSGS, GRASPConstructor, GRASPLocalSearch
from structure import TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY

@pytest.fixture
def mock_excel_data(tmp_path):
    df = pd.DataFrame({
        'Task ID': [1, 1, 2],
        'Operation ID': [1, 2, 1],
        'Task Duration': [1.5, 0.5, 2.0],
        'Skills Required': ['Mechanical', 'Electrical', 'Calibration'],
        'Num. Of Workers': [2, 1, 1],
        'Preceding Op': ['', '1', '']
    })

    file_path = tmp_path / "mock_data.xlsx"
    with pd.ExcelWriter(file_path) as writer:
        df.to_excel(writer, sheet_name='RRU', index=False)

    return file_path

@pytest.fixture
def sample_operations():
    op1 = Operation(machine='RRU', task_id=1, op_id=1, duration_hrs=1.5, skill='Mechanical', n_workers=2, predecessors_str='')
    op2 = Operation(machine='RRU', task_id=1, op_id=2, duration_hrs=0.5, skill='Electrical', n_workers=1, predecessors_str='1')
    op3 = Operation(machine='HQL', task_id=2, op_id=1, duration_hrs=2.0, skill='Calibration', n_workers=1, predecessors_str='')
    return [op1, op2, op3]

# ====================================
# TEST OPERATION
# ====================================

def test_operation_initialization():
    op = Operation(
        machine='RRU',
        task_id='1',
        op_id='2',
        duration_hrs=1.5,
        skill='Mechanical',
        n_workers='2',
        predecessors_str='1, 3'
    )

    assert op.machine == 'RRU'
    assert op.task_id == 1
    assert op.op_id == 2
    assert op.duration == 90  # 1.5 * 60
    assert op.skill == 'Mechanical'
    assert op.n_workers == 2
    assert op.predecessors_str == [1, 3]
    assert op.start_time is None
    assert op.end_time is None

def test_operation_parse_predecessors():
    op_empty1 = Operation('M1', 1, 1, 1, 'S1', 1, '')
    assert op_empty1.predecessors_str == []

    op_empty2 = Operation('M1', 1, 1, 1, 'S1', 1, np.nan)
    assert op_empty2.predecessors_str == []

    op_single = Operation('M1', 1, 1, 1, 'S1', 1, '1')
    assert op_single.predecessors_str == [1]

    op_multiple = Operation('M1', 1, 1, 1, 'S1', 1, '1; 2, 3')
    assert op_multiple.predecessors_str == [1, 2, 3]

# ====================================
# TEST LOAD OPERATIONS
# ====================================

def test_load_operations(mock_excel_data):
    operations = load_operations(mock_excel_data, 'RRU')

    assert len(operations) == 3

    assert operations[0].machine == 'RRU'
    assert operations[0].task_id == 1
    assert operations[0].op_id == 1
    assert operations[0].duration == 90
    assert operations[0].skill == 'Mechanical'
    assert operations[0].n_workers == 2
    assert operations[0].predecessors_str == []

    assert operations[1].predecessors_str == [1]

# ====================================
# TEST SSGS
# ====================================

def test_ssgs_initialization(sample_operations):
    ssgs = SSGS(sample_operations, TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY)
    assert len(ssgs.operations) == 3
    assert ssgs.tech_limits == TECHNICIANS_AVAILABLE
    assert ssgs.machine_limits == MACHINE_SPATIAL_CAPACITY
    assert len(ssgs.op_dict) == 3
    assert ssgs.tech_usage == {skill: 0 for skill in TECHNICIANS_AVAILABLE}

def test_ssgs_check_predecessors_finished(sample_operations):
    ssgs = SSGS(sample_operations, TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY)
    op1, op2, op3 = sample_operations

    # op1 has no predecessors
    assert ssgs._check_predecessors_finished(op1, 0) == True

    # op2 depends on op1, which hasn't finished
    assert ssgs._check_predecessors_finished(op2, 0) == False

    # op1 finishes at time 90
    op1.end_time = 90
    assert ssgs._check_predecessors_finished(op2, 89) == False
    assert ssgs._check_predecessors_finished(op2, 90) == True

def test_ssgs_check_resources_availability(sample_operations):
    # Use limited resources to test constraints
    tech_limits = {'Mechanical': 2, 'Electrical': 1, 'Calibration': 1, 'Lubrication': 1}
    machine_limits = {'RRU': 3, 'HQL': 2}

    ssgs = SSGS(sample_operations, tech_limits, machine_limits)
    op1, op2, op3 = sample_operations

    # op1 needs 2 Mechanical and 2 space on RRU
    assert ssgs._check_resources_availability(op1, 0) == True

    # Simulate op1 starting
    op1.start_time = 0
    op1.end_time = 90

    # op1 taking all Mechanical techs, a new Mechanical op would fail
    op_mech_extra = Operation('RRU', 1, 3, 1, 'Mechanical', 1, '')
    assert ssgs._check_resources_availability(op_mech_extra, 0) == False

    # op2 needs 1 Electrical and 1 space on RRU. RRU has 1 space left (3-2).
    assert ssgs._check_resources_availability(op2, 0) == True

    # Simulate op2 starting
    op2.start_time = 0
    op2.end_time = 30

    # RRU is now full (op1 takes 2, op2 takes 1, max is 3)
    op_elec_extra = Operation('RRU', 1, 4, 1, 'Electrical', 1, '')
    assert ssgs._check_resources_availability(op_elec_extra, 0) == False

    # Resources free up after operations finish
    assert ssgs._check_resources_availability(op_elec_extra, 90) == True

def test_ssgs_build_schedule(sample_operations):
    ssgs = SSGS(sample_operations, TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY)

    # Schedule operations in order: op1 -> op2 -> op3
    makespan, plv = ssgs.build_schedule(sample_operations)

    op1, op2, op3 = sample_operations

    # Check start and end times
    assert op1.start_time == 0
    assert op1.end_time == 90

    assert op2.start_time == 90 # Waits for op1
    assert op2.end_time == 120

    assert op3.start_time == 0 # No dependencies, starts immediately
    assert op3.end_time == 120

    assert makespan == 120
    assert plv >= 0

# ====================================
# TEST GRASP
# ====================================

def test_grasp_constructor(sample_operations):
    constructor = GRASPConstructor(sample_operations, alpha=0.3)
    priority_list = constructor.generate_priority_list()

    assert len(priority_list) == 3

    # op2 depends on op1, so op1 must appear before op2
    idx1 = priority_list.index(sample_operations[0])
    idx2 = priority_list.index(sample_operations[1])
    assert idx1 < idx2

def test_grasp_local_search_is_valid_swap(sample_operations):
    ssgs = SSGS(sample_operations, TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY)
    local_search = GRASPLocalSearch(ssgs)

    op1, op2, op3 = sample_operations

    # Valid swap: op1 and op3 have no dependencies between them
    assert local_search._is_valid_swap(op1, op3) == True

    # Invalid swap: op1 is a predecessor of op2 (they have same task_id=1, op1 is 1, op2 is 2)
    assert local_search._is_valid_swap(op1, op2) == False

    # Valid swap: op2 placed before op3 (no dependencies)
    assert local_search._is_valid_swap(op2, op3) == True

def test_grasp_local_search_optimize(sample_operations):
    ssgs = SSGS(sample_operations, TECHNICIANS_AVAILABLE, MACHINE_SPATIAL_CAPACITY)
    local_search = GRASPLocalSearch(ssgs)

    op1, op2, op3 = sample_operations
    initial_list = [op1, op2, op3]
    initial_makespan, initial_plv = ssgs.build_schedule(initial_list)

    best_list, best_makespan, best_plv = local_search.optimize(initial_list, initial_makespan, initial_plv)

    assert len(best_list) == 3
    assert best_makespan <= initial_makespan
    if best_makespan == initial_makespan:
        assert best_plv <= initial_plv
