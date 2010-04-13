#!/usr/bin/env python
from unittest import TestLoader, TextTestRunner
from potcommuntests import Tests

runner = TextTestRunner()

testsSuite = TestLoader().loadTestsFromTestCase(Tests)
runner.run(testsSuite)

