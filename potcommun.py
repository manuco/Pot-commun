# -*- coding: utf-8 -*-
from __future__ import division

class DebtManager(object):
    """
        A debt manager, core of this module
    """

    def __init__(self):
        self.persons = []
        self.outlays = {}

    def addPerson(self, name):
        if name not in self.persons:
            self.persons.append(name)
        else:
            raise ValueError("Already registered")

    def addOutlay(self, date, label, totalAmount):
        """
            Return a new outlay.
        """
        outlay = Outlay(self)
        self.outlays[outlay.getId()] = outlay
        return outlay

    def getOutlay(self, oid):
        return self.outlays[oid]

    @staticmethod
    def checkAndAdjustTotals(items, payments):
        """
            Adjust income and outcome in order to complete them with missing operations
        """
        names = set(items.keys() + payments.keys())
        itemsTotal = sum(items.values())
        paymentsTotal = sum(payments.values())

        if itemsTotal > paymentsTotal:
            missingAmount = itemsTotal - paymentsTotal
            missingPerPerson = missingAmount // len(names)
            elem = payments
        elif itemsTotal < paymentsTotal:
            missingAmount = paymentsTotal - itemsTotal
            missingPerPerson = missingAmount // len(names)
            elem = items
        else:
            names = []

        for name in names:
            if name in elem.keys():
                elem[name] += missingPerPerson
            else:
                elem[name] = missingPerPerson


        return items, payments

    def computeTotals(self):
        itemsTotals = {}
        paymentTotals = {}
        for outlay in self.outlays.values():
            totals = Item.computeTotals(outlay.items)
            itemsTotals = Item.mergeTotals(itemsTotals, totals)
            totals = Payment.computeTotals(outlay.payments)
            paymentTotals = Payment.mergeTotals(paymentTotals, totals)

        self.checkAndAdjustTotals(itemsTotals, paymentTotals)

        return itemsTotals, paymentTotals

    def computeBalances(self, totals):
        result = {}
        for name in totals[0].keys():
            result[name] = totals[0][name] - totals[1][name]
        return result

    def filterNull(self, balances):
        names = []
        for name, amount in balances.items():
            if amount == 0:
                names.append(name)
        for name in names:
            del balances[name]
        return balances

    def aggregateDebts(self, balances):
        debts = []
        balances = self.filterNull(balances)
        while len(balances):
            names = balances.keys()
            names.sort(cmp=lambda x, y: cmp(balances[x], balances[y]))
            pa = balances[names[0]]
            pb = balances[names[-1]]
            ## pb owes pa
            if -pa >= pb:
                debts.append((names[-1], pb, names[0]))
                balances[names[0]] += pb
                balances[names[-1]] = 0
            else:
                debts.append((names[-1], -pa, names[0]))
                balances[names[0]] = 0
                balances[names[-1]] += pa

            balances = self.filterNull(balances)
        return tuple(debts)

    def computeDebts(self):
        totals = self.computeTotals()
        balances = self.computeBalances(totals)
        debts = self.aggregateDebts(balances)
        return debts

class Outlay(object):
    def __init__(self, mgr):
        self.mgr = mgr
        self.items = []
        self.payments = []

    def addItem(self, persons, label, amount):
        item = Item(persons, label, amount)
        self.items.append(item)

    def addPayment(self, persons, amount):
        payment = Payment(persons, amount)
        self.payments.append(payment)

    def getId(self):
        return id(self)

class AbstractPayment(object):
    def __init__(self, persons, amount):
        if type(persons) in (type(""), type(u"")):
            persons = (persons,)
        self.persons = tuple(persons)
        self.amount = amount

    @staticmethod
    def computeTotals(payments):
        results = {}
        for payment in payments:
            divisor = len(payment.persons)
            for person in payment.persons:
                if person in results.keys():
                    results[person] += payment.amount // divisor
                else:
                    results[person] = payment.amount // divisor
        return results

    @staticmethod
    def mergeTotals(totalsA, totalsB):
        for name, amount in totalsB.items():
            if name in totalsA.keys():
                totalsA[name] += amount
            else:
                totalsA[name] = amount
        return totalsA

class Payment(AbstractPayment):
    pass

class Item(AbstractPayment):
    def __init__(self, persons, label, amount):
        self.label = label
        AbstractPayment.__init__(self, persons, amount)














