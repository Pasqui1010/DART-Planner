import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

from tests.control.temp_test import test_acceleration_matches_desired, test_torque_coriolis_term, controller

def run_tests():
    print("Running tests...")
    c = controller()
    test_acceleration_matches_desired(c)
    test_torque_coriolis_term(c)
    print("Tests passed!")

if __name__ == "__main__":
    run_tests()
