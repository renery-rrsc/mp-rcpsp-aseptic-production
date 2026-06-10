import pytest
import pandas as pd
import numpy as np
from structure import Operation

@pytest.fixture
def dummy_op():
    # Instantiate with dummy values.
    # Passing an empty string for predecessors_str to avoid errors during init.
    return Operation("M1", 1, 1, 1.0, "Skill", 1, "")

def test_parse_predecessors_empty_strings(dummy_op):
    assert dummy_op._parse_predecessors("") == []
    assert dummy_op._parse_predecessors("   ") == []

def test_parse_predecessors_missing_values(dummy_op):
    assert dummy_op._parse_predecessors(None) == []
    assert dummy_op._parse_predecessors(pd.NA) == []
    assert dummy_op._parse_predecessors(np.nan) == []
    assert dummy_op._parse_predecessors("nan") == []

def test_parse_predecessors_integers(dummy_op):
    assert dummy_op._parse_predecessors(1) == [1]

def test_parse_predecessors_valid_lists(dummy_op):
    assert dummy_op._parse_predecessors("1, 2, 3") == [1, 2, 3]
    assert dummy_op._parse_predecessors("1; 2; 3") == [1, 2, 3]
    assert dummy_op._parse_predecessors("1, 2; 3") == [1, 2, 3]

def test_parse_predecessors_invalid_parts(dummy_op):
    # 'a' and '2.5' are not digits, so they should be filtered out
    assert dummy_op._parse_predecessors("1; a; 2") == [1, 2]
    assert dummy_op._parse_predecessors("1; 2.5; 3") == [1, 3]
