import sys
import unittest

from test.base import PTCTestSuite


def run_tests():
    test_suite = PTCTestSuite.build_from(sys.argv)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(test_suite)

if __name__ == '__main__':
    run_tests()
