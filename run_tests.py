import unittest

from test.base import PTCTestSuite


test_suite = PTCTestSuite.build()
runner = unittest.TextTestRunner()
runner.run(test_suite)