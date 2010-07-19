# -*- coding: utf-8 -*-

from unittest import TestCase

from datetime import datetime
from potcommun import Handler, DebtManager, Item, Payment, Outlay, Person, Refund

class Tests(TestCase):
    def test_void(self):
        self.assertEqual(1, 1)

    def setUp(self):
        self.saveHandler = Handler()

        mgr = DebtManager()
        self.alice = alice = Person("Alice")
        self.bob = bob = Person("Bob")
        mgr.addPersons((alice, bob))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "Starter", 500))
        outlay.addItem(Item((alice,), "Course", 2000))
        outlay.addItem(Item((bob,), "Course", 2500))
        outlay.addItem(Item((bob,), "Wine", 1000))
        outlay.addPayment(Payment((alice,), 6000))
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice, bob), "ticket", 2000))
        outlay.addPayment(Payment((bob,), 2000))
        self.mgr = mgr

    def test_add_person_as_string_raise(self):
        """
            A person should be inserted as a Person, not as a String.
        """
        mgr = DebtManager()
        self.assertRaises(Exception, mgr.addPersons, "Alice")
        mgr.addPersons((Person("Alice"), ))

        alice = mgr.getPerson("Alice")
        self.assertRaises(Exception, Item, ("Alice",), "Starter", 500)
        item = Item((alice,), "Starter", 500)

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
        alice = Person("Alice")
        bob = Person("Bob")

        # When, what, how much, in cents
        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        # Who has consummed, what, how much
        outlay.addItem(Item((alice,), "Starter", 500))
        outlay.addItem(Item((alice,), "Course", 2000))
        outlay.addItem(Item((bob,), "Course", 2500))
        outlay.addItem(Item((bob,), "Wine", 1000))
        # Who, how much
        outlay.addPayment(Payment((alice,), 6000))

        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        # Who has consummed, what, how much
        outlay.addItem(Item((alice, bob), "ticket", 2000))
        # Who, how much
        outlay.addPayment(Payment((bob,), 2000))

        # Who owes who how much?
        result = mgr.computeDebts()

        # Bob should pay back ¤25,00.
        expected = (
            (bob, 2500, alice),
        )
        self.assertEqual(result, expected)


    def test_abstract_payments_totals(self):
        a = Person("a")
        b = Person("b")
        payments = (Payment((a, b), 4), Payment((a,), 3), Payment((b,), 5))
        r = Payment.computeTotals(payments)
        self.assertEqual(r, {a: 5, b: 7})

    def test_merge_totals(self):
        r = Payment.mergeTotals({"A": 5, "B": 7}, {"A": 5, "C": 3})
        self.assertEqual(r, {"A": 10, "B": 7, "C": 3})

    def test_compute_totals(self):
        r = self.mgr.computeTotals()
        self.assertEqual(r, ({self.alice: 3500, self.bob: 4500}, {self.alice: 6000, self.bob: 2000}))

    def test_compute_balances(self):
        r = self.mgr.computeBalances()
        self.assertEqual(r, {self.alice: -2500, self.bob: 2500})

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
        alice = Person("Alice")
        bob = Person("Bob")
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPayment(Payment((bob,), 2000))
        outlay.addPersons((alice,))
        result = mgr.computeDebts()
        expected = ((alice, 1000, bob),)
        self.assertEqual(result, expected)

    def test_void_operation(self):
        mgr = DebtManager()
        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        alice = Person("Alice")
        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T1")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1))

        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        bob = Person("Bob")
        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T2")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1))
        outlay.addItem(Item((bob,), "B", 1))

        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T3")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1))
        outlay.addItem(Item((bob,), "B", 1))
        outlay.addPayment(Payment((alice, bob), 2))

        result = mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T4")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1))
        outlay.addPayment(Payment((bob,), 1))

        result = mgr.computeDebts()
        expected = ((alice, 1, bob), )
        self.assertEqual(result, expected)


    def test_real_example(self):
        mgr = DebtManager()
        alice = Person("Alice")
        bob = Person("Bob")
        cesar = Person("Cesar")
        daniel = Person("Daniel")
        empu = Person("Empu")

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T1")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1500))
        outlay.addItem(Item((bob,), "B", 1700))
        outlay.addItem(Item((cesar,), "C", 1600))
        outlay.addItem(Item((daniel,), "D", 1500))
        outlay.addItem(Item((empu,), "E", 1000))
        outlay.addItem(Item((alice, bob, cesar, daniel), "F", 2000))
        outlay.addPayment(Payment((alice,), 9300))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T2")
        mgr.addOutlay(outlay)
        outlay.addPersons((alice, bob, cesar, daniel, empu))
        outlay.addPayment(Payment((bob,), 7500))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T3")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1000))
        outlay.addItem(Item((bob,), "B", 700))
        outlay.addItem(Item((cesar,), "C", 900))
        outlay.addPayment(Payment((cesar,), 2600))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T4")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 700))
        outlay.addItem(Item((bob,), "B", 700))
        outlay.addItem(Item((daniel,), "D", 700))
        outlay.addItem(Item((empu,), "E", 700))
        outlay.addPayment(Payment((daniel,), 2800))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "T5")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "A", 1800))
        outlay.addItem(Item((bob,), "B", 1500))
        outlay.addItem(Item((cesar,), "C", 2000))
        outlay.addItem(Item((daniel,), "D", 2000))
        outlay.addItem(Item((empu,), "E", 1700))
        outlay.addPayment(Payment((bob,), 5300))
        outlay.addPayment(Payment((empu,), 3700))

        result = mgr.computeDebts()

        expected = (
            (cesar, 3900, bob),
            (daniel, 2300, bob),
            (empu, 1200, alice),
            (daniel, 1100, alice),
        )
        self.assertEqual(result, expected)


    def test_save(self):
        pass
        
    def test_rounding_bug_when_item_payment_balance_is_not_null(self):
        mgr = DebtManager()
        alice = Person("Alice")
        bob = Person("Bob")
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPayment(Payment((bob,), 3))
        outlay.addPersons((alice,))
        result = mgr.computeDebts()
        expected = ((alice, 1, bob),)
        self.assertEqual(result, expected)

    def test_refunds(self):
        self.mgr.addRefund(Refund(self.bob, 2500, self.alice))
        result = self.mgr.computeDebts()
        expected = ()
        self.assertEqual(result, expected)

    def test_partial_refunds(self):
        self.mgr.addRefund(Refund(self.bob, 500, self.alice))
        result = self.mgr.computeDebts()
        expected = ((self.bob, 2000, self.alice),)
        self.assertEqual(result, expected)


    def test_items_equality(self):
        item1 = Item((Person("alice"), Person("Bob"),),  "abcd", 15)
        item2 = Item((Person("bob"), Person("alice"),), "abcd", 15)
        self.assertEqual(item1, item2)

        item3 = Item((Person("alice"), ), "abcd", 15)
        self.assertNotEqual(item1, item3)

        item4 = Item((Person("alice"), ), "abcd", 16)
        self.assertNotEqual(item4, item3)

        item5 = Item((Person("alice"), ), "abcde", 16)
        self.assertNotEqual(item4, item5)

    def test_data_formaters_items(self):
        result = self.mgr.getItemsPerPerson()
        expected = {
            Person("Alice"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    ("Starter", 500),
                    ("Course", 2000),
                )),
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000): set((("ticket", 1000), )),
            },

            Person("Bob"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    ("Course", 2500),
                    ("Wine", 1000),
                )),
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000): set((("ticket", 1000), )),
            },
        }
        self.assertEqual(result, expected)

    def test_data_formaters_items2(self):
        mgr = DebtManager()
        alice = mgr.addPersons((Person("Alice"), ))
        bob = mgr.addPersons((Person("Bob"), ))
        carl = mgr.addPersons((Person("Carl"), ))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "Starter", 500))
        outlay.addItem(Item((alice,), "Course", 2000))
        outlay.addItem(Item((bob,), "Course", 2500))
        outlay.addItem(Item((bob,), "Wine", 1000))
        outlay.addPayment(Payment((alice,), 6000))
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPersons((alice, bob, carl))
        outlay.addPayment(Payment((bob,), 3000))
        

        result = mgr.getItemsPerPerson()
        expected = {
            Person("Alice"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    ("Starter", 500),
                    ("Course", 2000),
                )),
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((("(1 / 3)", 1000), )),
            },

            Person("Bob"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    ("Course", 2500),
                    ("Wine", 1000),
                )),
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((("(1 / 3)", 1000), )),
            },
            Person("Carl"): {
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((("(1 / 3)", 1000), )),
            },
        }
        self.assertEqual(result, expected)



    def test_data_formaters_items3(self):
        mgr = DebtManager()
        alice = mgr.addPersons((Person("Alice"), ))
        bob = mgr.addPersons((Person("Bob"), ))
        carl = mgr.addPersons((Person("Carl"), ))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "Starter", 500))
        outlay.addItem(Item((alice,), "Course", 2000))
        outlay.addItem(Item((bob,), "Course", 2500))
        outlay.addItem(Item((bob,), "Wine", 1000))
        outlay.addPayment(Payment((carl,), 6000))
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPersons((alice, bob, carl))
        outlay.addPayment(Payment((bob,), 3000))


        result = mgr.getItemsPerPerson()
        expected = {
            Person("Alice"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    ("Starter", 500),
                    ("Course", 2000),
                )),
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((("(1 / 3)", 1000), )),
            },

            Person("Bob"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    ("Course", 2500),
                    ("Wine", 1000),
                )),
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((("(1 / 3)", 1000), )),
            },
            Person("Carl"): {
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((("(1 / 3)", 1000), )),
            },
        }
        self.assertEqual(result, expected)



    def test_data_formaters_payments(self):
        result = self.mgr.getPaymentsPerPerson()
        expected = {
            Person("Alice"): {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    6000,
                )),
            },

            Person("Bob"): {
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 2000): set((2000, )),
            },
        }
        self.assertEqual(result, expected)

        mgr = DebtManager()
        alice = mgr.addPersons((Person("Alice"), ))
        bob = mgr.addPersons((Person("Bob"), ))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "Starter", 500))
        outlay.addItem(Item((alice,), "Course", 2000))
        outlay.addItem(Item((bob,), "Course", 2500))
        outlay.addItem(Item((bob,), "Wine", 1000))
        outlay.addPayment(Payment((alice,), 6000))
        
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPersons((alice, bob))
        outlay.addPayment(Payment((bob,), 2000))

        result = mgr.getPaymentsPerPerson()
        self.assertEqual(result, expected)

    def test_data_formaters_payments2(self):

        mgr = DebtManager()
        alice = mgr.addPersons((Person("Alice"), ))
        bob = mgr.addPersons((Person("Bob"), ))
        carl = mgr.addPersons((Person("Carl"), ))

        outlay = Outlay(datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli")
        mgr.addOutlay(outlay)
        outlay.addItem(Item((alice,), "Starter", 500))
        outlay.addItem(Item((alice,), "Course", 2000))
        outlay.addItem(Item((bob,), "Course", 2500))
        outlay.addItem(Item((bob,), "Wine", 1000))
        outlay.addPayment(Payment((carl,), 6000))
        outlay = Outlay(datetime(2010, 3, 15, 21, 0, 0), "Cinema")
        mgr.addOutlay(outlay)
        outlay.addPersons((alice, bob, carl))
        outlay.addPayment(Payment((bob,), 3000))

        expected = {
            carl: {
                (datetime(2010, 3, 15, 20, 0, 0), "Restaurant le Grizzli", 6000): set((
                    6000,
                )),
            },

            Person("Bob"): {
                (datetime(2010, 3, 15, 21, 0, 0), "Cinema", 3000): set((3000, )),
            },
        }

        result = mgr.getPaymentsPerPerson()
        self.assertEqual(result, expected)

    def test_report(self):
        self.mgr.printReport()

