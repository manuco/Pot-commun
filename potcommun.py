# -*- coding: utf-8 -*-
from __future__ import division
import warnings

__version__ = "0.0"

def getAmountAsString(amount):
    if amount < 0:
        return u"%d,%02d €" % ((amount + 99) // 100, -amount % 100)
    else:
        return u"%d,%02d €" % (amount // 100, amount % 100)


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
        self.transactions = set()

    def getPersons(self):
        result = set()
        for transaction in self.transactions:
            result.update(transaction.getPersons())
        return result

    def addPersons(self, persons):
        raise RuntimeError("Deprecated : add persons thru transactions.")
        if type(persons) in (type(""), type(u"")):
            raise ValueError("persons must be a non string iterable")
        self.persons.update(persons)

    def getPerson(self, name):
        persons = self.getPersons()
        for person in persons:
            if name == person.name:
                return person

    def addTransaction(self, transaction):
        """
            Return the outlay.
        """
        warnings.warn("Use xxx.transactions.add instead", DeprecationWarning, stacklevel=2)
        self.transactions.add(transaction)
        return transaction

    def addRefund(self, refund):
        warnings.warn("Use xxx.transactions.add instead", DeprecationWarning, stacklevel=2)
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

        # We only adjust the items : what has been paid should't be adjusted
        # It only change the way the computation is done, but the result is the same
        # But the report are now righlty generated
        if itemsTotal != paymentsTotal:
            #missingAmount = itemsTotal - paymentsTotal
            #elemToAdjust = payments
        #elif itemsTotal < paymentsTotal:
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
            perTransactionItemsTotals, perTransactionPaymentsTotals = self.checkAndAdjustTotals(transaction.getPersons(), perTransactionItemsTotals, perTransactionPaymentsTotals)
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
        for person in self.getPersons():
            resultForPerson = {}
            for transaction in self.transactions:
                persons_for_transaction = transaction.getPersons()
                if person not in persons_for_transaction:
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
                            if len(elem.persons) > 1:
                                items.add((u"1/%d %s" % (len(elem.persons), elem.label), amounts[person]))
                            else:
                                items.add((elem.label, amounts[person]))
                        amount += amounts[person]
                    except KeyError:
                        pass

                perTransactionItemsTotals = AbstractPayment.computeTotals(transaction.items)
                perTransactionPaymentsTotals = AbstractPayment.computeTotals(transaction.payments)
                perTransactionItemsTotals, perTransactionPaymentsTotals = self.checkAndAdjustTotals(persons_for_transaction, perTransactionItemsTotals, perTransactionPaymentsTotals)

                if isPayment:
                    if amount != perTransactionPaymentsTotals[person]:
                        raise ValueError("Adjustements on payments are forbidden")
                        items.add(perTransactionPaymentsTotals[person] - amount)
                else:
                    if amount < perTransactionItemsTotals[person]:
                        items.add((u"(1/%d)" % len(persons_for_transaction), perTransactionItemsTotals[person] - amount))
                    elif amount > perTransactionItemsTotals[person]:
                        items.add((u"(Réduction)", perTransactionItemsTotals[person] - amount))

                total = sum(perTransactionItemsTotals.values())
                total2 = sum(perTransactionPaymentsTotals.values())
                assert total == total2
                if len(items) > 0:
                    resultForPerson[(transaction.date, transaction.label, total)] = items
            if len(resultForPerson.keys()) > 0:
                result[person] = resultForPerson
        return result


    def getReportItems(self, items):
        text = u" --- Dépenses ---\n\n"
        datesAndlabels = items.keys()
        datesAndlabels.sort()
        maxLabelLen = 0
        for dl in datesAndlabels:
            maxLabelLen = max(maxLabelLen, *map(len, [d[0] for d in items[dl]])) + 5

        gdTotal = 0
        for dl in datesAndlabels:
            text += unicode(dl[0]) + u" - " + dl[1] + u"\n"
            total = 0
            for item in items[dl]:
                text += u" - " + item[0] + u" " * (maxLabelLen - len(item[0])) + getAmountAsString(item[1]) + u"\n"
                total += item[1]
            gdTotal += total
            text += u" = Total" + u" " * (maxLabelLen - 5) + getAmountAsString(total)
            text += u"\n\n"

        text += u"Total" + u" " * (maxLabelLen - 2) + getAmountAsString(gdTotal) + "\n\n"
        return gdTotal, text

    def getReportPayments(self, payments):
        text = u" +++ Paiements +++\n\n"
        datesAndlabels = payments.keys()
        datesAndlabels.sort()

        gdTotal = 0
        for dl in datesAndlabels:
            text += unicode(dl[0]) +  u" - " + dl[1] + u" : " + u", ".join([getAmountAsString(elem) for elem in payments[dl]]) + (u" = " + getAmountAsString(sum(payments[dl])) if len(payments[dl]) > 1 else u"") + "\n"
            gdTotal += sum(payments[dl])
        text += u"\nTotal   " +  getAmountAsString(gdTotal) + "\n\n"
        return gdTotal, text

    def getDebtsReport(self):
        text = u""
        debts = self.computeDebts()
        for a, s, b in debts:
            text += a.name + " doit " + getAmountAsString(s) + u" à " + b.name + u"\n"
        if len(debts) == 0:
            text += u"Aucune dette.\n"
        text += u"\n"

        return text


    def getReport(self):
        text = u"     %s\n" % self.name
        text += u"   %s\n\n\n" % (u"-" * (len(self.name) + 4))
        allItems = self.getItemsPerPerson()
        allPayments = self.getPaymentsPerPerson()


        persons = list(self.getPersons())
        persons.sort()
        for person in persons:
            text += person.name + u"\n"
            text +=  "=" * len(person.name) + "\n\n"
            solde = 0
            try:
                gdTotal, subText = self.getReportItems(allItems[person])
                solde = -gdTotal
                text += subText
            except KeyError:
                text += u"Pas de dépense\n"
            try:
                gdTotal, subText = self.getReportPayments(allPayments[person])
                solde += gdTotal
                text += subText

            except KeyError:
                text += u"Pas de paiement\n"

            text += u"Solde : " + getAmountAsString(solde) + u"\n\n"

        if len(persons) == 0:
            text += u"Aucune personne ne participe à ce pot commun.\n"
        text += u"\n"

        text += self.getDebtsReport()

        return text

    def printReport(self):
        print self.getReport()


class Transaction(object):
    def __init__(self, date):
        self.date = date
        self.items = set()
        self.payments = set()
        self.persons = set()

    def addItem(self, item):
        warnings.warn("Use xxx.items.add instead", DeprecationWarning, stacklevel=2)
        self.items.add(item)

    def addPayment(self, payment):
        warnings.warn("Use xxx.items.add instead", DeprecationWarning, stacklevel=2)
        self.payments.add(payment)

    def getPersons(self):
        result = set(self.persons)
        for item in self.items:
            result.update(item.persons)
        for payment in self.payments:
            result.update(payment.persons)
        return result
        
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

    def getItemsTotalAmount(self):
        amount = 0
        for item in self.items:
            amount += item.amount

        return amount

    def getPaymentsTotalAmount(self):
        amount = 0
        for payment in self.payments:
            amount += payment.amount
        return amount

    def getBalance(self):
        """
            Should be 0 if all has been declared
            Should be > 0 if only paiment is indicated
            < 0 let think there is an error
        """
        return self.getPaymentsTotalAmount() - self.getItemsTotalAmount()

    def getItemForPerson(self, person):
        """
            Return a set of tuples, where the first element is the item
            and the second, the part the person is involved (for items shared amongs persons)
        """
        result = set()
        for item in self.items:
            if person in item.persons:
                result.add((item, len(item.persons)))
        return result


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
        self.update(date, debitPerson, amount, creditPerson)

    def update(self, date, debitPerson, amount, creditPerson):
        self.items.clear()
        self.payments.clear()

        item = self.getItem((creditPerson, ), "Remboursement de %s" % debitPerson, amount)
        payment = self.getPayment((debitPerson, ), amount)

        self.items.add(item)
        self.payments.add(payment)

        self.date = date

        self.debitPerson = debitPerson
        self.creditPerson = creditPerson

    @property
    def label(self):
        return u"Remboursement de %s à %s" % (self.debitPerson.name, self.creditPerson.name)

    @property
    def amount(self):
        import sys
        print >>sys.stderr, self.payments
        return set(self.payments).pop().amount

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



