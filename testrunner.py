#!/usr/bin/env python
# -*- coding: utf-8 -*-
from unittest import TestLoader, TextTestRunner
from potcommuntests import Tests

runner = TextTestRunner()

testsSuite = TestLoader().loadTestsFromTestCase(Tests)
#testsSuite = TestLoader().loadTestsFromName("potcommuntests.Tests.test_with_some_missing_items")
runner.run(testsSuite)

