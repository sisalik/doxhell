import unittest

from doxhell import verifies

from advanced_project.calculator import multiply_numbers


# doxhell supports pytest-style test functions
@verifies("REQ-001")
def test_1():
    """Test 1."""
    assert multiply_numbers(1, 2) == 2


# unittest-style test methods are also supported
class TestAdvancedProject(unittest.TestCase):
    @verifies("REQ-011")
    @verifies("REQ-021")  # @verifies can be applied multiple times
    def test_2(self):
        """Test 2."""
        self.assertEqual(multiply_numbers(-10.0, -0.5), 5.0)

    def test_3(self):
        """Test 3."""
        with self.assertRaises(ValueError):
            multiply_numbers(1, "2")
