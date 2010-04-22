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

    def addOutlay(self, date, label):
        """
            Return a new outlay.
        """
        outlay = Outlay(self, date, label)
        self.outlays[outlay.getId()] = outlay
        return outlay

    def getOutlay(self, oid):
        return self.outlays[oid]

    @staticmethod
    def checkAndAdjustTotals(persons, items, payments):
        """
            Adjust income and outcome in order to complete them with missing operations
        """
        itemsTotal = sum(items.values())
        paymentsTotal = sum(payments.values())

        if itemsTotal > paymentsTotal:
            missingAmount = itemsTotal - paymentsTotal
            missingPerPerson = missingAmount // len(persons)
            elemToAdjust = payments
        elif itemsTotal < paymentsTotal:
            missingAmount = paymentsTotal - itemsTotal
            missingPerPerson = missingAmount // len(persons)
            elemToAdjust = items
        else:
            elemToAdjust = None

        for person in persons:
            for elem in [items, payments]:
                value = missingPerPerson if elem is elemToAdjust else 0
                if person in elem.keys():
                    elem[person] += value
                else:
                    elem[person] = value

        return items, payments

    def computeTotals(self):
        itemsTotals = {}
        paymentTotals = {}
        for outlay in self.outlays.values():
            perOutlayItemsTotals = AbstractPayment.computeTotals(outlay.items)
            perOutlayPaymentsTotals = AbstractPayment.computeTotals(outlay.payments)
            perOutlayItemsTotals, perOutlayPaymentsTotals = self.checkAndAdjustTotals(outlay.persons, perOutlayItemsTotals, perOutlayPaymentsTotals)
            itemsTotals = Item.mergeTotals(itemsTotals, perOutlayItemsTotals)
            paymentTotals = Payment.mergeTotals(paymentTotals, perOutlayPaymentsTotals)


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
        while len(balances) > 1:
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

        if len(balances) > 0:
            raise RuntimeError("Wrong balances!")
        return tuple(debts)

    def computeDebts(self):
        totals = self.computeTotals()
        balances = self.computeBalances(totals)
        debts = self.aggregateDebts(balances)
        return debts

class Outlay(object):
    def __init__(self, mgr, date, label):
        self.mgr = mgr
        self.date = date
        self.label = label
        self.items = []
        self.payments = []
        self.persons = set()

    def addItem(self, persons, label, amount):
        self.addPersons(persons)
        item = Item(persons, label, amount)
        self.items.append(item)

    def addPayment(self, persons, amount):
        self.addPersons(persons)
        payment = Payment(persons, amount)
        self.payments.append(payment)

    def addPersons(self, persons):
        if type(persons) in (type(""), type(u"")):
            raise ValueError("persons must be a non string iterable")
        self.persons.update(persons)

    def getId(self):
        return id(self)

class AbstractPayment(object):
    def __init__(self, persons, amount):
        self.persons = set(persons)
        self.amount = amount

    @staticmethod
    def computeTotals(payments):
        results = {}
        for payment in payments:
            divisor = len(payment.persons)
            roundingError = payment.amount - ((payment.amount // divisor) * divisor)
            for person in payment.persons:
                amount = payment.amount // divisor + (1 if roundingError > 0 else 0)
                roundingError -= 1
                if person in results.keys():
                    results[person] += amount
                else:
                    results[person] = amount
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














