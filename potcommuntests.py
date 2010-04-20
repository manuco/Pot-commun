from unittest import TestCase

from datetime import datetime
from potcommun import DebtManager

class Tests(TestCase):
    def test_void(self):
        self.assertEqual(1, 1)
        
    def test_api(self):
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
        outlay.addPayment(("Bob"), 2000)

        # Who owes who how much?
        result = mgr.computeDebts()

        # Bob should pay back ¤25,00.
        expected = (
            ("Bob", 2500, "Alice")
        )
        self.assertEqual(result, expected)



    def test_mgr(self):
        mgr = DebtManager()
        outlay = mgr.addOutlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 5000)
        other = mgr.addOutlay(outlay.getId())