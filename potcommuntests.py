# -*- coding: utf-8 -*-

from unittest import TestCase

from datetime import datetime
from potcommun import Handler, DebtManager, Item, Payment, Outlay, Person

class Tests(TestCase):
    def test_void(self):
        self.assertEqual(1, 1)

    def setUp(self):
        self.saveHandler = Handler()

        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "Starter", 500))
        outlay.addItem(Item(("Alice",), "Course", 2000))
        outlay.addItem(Item(("Bob",), "Course", 2500))
        outlay.addItem(Item(("Bob",), "Wine", 1000))
        outlay.addPayment(Payment(("Alice",), 6000))
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice", "Bob"), "ticket", 2000))
        outlay.addPayment(Payment(("Bob",), 2000))
        self.mgr = mgr

    def test_add_person_as_string_raise(self):
        """
            A person should be inserted as a Person, not as a String.
        """
        mgr = DebtManager()
        self.assertRaises(Exception, mgr.addPerson, "Alice")


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
        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        # Who has consummed, what, how much
        outlay.addItem(Item(("Alice",), "Starter", 500))
        outlay.addItem(Item(("Alice",), "Course", 2000))
        outlay.addItem(Item(("Bob",), "Course", 2500))
        outlay.addItem(Item(("Bob",), "Wine", 1000))
        # Who, how much
        outlay.addPayment(Payment(("Alice",), 6000))

        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        # Who has consummed, what, how much
        outlay.addItem(Item(("Alice", "Bob"), "ticket", 2000))
        # Who, how much
        outlay.addPayment(Payment(("Bob",), 2000))

        # Who owes who how much?
        result = mgr.computeDebts()

        # Bob should pay back ¤25,00.
        expected = (
            ("Bob", 2500, "Alice"),
        )
        self.assertEqual(result, expected)


    def test_abstract_payments_totals(self):
        payments = (Payment(("A", "B"), 4), Payment(("A",), 3), Payment(("B",), 5))
        r = Payment.computeTotals(payments)
        self.assertEqual(r, {"A": 5, "B": 7})

    def test_merge_totals(self):
        r = Payment.mergeTotals({"A": 5, "B": 7}, {"A": 5, "C": 3})
        self.assertEqual(r, {"A": 10, "B": 7, "C": 3})

    def test_compute_totals(self):
        r = self.mgr.computeTotals()
        self.assertEqual(r, ({"Alice": 3500, "Bob": 4500}, {"Alice": 6000, "Bob": 2000}))

    def test_compute_balances(self):
        r = self.mgr.computeBalances()
        self.assertEqual(r, {"Alice": -2500, "Bob": 2500})

    def test_checkAndAdjustTotals(self):
        r = self.mgr.checkAndAdjustTotals(("A", "B"), {"A": 4, "B": 3}, {"A": 11})
        self.assertEqual(r, ({"A": 6, "B": 5}, {"A": 11, "B": 0}))

        r = self.mgr.checkAndAdjustTotals(("A", "B"), {"A": 3}, {"A": 4, "B": 3})
        self.assertEqual(r, ({"A": 5, "B": 2}, {"A": 4, "B": 3}))

        r = self.mgr.checkAndAdjustTotals(("A", "B"), {"A": 4}, {})
        self.assertEqual(r, ({"A": 4, "B": 0}, {"A": 2, "B": 2}))

        r = self.mgr.checkAndAdjustTotals(("A", "B"), {}, {"A": 4})
        self.assertEqual(r, ({"A": 2, "B": 2}, {"A": 4, "B": 0}))


    def test_with_missing_info(self):
        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPayment(Payment(("Bob",), 2000))
        outlay.addPersons(("Alice",))
        result = mgr.computeDebts()
        expected = (("Alice", 1000, "Bob"),)
        self.assertEqual(result, expected)

    def test_void_operation(self):
        mgr = DebtManager()
        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        mgr.addPerson("Alice")
        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T1")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1))

        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        mgr.addPerson("Bob")
        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T2")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1))
        outlay.addItem(Item(("Bob",), "B", 1))

        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T3")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1))
        outlay.addItem(Item(("Bob",), "B", 1))
        outlay.addPayment(Payment(("Alice", "Bob"), 2))

        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T4")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1))
        outlay.addPayment(Payment(("Bob",), 1))

        result = mgr.computeDebts()
        expected = (("Alice", 1, "Bob"), )
        self.assertEqual(result, expected)


    def test_real_example(self):
        mgr = DebtManager()
        mgr.addPerson("Alice")
        mgr.addPerson("Bob")
        mgr.addPerson("Cesar")
        mgr.addPerson("Daniel")
        mgr.addPerson("Empu")

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T1")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1500))
        outlay.addItem(Item(("Bob",), "B", 1700))
        outlay.addItem(Item(("Cesar",), "C", 1600))
        outlay.addItem(Item(("Daniel",), "D", 1500))
        outlay.addItem(Item(("Empu",), "E", 1000))
        outlay.addItem(Item(("Alice", "Bob", "Cesar", "Daniel"), "F", 2000))
        outlay.addPayment(Payment(("Alice",), 9300))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T2")
        mgr.addOutlay(outlay)
        outlay.addPersons(("Alice", "Bob", "Cesar", "Daniel", "Empu"))
        outlay.addPayment(Payment(("Bob",), 7500))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T3")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1000))
        outlay.addItem(Item(("Bob",), "B", 700))
        outlay.addItem(Item(("Cesar",), "C", 900))
        outlay.addPayment(Payment(("Cesar",), 2600))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T4")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 700))
        outlay.addItem(Item(("Bob",), "B", 700))
        outlay.addItem(Item(("Daniel",), "D", 700))
        outlay.addItem(Item(("Empu",), "E", 700))
        outlay.addPayment(Payment(("Daniel",), 2800))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T5")
        mgr.addOutlay(outlay)
        outlay.addItem(Item(("Alice",), "A", 1800))
        outlay.addItem(Item(("Bob",), "B", 1500))
        outlay.addItem(Item(("Cesar",), "C", 2000))
        outlay.addItem(Item(("Daniel",), "D", 2000))
        outlay.addItem(Item(("Empu",), "E", 1700))
        outlay.addPayment(Payment(("Bob",), 5300))
        outlay.addPayment(Payment(("Empu",), 3700))

        result = mgr.computeDebts()

        expected = (
            ("Cesar", 3900, "Bob"),
            ("Daniel", 2300, "Bob"),
            ("Empu", 1200, "Alice"),
            ("Daniel", 1100, "Alice"),
        )
        self.assertEqual(result, expected)


    def test_save(self):
        self.mgr.save(self.saveHandler)

