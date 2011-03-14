# -*- coding: utf-8 -*-
from __future__ import division

__version__ = "0.0"

class DebtManager(object):
    """
        A debt manager, core of this module.

        This manager handles all spendings of a journey, called outlays.

        Each outlay is connected (more or less) with a receipt a merchant gives
        you when you pay for something.

        For each outlay, you can specify:
        - who is consuming (and what)
        - who is paying (and what)

        Each outlay is composed of items (what is bought, who and how much), and payments
        (who paid, and how much). If payments and items amounts are not equals,
        the missing part is dispatched among this outlay's participating people.

        For example: let imagine you go to a restaurant then to the cinema for two of us.
        You are three friends (A, B and C)
        A and B eat a common meal for 25 €
        C eats for 15 €
        B and C drink a common bottle of wine which cost 20 €
        B pays for the complete meal (25 + 15 + 20 = 60 €).

        Then A and B go to the cinema (9€ entrance fee), A pays (18 €) and debts
        calculations will be done later.

        You'll have two outlays in the manager: one for the restaurant, and one
        for the cinema.

        For the first one, you'll add theses items:
        A & B's meal: 25 €
        C's meal: 15 €
        B & C's wine: 20 €
        payment:
        B: 60 €

        Then the second outlay :
        persons: A and B
        payment: A: 18 €

        (In the case someone is paying for something he doesn't participate
        is handled by explicitly adding the fees for the persons participating)

        Then the DebtManager would tell you that :
        C owe 25 € B (his meal (15 €) + half the wine (10 €) == 25 €, all's okay)
        A owe 4 € B (Meal is 12,50 € - 9 € == 4€) (including rounding errors :-) )

        The Python way :
        >>> from potcommun import DebtManager
        >>> mgr = DebtManager()
        >>> o1=mgr.addTransaction(Outlay(None, "Restaurant"))  # None is a placeholder for a date
        >>> o1.addItem(("A", "B"), "meal A & B", 25)
        >>> o1.addItem(("C",), "meal C", 15)
        >>> o1.addItem(("B","C",), "wine B & C", 20)
        >>> o1.addPayment(("B",), 60)
        >>> o2=mgr.addTransaction(Outlay(None, "Cinema"))
        >>> o2.addPersons(("A", "B"))  # No details about items : auto-adjustment will be done
        >>> o2.addPayment(("A",), 18)
        >>> mgr.computeDebts()
        (('C', 25, 'B'), ('A', 4, 'B'))

    """

    def __init__(self, name="unnamed"):
        self.name = name
        self.persons = set()
        self.transactions = set()

    def addPersons(self, persons):
        if type(persons) in (type(""), type(u"")):
            raise ValueError("persons must be a non string iterable")
        self.persons.update(persons)

    def getPerson(self, name):
        for person in self.persons:
            if name == person.name:
                return person

    def addTransaction(self, transaction):
        """
            Return the outlay.
        """
        transaction.mgr = self
        self.transactions.add(transaction)
        self.addPersons(transaction.persons)
        return transaction

    def addRefund(self, refund):
        self.transactions.add(refund)
        return refund

    @staticmethod
    def checkAndAdjustTotals(persons, items, payments):
        """
            Adjust income and outcome in order to complete them with missing operations
        """
        itemsTotal = sum(items.values())
        paymentsTotal = sum(payments.values())
        roundingError = 0

        if itemsTotal > paymentsTotal:
            missingAmount = itemsTotal - paymentsTotal
            elemToAdjust = payments
        elif itemsTotal < paymentsTotal:
            missingAmount = paymentsTotal - itemsTotal
            elemToAdjust = items
        else:
            elemToAdjust = None

        if elemToAdjust is not None:        
            missingPerPerson = missingAmount // len(persons)
            divisor = len(persons)
            roundingError = missingAmount - missingAmount // divisor * divisor

        for person in persons:
            for elem in [items, payments]:
                if person not in elem.keys():
                    elem[person] = 0
        
        if elemToAdjust is None:
            return items, payments
        
        for person in persons:
            elemToAdjust[person] += missingPerPerson

        while roundingError > 0:
            for person in persons:
                elemToAdjust[person] += 1 if roundingError > 0 else 0 
                roundingError -= 1

        return items, payments

    def computeTotals(self):
        itemsTotals = {}
        paymentTotals = {}
        for transaction in self.transactions:
            perTransactionItemsTotals = AbstractPayment.computeTotals(transaction.items)
            perTransactionPaymentsTotals = AbstractPayment.computeTotals(transaction.payments)
            perTransactionItemsTotals, perTransactionPaymentsTotals = self.checkAndAdjustTotals(transaction.persons, perTransactionItemsTotals, perTransactionPaymentsTotals)
            itemsTotals = Item.mergeTotals(itemsTotals, perTransactionItemsTotals)
            paymentTotals = Payment.mergeTotals(paymentTotals, perTransactionPaymentsTotals)


        return itemsTotals, paymentTotals

    def computeBalances(self):
        totals = self.computeTotals()
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

    def computeDebts(self):
        balances = self.computeBalances()
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

    def getItemsPerPerson(self):
        return self.getPaymentsOrItemsPerPerson(isPayment=False)

    def getPaymentsPerPerson(self):
        return self.getPaymentsOrItemsPerPerson(isPayment=True)


    def getPaymentsOrItemsPerPerson(self, isPayment):
        result = {}
        for person in self.persons:
            resultForPerson = {}
            for transaction in self.transactions:
                if person not in transaction.persons:
                    continue
                items = set()

                amount = 0
                elems = transaction.payments if isPayment else transaction.items
                for elem in elems:
                    amounts = elem.computeAmountPerPerson()
                    try:
                        if isPayment:
                            items.add(amounts[person])
                        else:
                            items.add((elem.label, amounts[person]))
                        amount += amounts[person]
                    except KeyError:
                        pass

                perTransactionItemsTotals = AbstractPayment.computeTotals(transaction.items)
                perTransactionPaymentsTotals = AbstractPayment.computeTotals(transaction.payments)
                perTransactionItemsTotals, perTransactionPaymentsTotals = self.checkAndAdjustTotals(transaction.persons, perTransactionItemsTotals, perTransactionPaymentsTotals)

                if isPayment:
                    if amount < perTransactionPaymentsTotals[person]:
                        items.add(perTransactionPaymentsTotals[person] - amount)
                else:
                    if amount < perTransactionItemsTotals[person]:
                        items.add(("(1 / %d)" % len(transaction.persons), perTransactionItemsTotals[person] - amount))

                total = sum(perTransactionItemsTotals.values())
                total2 = sum(perTransactionPaymentsTotals.values())
                assert total == total2
                if len(items) > 0:
                    resultForPerson[(transaction.date, transaction.label, total)] = items
            if len(resultForPerson.keys()) > 0:
                result[person] = resultForPerson
        return result


    def printItems(self, items):
        print " --- Dépenses ---\n"
        datesAndlabels = items.keys()
        datesAndlabels.sort()
        maxLabelLen = 0
        for dl in datesAndlabels:
            maxLabelLen = max(maxLabelLen, *map(len, [d[0] for d in items[dl]]))

        gdTotal = 0
        for dl in datesAndlabels:
            print dl[0], "-", dl[1], "(%s)" % format(dl[2] / 100, ".2f")
            total = 0
            for item in items[dl]:
                print " -", item[0] + " " * (maxLabelLen - len(item[0])), format(item[1] / 100, " >8.2f")
                total += item[1]
            gdTotal += total
            print " =", "Total" + " " * (maxLabelLen - 5), format(total / 100, " >8.2f")
            print

        print "Total" + " " * (maxLabelLen - 2), format(gdTotal / 100, " >8.2f"), "\n"
        return gdTotal

    def printPayments(self, payments):
        print " +++ Paiements +++\n"
        datesAndlabels = payments.keys()
        datesAndlabels.sort()

        gdTotal = 0
        for dl in datesAndlabels:
            print dl[0], "-", dl[1], " :", ", ".join([format(elem / 100, ".2f") for elem in payments[dl]]) + (" = " + format(sum(payments[dl]) / 100, ".2f") if len(payments[dl]) > 1 else "")
            gdTotal += sum(payments[dl])
        
        print "\nTotal   ", format(gdTotal / 100, " >8.2f"), "\n"
        return gdTotal


    def printReport(self):
        print
        allItems = self.getItemsPerPerson()
        allPayments = self.getPaymentsPerPerson()


        persons = list(self.persons)
        persons.sort()
        for person in persons:
            print person.name
            print "=" * len(person.name) + "\n"
            solde = 0
            try:
                solde = -self.printItems(allItems[person])
            except KeyError:
                print "Pas de dépense"
            try:
                solde += self.printPayments(allPayments[person])
            except KeyError:
                print "Pas de paiement"

            print "Solde :", format(solde / 100, ".2f")
            print
        
        print
        for a, s, b in self.computeDebts():
            print a, "doit", format(s / 100, ".2f"), "à", b

        

class Transaction(object):
    def __init__(self, date):
        self.date = date
        self.items = set()
        self.payments = set()
        self.persons = set()

    def addItem(self, item):
        self.addPersons(item.persons)
        self.items.add(item)

    def addPayment(self, payment):
        self.addPersons(payment.persons)
        self.payments.add(payment)

    def addPersons(self, persons):
        if type(persons) in (type(""), type(u"")):
            raise ValueError("persons must be a non string iterable")
        self.persons.update(persons)

    def getId(self):
        return id(self)

    def getItem(self, *args, **kwargs):
        return Item(*args, **kwargs)

    def getPayment(self, *args, **kwargs):
        return Payment(*args, **kwargs)

class Outlay(Transaction):
    def __init__(self, date, label):
        Transaction.__init__(self, date)
        self.label = label
  

class Refund(Transaction):
    """
        A direct refund, maybe partial.
    """
    def __init__(self, date, debitPerson, amount, creditPerson):
        from datetime import datetime
        Transaction.__init__(self, date)
        
        item = self.getItem((creditPerson, ), "Refund from %s" % debitPerson, amount)
        payment = self.getPayment((debitPerson, ), amount)
        
        self.addItem(item)
        self.addPayment(payment)
        
        self.debitPerson = debitPerson
        self.amount = amount
        self.creditPerson = creditPerson

    def getLabel(self):
        return "Refund to %s" % str(self.creditPerson)

    label = property(getLabel)

class AbstractPayment(object):
    def __init__(self, persons, amount):
        for person in persons:
            if type(person) in (type(""), type(u"")):
                raise ValueError("Persons should not be a string: %s." % person)

        self.persons = set(persons)
        self.amount = amount

    @staticmethod
    def computeTotals(payments):
        results = {}
        for payment in payments:
            for person, amount in payment.computeAmountPerPerson().items():
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

    def computeAmountPerPerson(self):
        results = {}
        divisor = len(self.persons)
        roundingError = self.amount - ((self.amount // divisor) * divisor)
        for person in self.persons:
            amount = self.amount // divisor + (1 if roundingError > 0 else 0)
            roundingError -= 1
            results[person] = amount
        return results


    def __eq__(self, other):
        if not isinstance(other, type(self)):
            return False
        if self.amount != other.amount:
            return False
        return self.persons == other.persons

class Payment(AbstractPayment):
    pass

class Item(AbstractPayment):
    def __init__(self, persons, label, amount):
        AbstractPayment.__init__(self, persons, amount)
        self.label = label

    def __eq__(self, other):
        if not AbstractPayment.__eq__(self, other):
            return False

        return self.label == other.label

class Person(object):
    def __init__(self, name):
        if type(name) == type(""):
            self.name = name.decode("utf-8")
        elif type(name) == type(u""):
            self.name = name
        else:
            raise ValueError("name should be a string!")

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, Person):
            return False
        return self.name == other.name

    def __repr__(self):
        return "Person('%s')" % self.name

    def __str__(self):
        return "%s  " % self.name


class Handler(object):
    """
        In memory save handler
    """
    def __init__(self, *args, **kw):
        pass

    def save(self, debtManager):
        pass

    def purge(self):
        pass



