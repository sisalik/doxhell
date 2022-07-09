from doxhell.decorators import satisfies


@satisfies("REQ-001")
def test_1():
    assert True


@satisfies("REQ-002", "REQ-003")
def test_2():
    assert False


def test_3():
    assert None
