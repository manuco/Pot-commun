# -*- coding: utf-8 -*-

from unittest import TestCase

from datetime import datetime
from potcommun import DebtManager, Item, Payment

class Tests(TestCase):
    def test_void(self):
        self.assertEqual(1, 1)

    def setUp(self):
        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000)
        outlay.addItem(("Alice",), "Starter", 500)
        outlay.addItem(("Alice",), "Course", 2000)
        outlay.addItem(("Bob",), "Course", 2500)
        outlay.addItem(("Bob",), "Wine", 1000)
        outlay.addPayment(("Alice"), 6000)
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000)
        outlay.addItem(("Alice", "Bob"), "ticket", 2000)
        outlay.addPayment(("Bob",), 2000)
        self.mgr = mgr


    def test_simple_example(self):
        """
            Bob and Alice go to a restaurant, and after that to the cinema.
            Alice eats for ¤25 (a starter then a course)
            Bob eats for ¤35 (a course and some wine)
            Alice pays for the restaurant.

            The cinema's fee is ¤10
            Bob pays for it.
        """
        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")

        # When, what, how much, in cents
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000)
        # Who has consummed, what, how much
        outlay.addItem(("Alice",), "Starter", 500)
        outlay.addItem(("Alice",), "Course", 2000)
        outlay.addItem(("Bob",), "Course", 2500)
        outlay.addItem(("Bob",), "Wine", 1000)
        # Who, how much
        outlay.addPayment(("Alice"), 6000)

        outlay = mgr.addOutlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000)
        # Who has consummed, what, how much
        outlay.addItem(("Alice", "Bob"), "ticket", 2000)
        # Who, how much
        outlay.addPayment(("Bob",), 2000)

        # Who owes who how much?
        result = mgr.computeDebts()

        # Bob should pay back ¤25,00.
        expected = (
            ("Bob", 2500, "Alice"),
        )
        self.assertEqual(result, expected)



    def test_mgr(self):
        mgr = DebtManager()
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 5000)
        other = mgr.getOutlay(outlay.getId())



    def test_abstract_payments_totals(self):
        payments = (Payment(("A", "B"), 4), Payment(("A",), 3), Payment(("B",), 5))
        r = Payment.computeTotals(payments)
        self.assertEqual(r, {"A": 5, "B": 7})

    def test_merge_totals(self):
        r = Payment.mergeTotals({"A": 5, "B": 7}, {"A": 5, "C": 3})
        self.assertEqual(r, {"A": 10, "B": 7, "C": 3})



    def test_compute_totals(self):
        r = self.mgr.computeTotals()
        self.assertEqual(r, ({"Alice": 3500, "Bob": 4500},{"Alice": 6000, "Bob": 2000}))

    def test_compute_balances(self):
        r = self.mgr.computeBalances(self.mgr.computeTotals())
        self.assertEqual(r, {"Alice": -2500, "Bob": 2500})

    def test_checkAndAdjustTotals(self):
        r = self.mgr.checkAndAdjustTotals({"A": 4, "B": 3}, {"A": 11})
        self.assertEqual(r, ({"A": 6, "B": 5}, {"A": 11}))

        r = self.mgr.checkAndAdjustTotals({"A": 3}, {"A": 4, "B": 3})
        self.assertEqual(r, ({"A": 5, "B": 2}, {"A": 4, "B": 3}))


    def test_with_missing_info(self):
        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000)
        outlay.addItem(("Alice",), "Starter", 500)
        outlay.addItem(("Alice",), "Course", 2000)
        outlay.addItem(("Bob",), "Course", 2500)
        outlay.addItem(("Bob",), "Wine", 1000)
        outlay.addPayment(("Alice"), 6000)
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000)
        outlay.addPayment(("Bob",), 2000)
        result = mgr.computeDebts()
        expected = (("Bob", 2500, "Alice"),)
        self.assertEqual(result, expected)


    def test_real_example(self):
        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")
        mgr.addPerson("Cesar")
        mgr.addPerson("Daniel")
        mgr.addPerson("Empu")
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000)
        outlay.addItem(("Alice",), "Starter", 500)
        outlay.addItem(("Alice",), "Course", 2000)
        outlay.addItem(("Bob",), "Course", 2500)
        outlay.addItem(("Bob",), "Wine", 1000)
        outlay.addPayment(("Alice"), 6000)
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000)
        outlay.addItem(("Alice", "Bob"), "ticket", 2000)
        outlay.addPayment(("Bob",), 2000)

        ### TBC
