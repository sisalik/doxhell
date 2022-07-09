import pytest

from doxhell.decorators import satisfies


@satisfies("REQ-001")
def test_1():
    """Test 1."""
    assert True


@satisfies("REQ-002", "REQ-003")
def test_2():
    """Test 2."""
    pytest.fail("Simulate a failure")


def test_3():
    """Test 3."""
    pytest.fail("Simulate a failure")
