import pytest
from doxhell import verifies

from advanced_project.calculator import multiply_numbers


@verifies("REQ-001")
def test_1():
    """Test 1."""
    assert multiply_numbers(1, 2) == 2


@verifies("REQ-011")
@verifies("REQ-021")
def test_2():
    """Test 2."""
    assert multiply_numbers(-10.0, -0.5) == 5.0


def test_3():
    """Test 3."""
    with pytest.raises(ValueError):
        multiply_numbers(1, "2")
