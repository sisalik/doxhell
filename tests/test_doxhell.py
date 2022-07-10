from doxhell.decorators import satisfies


@satisfies("REQ-001")
def test_1():
    """Test 1."""


@satisfies("REQ-002", "REQ-003")
def test_2():
    """Test 2."""


def test_3():
    """Test 3."""
