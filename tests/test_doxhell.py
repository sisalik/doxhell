from doxhell.decorators import verifies


@verifies("REQ-001")
def test_1():
    """Test 1."""


@verifies("REQ-011", "REQ-021")
def test_2():
    """Test 2."""


def test_3():
    """Test 3."""
