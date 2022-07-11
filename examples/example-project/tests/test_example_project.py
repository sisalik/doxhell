import pytest
from doxhell.decorators import verifies

from example_project.calculator import add_numbers


@verifies("REQ-001")
def test_1():
    """Test 1."""
    assert add_numbers(1, 2) == 3


@verifies("REQ-011", "REQ-021")
def test_2():
    """Test 2."""
    assert add_numbers(-10.5, -5.5) == -16.0


def test_3():
    """Test 3."""
    with pytest.raises(ValueError):
        add_numbers(1, "2")
