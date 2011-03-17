#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import os
import re
import traceback
import datetime
import subprocess

import curses
import curses.wrapper

import potcommun
from potcommun import getAmountAsString
import sqlstorage
from forms import *

import locale
locale.setlocale(locale.LC_ALL, '')

#import sys
#sys.stderr = open("/dev/pts/3", "w")
#print >>sys.stderr, "\n" * 10

os.environ["ESCDELAY"] = "10"
## Tip : export ESCDELAY var to reduce time to interpret escape key (10 is fine)

def getPersonsAsString(persons):
    return u", ".join([p.name for p in persons])

class WelcomeForm(BaseForm):
    def draw(self):
        BaseForm.draw(self)
        title = u"Bienvenue ! Appuyez sur Entrée pour commencer."
        my, mx = self.win.getmaxyx()
        x = mx // 2 - len(title) // 2
        y = my // 2
        self.win.addstr(y, x, title.encode(ENCODING), YELLOW | c.A_BOLD)

    def onInput(self, ch, key):
        if ch == 27 or key in ('q', 'Q'):
            return 1
        elif ch == 13:
            return DebtManagerSelection()

class DebtManagerForm(BaseForm):
    def __init__(self, dm):
        self.dm = dm
        self.menu = BaseMenu()
        self.statsLabel = MultiLinesLabel("")

        self.onFocus()
        
    def getOutlays(self):
        r = []
        r.append((u" - Nouvelle dépense...", "new_outlay"))
        i = [(o.date.strftime('%Y-%m-%d') + u" " +  o.label, o) for o in self.dm.transactions if isinstance(o, sqlstorage.Outlay)]
        i.sort(lambda a, b: cmp(a[1].date, b[1].date), reverse=True)
        r.extend(i)
        r.append((u" - Nouveau remboursement...", "new_refund"))
        i = [(o.label, o) for o in self.dm.transactions if isinstance(o, sqlstorage.Refund)]
        i.sort()
        r.extend(i)
        r.append((u" - Modifier ce pot commun...", "edit_dm"))
        r.append((u" - Afficher rapport complet...", "display_report"))
        return r

    def layout(self, win):
        BaseForm.layout(self, win)
        ymax, xmax = win.getmaxyx()
        topOffset = 0
        menuLinesCount = min(len(self.outlays), 13)
        self.menu.layout(self.win.derwin(menuLinesCount + 2, xmax, topOffset, 0))

        self.statsLabel.layout(self.win.derwin(topOffset + menuLinesCount + 2, 7))

    def draw(self):
        BaseForm.draw(self)
        self.menu.draw()
        self.statsLabel.draw()

    def onInput(self, ch, key):
        action = self.menu.onInput(ch, key)
        if action == "DELETE":
            self.dm.transactions.remove(self.menu.getSelectedItem())
            db = getDB()
            db.saveDebtManager(self.dm)
            self.onFocus()
            return "OK"
        elif action == "ACCEPT":
            transaction = self.menu.getSelectedItem()
            if transaction == "new_outlay":
                outlay = sqlstorage.Outlay(datetime.datetime.now(), "")
                return OutlayEditForm(self.dm, outlay)
            elif transaction == "new_refund":
                refund = sqlstorage.Refund(datetime.datetime.now(), None, 0, None)
                return RefundEditForm(self.dm, refund)
            elif transaction == "display_report":
                self.displayReport()
                return "OK"
            elif transaction == "edit_dm":
                return DebtManagerEditForm(self.dm)
            elif isinstance(transaction, sqlstorage.Outlay):
                return OutlayManagementForm(self.dm, transaction)
            elif isinstance(transaction, sqlstorage.Refund):
                return RefundEditForm(self.dm, transaction)
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        return action

    def getStats(self):
        leftLines = [u"Soldes :"]

        maxName = 0
        maxAmount = 0
        for person, balance in self.dm.computeBalances().items():
            maxName = max(maxName, len(person.name))
            maxAmount = max(maxAmount, len(getAmountAsString(balance)))

        maxName += 2

        balances = self.dm.computeBalances().items()
        balances.sort(lambda a, b: cmp(a[1], b[1]))

        for person, balance in balances:
            name = person.name
            amount = getAmountAsString(balance)
            padding = u" " * ((maxName - len(name)) + (maxAmount - len(amount)))
            leftLines.append(name + padding + amount)

        rightLines = [u"%sDettes :" % (u" " * (len(leftLines[0]) - 1))]
        debts = self.dm.computeDebts()
        for debit, amount, credit in debts:
            rightLines.append(u"%s -> %s -> %s" % (debit.name, getAmountAsString(amount), credit.name))

        if len(leftLines) > len(rightLines):
            rightLines.extend([u"" for i in range(len(leftLines) - len(rightLines))])
        else:
            leftLines.extend([u"" for i in range(len(rightLines) - len(leftLines))])

        lines = []
        for left, right in zip(leftLines, rightLines):
            lines.append("%s            %s" % (left, right))
        if len(lines) == 1:
            return u""
        return "\n".join(lines)

    def onFocus(self):
        self.outlays = self.getOutlays()
        self.menu.refresh(self.outlays)
        self.menu.setTitle(u"Pot commun : %s" % self.dm.name)
        self.statsLabel.setText(self.getStats())

    def displayReport(self):
        curses.def_prog_mode()
        curses.endwin()

        text = self.dm.getReport()

        tool = "/usr/bin/less"
        process = subprocess.Popen(
            args=[tool, "-cM", "+g", "+G", "-PM  %lb / %L -- {0} -- (Q pour quitter)$".format(self.dm.name.encode(ENCODING)), ],
            executable=tool,
            stdin=subprocess.PIPE,
        )

        process.stdin.write(text.encode(ENCODING))
        process.stdin.close()
        result = None
        while result is None:
            try:
                result = process.wait()
            except KeyboardInterrupt:
                pass
        curses.reset_prog_mode()
        curses.flushinp()
        self.win.refresh()

class RefundEditForm(BaseForm):
    def __init__(self, dm, refund):
        self.dm = dm
        self.refund = refund

        self.debitPerson = set() if refund.debitPerson is None else set((refund.debitPerson,))
        self.creditPerson = set() if refund.creditPerson is None else set((refund.creditPerson,))

        self.stack = StackedFields()
        self.dateField = InputField(u"Date : ", unicode(refund.date.strftime("%Y-%m-%d %H:%M:%S")))
        self.debitPersonField = PersonChooserField(dm, u"De qui ? ", self.debitPerson, unique=True)
        self.creditPersonField = PersonChooserField(dm, u"À qui ? ", self.creditPerson, unique=True)
        self.amountField = InputField(u"Montant : ", getAmountAsString(refund.amount) if refund.amount != 0 else u"")
        self.errorField = Label("")

        self.stack.add(self.dateField)
        self.stack.add(self.debitPersonField)
        self.stack.add(self.creditPersonField)
        self.stack.add(self.amountField)
        self.stack.add(self.errorField)

        self.errorString = ""

    def layout(self, win):
        self.win = win
        xmax = win.getmaxyx()[1]
        self.workspace = self.win.derwin(len(self.stack), xmax, 5, 0)
        self.stack.layout(self.workspace)

    def draw(self):
        self.drawTitle(u"Édition d'un remboursement", WHITE)
        self.stack.draw()

    def onInput(self, ch, key):
        self.errorField.setText(self.errorString, WHITE)
        action = self.stack.onInput(ch, key)
        if action == "ACCEPT":
            try:
                amount = self.amountField.getUserInput().strip()
                if len(amount) > 0:
                    RE = ur"^ *(\d+)(?:[,.](\d{1,2}))?(?: *€? *)?$"
                    result = re.findall(RE, amount)
                    euros = result[0][0]
                    cents = result[0][1]
                    if len(cents) == 0:
                        cents = 0

                    amount = int(euros) * 100 + int(cents)
                else:
                    amount = 0
            except IndexError:
                self.errorString = u"Veuillez entrer un montant positif valide (15.55 par exemple)."
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.stack.onFocus()
                return "OK"
            except Exception, e:
                self.errorString = e.args[0].decode(ENCODING)
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.stack.onFocus()
                return "OK"

            try:
                date = datetime.datetime.strptime(self.dateField.getUserInput(), "%Y-%m-%d %H:%M:%S")
            except Exception, e:
                self.errorString = e.args[0].decode(ENCODING)
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.stack.onFocus()
                return "OK"

            try:
                debitPerson = set(self.debitPersonField.persons).pop()
                creditPerson = set(self.creditPersonField.persons).pop()
            except KeyError:
                self.errorString = u"Veuillez préciser les deux personnes de cette transaction."
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.stack.onFocus()
                return "OK"

            self.refund.update(date, debitPerson, amount, creditPerson)

            if self.refund not in self.dm.transactions:
                self.dm.transactions.add(self.refund)

            db = getDB()
            db.saveDebtManager(self.dm)
            return 1
        elif action == "CANCEL":
            return 1
        elif action == "FOCUS_NEXT":
            self.stack.onFocus(first=True)
            return "OK"
        elif action == "FOCUS_PREVIOUS":
            self.stack.onFocus(last=True)
            return "OK"
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        return action


class DebtManagerSelection(BaseForm):

    def __init__(self):
        self.dms = None
        self.dmToBeDeleted = None
        self.menu = BaseMenu()

    def onFocus(self):
        self.menu.refresh(self.getDMs(), self.menu.getSelectedIndex() if self.menu is not None else 0)

    def layout(self, win):
        BaseForm.layout(self, win)
        self.menu.layout(self.win.derwin(4, 0))

    def draw(self):
        BaseForm.draw(self)
        self.drawTitle(u"Sélection du pot commun", WHITE)
        if self.dms is None:
            self.dms = self.getDMs()
        self.menu.draw()


    def onInput(self, ch, key):
        action = self.menu.onInput(ch, key)
        if action == "DELETE":
            self.deleteDM(self.menu.getSelectedItem())
            self.menu.refresh(self.getDMs(), self.menu.getSelectedIndex())
        elif action == "ACCEPT":
            dm = self.menu.getSelectedItem()
            if dm is None:
                return DebtManagerEditForm(sqlstorage.DebtManager(u""))
            else:
                return DebtManagerForm(dm)
        elif action is None:
            return BaseForm.onInput(self, ch, key)

    def getDMs(self):
        db = getDB()
        
        r = [(dm.name, dm) for dm in db.getManagers()]
        r.sort()
        r.append(
            (u"Nouveau pot commun...", None),
        )

        return r


    def deleteDM(self, dm):
        db = getDB()
        db.deleteDebtManager(dm)
        

class DebtManagerEditForm(BaseForm):

    def __init__(self, dm):
        self.dm = dm
        self.inputField = InputField(u"Nom : ", dm.name)

    def layout(self, win):
        self.win = win
        lines, cols = self.inputField.getPreferredSize()
        mlines, mcols = win.getmaxyx()
        subwin = win.derwin(lines, min(cols, mcols - 2), 5, 0)
        self.inputField.layout(subwin)

    def draw(self):
        self.drawTitle(u"Nouveau pot commun", WHITE)
        self.inputField.draw()

    def onInput(self, ch, key):
        action = self.inputField.onInput(ch, key)
        if action == "ACCEPT":
            self.dm.name = self.inputField.getUserInput()
            db = getDB()
            db.saveDebtManager(self.dm)
            return 1
        elif action == "CANCEL":
            return 1

class OutlayEditForm(BaseForm):
    def __init__(self, dm, outlay):
        self.dm = dm
        self.outlay = outlay
        self.stack = StackedFields()
        self.nameField = InputField(u"Nom : ", outlay.label)
        self.dateField = InputField(u"Date : ", unicode(outlay.date.strftime("%Y-%m-%d %H:%M:%S")))
        self.errorMsg = Label("")
        self.errorString = ""
        self.stack.add(self.nameField)
        self.stack.add(self.dateField)
        self.stack.add(self.errorMsg)

    def layout(self, win):
        self.win = win
        xmax = win.getmaxyx()[1]
        self.workspace = self.win.derwin(len(self.stack), xmax, 5, 0)
        self.stack.layout(self.workspace)

    def draw(self):
        self.drawTitle(u"Édition d'une dépense", WHITE)
        self.stack.draw()
        
    def onInput(self, ch, key):
        self.errorMsg.setText(self.errorString, WHITE)
        action = self.stack.onInput(ch, key)
        if action == "ACCEPT":
            try:
                self.outlay.label = self.nameField.getUserInput()
                self.outlay.date = datetime.datetime.strptime(self.dateField.getUserInput(), "%Y-%m-%d %H:%M:%S")
                if self.outlay not in self.dm.transactions:
                    self.dm.transactions.add(self.outlay)
                db = getDB()
                db.saveDebtManager(self.dm)
                return 1
            except Exception, e:
                self.errorString = e.args[0].decode(ENCODING)
                self.errorMsg.setText(self.errorString, RED | curses.A_BOLD)
                self.stack.onFocus()
                return "OK"
        elif action == "CANCEL":
            return 1
        elif action == "FOCUS_NEXT":
            self.stack.onFocus(first=True)
            return "OK"
        elif action == "FOCUS_PREVIOUS":
            self.stack.onFocus(last=True)
            return "OK"
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        return action

class OutlayDetailsForm(Widget):
    """
        Right pane of the outlay
    """
    focusable = True
    def __init__(self, dm, outlay):
        self.dm = dm
        self.outlay = outlay
        self.field = MultiLinesLabel("")

    def text_involved(self, text):
        balance = self.outlay.getBalance()
        text += u"Participants :\n"
        allPersons = self.outlay.getPersons()
        for person in allPersons:
            items = self.outlay.getItemForPerson(person)
            if len(items) > 0:
                total = 0
                subText = ""
                for item, part in items:
                    if part > 1:
                        subText += u"   - 1/%d %s (%s)\n" % (part, item.label, getAmountAsString(item.amount // part))
                    else:
                        subText += u"   - %s (%s)\n" % (item.label, getAmountAsString(item.amount // part))
                    total += item.amount // part
                if balance != 0:
                    subText += u"   ? (Auto-répartition) %s\n" % getAmountAsString(balance // len(allPersons))
                    total += balance // len(allPersons)
                text += u" - %s (Total : %s)\n" % (person.name, getAmountAsString(total))
                text += subText
            elif balance != 0:
                text += u" - %s : %s (Auto-répartition)\n" % (person.name, getAmountAsString(balance // len(allPersons)))
            else:
                text += u" - %s (Paiement uniquement)\n" % person.name
        return text

    def text_title(self, text):
        text += "%s (%s)\n" % (self.outlay.label, self.outlay.date)
        text += "%s\n\n" % "-" * len(self.outlay.label)

    def text_balance(self, text):
        balance = self.outlay.getBalance()
        if balance > 0:
            text += u"Achats manquants :\n"
            text += u"Répartition auto de %s.\n" % getAmountAsString(balance)
        elif balance < 0:
            text += u"Erreur : les paiments ne couvrent pas les achats !\n"
            text += u"Total : %s Manque : %s\n" % (
                getAmountAsString(self.outlay.getItemsTotalAmount()),
                getAmountAsString(-balance)
            )
        return text

    def refreshText(self):
        text = self.text_involved(u"")
        text += "\n"
        text = self.text_balance(text)
        self.field.setText(text)

    def layout(self, win):
        Widget.layout(self, win)
        self.refreshText()
        self.field.layout(win)

    def draw(self):
        self.field.draw()

    def onInput(self, ch, key):
        return self.field.onInput(ch, key)

    def onFocus(self):
        return self.field.onFocus()

    def onFocusLost(self):
        return self.field.onFocusLost()


class OutlayItemsManagementForm(Widget):
    """
        Left pane of the outlay
    """
    focusable = True
    def __init__(self, dm, outlay):
        self.dm = dm
        self.outlay = outlay
        self.menu = BaseMenu()
        self.newPersons = None
        self.onFocus()

    def layout(self, win):
        Widget.layout(self, win)
        self.menu.layout(win.derwin(0, 0))


    def onFocus(self):
        if self.newPersons is not None:
            self.outlay.persons.clear()
            self.outlay.persons.update(self.newPersons)
            self.newPersons = None
            db = getDB()
            db.saveDebtManager(self.dm)
        self.menu.refresh(self.getItems(), None, margin=0)

    def draw(self):
        self.menu.draw()


    def onInput(self, ch, key):
        action = self.menu.onInput(ch, key)
        item = self.menu.getSelectedItem()
        if action == "ACCEPT":
            if item == "edit_outlay":
                return OutlayEditForm(self.dm, self.outlay)
            if item == "new_item":
                item = sqlstorage.Item(set(), u"", 0)
            if isinstance(item, sqlstorage.Item):
                return ItemEditForm(self.dm, self.outlay, item)
            if item == "new_payment":
                item = sqlstorage.Payment(set(), 0)
            if isinstance(item, sqlstorage.Payment):
                return PaymentEditForm(self.dm, self.outlay, item)
            if item == "new_persons":
                self.newPersons = set(self.outlay.persons)
                return PersonChooserForm(self.dm, self.newPersons, excluded=frozenset(self.outlay.getPersons() - self.outlay.persons))
            if isinstance(item, sqlstorage.Person):
                return PersonEditForm(self.dm, item)

        elif action == "DELETE":
            item = self.menu.getSelectedItem()
            if isinstance(item, sqlstorage.Item):
                self.outlay.items.remove(item)
            elif isinstance(item, sqlstorage.Payment):
                self.outlay.payments.remove(item)
            elif isinstance(item, sqlstorage.Person):
                self.outlay.persons.remove(item)
            db = getDB()
            db.saveDebtManager(self.dm)
            self.onFocus()
            return "LAYOUT"
        else:
            return action

    def getItems(self):
        items = []
        items.append((u"- Modifier cette dépense...", "edit_outlay"))
        items.append((u"- Nouvel achat...", "new_item"))
        i = [(u"%s - %s (%s)" % (i.label, getAmountAsString(i.amount), getPersonsAsString(i.persons)), i) for i in self.outlay.items]
        i.sort()
        items.extend(i)
        items.append((u"- Nouveau paiment...", "new_payment"))
        i = [(u"%s (%s)" % (getAmountAsString(p.amount), getPersonsAsString(p.persons)), p) for p in self.outlay.payments]
        i.sort(lambda a, b: cmp(a[1].amount, b[1].amount))
        items.extend(i)
        items.append((u"- Participants supplémentaires...", "new_persons"))
        i = [(u"%s" % p.name, p) for p in self.outlay.persons]
        i.sort()
        items.extend(i)
        #import sys
        #print >>sys.stderr, items

        return items



class PersonChooserField(Widget):
    """
        This is a simple widget that allow user to call the PersonChooserForm by pressing enter
    """
    focusable = True
    def __init__(self, dm, label, persons, unique=False):
        self.dm = dm
        self.label = label
        self.persons = set(persons)
        self.unique = unique

    def getPreferredSize(self):
        return 1, 1000

    def draw(self):
        text = self.label + ", ".join([p.name for p in self.persons]) + u"  [Entrée pour choisir...]"
        self.drawStr(text)
        self.win.move(0, len(self.label))
        self.win.cursyncup()

    def onInput(self, ch, key):
        if key == "KEY_LEFT":
            pass
        elif key == "KEY_RIGHT":
            pass
        elif key == "KEY_BACKSPACE":
            pass
        elif key == "KEY_DC": # del
            pass
        elif key == "KEY_HOME":
            pass
        elif key == "KEY_END":
            pass
        elif key == "KEY_RETURN":
            return PersonChooserForm(self.dm, self.persons, unique=self.unique)
        elif key == "KEY_ESCAPE":
            return "CANCEL"
        elif key in ("KEY_TAB", "KEY_DOWN"):
            return "FOCUS_NEXT"
        elif key in ("KEY_BTAB", "KEY_UP"):
            return "FOCUS_PREVIOUS"
        else:
            return None
        return "OK"


import sys
class PersonChooserForm(BaseForm):
    def __init__(self, dm, persons, excluded = frozenset(), unique=False):
        self.dm = dm
        self.persons = persons
        self.newPerson = None
        self.excluded = frozenset(excluded)
        self.stack = StackedFields(nextOnAccept=False)
        self.unique = unique

    def getAllPersons(self):
        result = set(self.dm.getPersons())
        result -= self.excluded

        if self.newPerson is not None:
            if len(self.newPerson.name) != 0:
                if self.unique:
                    self.persons.clear()
                self.persons.add(self.newPerson)
            self.newPerson = None
        result.update(self.persons)
        result = list(result)
        result.sort(lambda x, y: cmp(x.name, y.name))
        return result

    def updateSelectedPersons(self):
        self.persons.clear()
        for person, field in self.fields:
            if field.state:
                self.persons.add(person)

    def onFocus(self):
        self.fields = []
        self.stack.clear()

        for person in self.getAllPersons():
            field = Checkbox(person.name, unique=self.unique)
            field.state = person in self.persons
            self.fields.append((person, field))
            self.stack.add(field)

        if self.unique and len(self.persons) == 0 and len(self.fields) > 0:
            person, field = self.fields[0]
            self.persons.add(person)
            field.state = True

        self.stack.add(Label(u""))
        self.stack.add(ActivableLabel(u"Valider", "ACCEPT_FORM"))
        self.stack.add(ActivableLabel(u"Ajouter une personne...", "ADD_PERSON"))

    def layout(self, win):
        self.stack.layout(win)

    def draw(self):
        self.stack.draw()

    def onInput(self, ch, key):
        if self.unique and self.stack.currentField in [f[1] for f in self.fields]:
            if key in ("KEY_BACKSPACE", "KEY_DC", ):
                return "OK"
            elif key in ("KEY_IC", "X", "x", "KEY_RETURN", "KEY_SPACE"):
                for person, field in self.fields:
                    field.state = False

        action = self.stack.onInput(ch, key)
        if action == "ADD_PERSON":
            self.newPerson = sqlstorage.Person(u"")
            return PersonEditForm(self.dm, self.newPerson)
        elif action == "OK":
            self.updateSelectedPersons()
        elif action in ("ACCEPT", "ACCEPT_FORM"):
            self.updateSelectedPersons()
            return 1
        elif action == "FOCUS_NEXT":
            self.stack.onFocus(first=True)
        elif action == "FOCUS_PREVIOUS":
            self.stack.onFocus(last=True)
        else:
            return BaseForm.onInput(self, ch, key)
        return "OK"

class PersonEditForm(BaseForm):
    def __init__(self, dm, person):
        self.dm = dm
        self.person = person
        self.stack = StackedFields()
        self.nameField = InputField(u"Nom : ", self.person.name)
        self.errorField = Label("")
        self.stack.add(self.nameField)

    def layout(self, win):
        self.win = win
        xmax = win.getmaxyx()[1]
        self.workspace = self.win.derwin(len(self.stack), xmax, 5, 0)
        self.stack.layout(self.workspace)

    def draw(self):
        self.drawTitle(u"Édition d'une personne", WHITE)
        self.stack.draw()

    def onInput(self, ch, key):
        action = self.stack.onInput(ch, key)
        if action == "ACCEPT":
            self.person.name = self.nameField.getUserInput()
            db = getDB()
            try:
                db.saveDebtManager(self.dm)
                return 1
            except Exception, e:
                self.errorField.setText(e)
                db.getSession().rollback()
                return "OK"
        elif action == "CANCEL":
            return 1
        elif action == "FOCUS_NEXT":
            self.stack.onFocus(first=True)
            return "OK"
        elif action == "FOCUS_PREVIOUS":
            self.stack.onFocus(last=True)
            return "OK"
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        return action


class ItemEditForm(BaseForm):
    def __init__(self, dm, outlay, item):
        self.outlay = outlay
        self.dm = dm
        self.item = item

        self.labelField = InputField(u"Intitulé : ", item.label)
        self.amountField = InputField(u"Montant : ", getAmountAsString(item.amount) if item.amount != 0 else u"")
        self.personsField = PersonChooserField(self.dm, u"Qui ? ", item.persons)
        #self.personsField = Label(1, 30)
        #self.personsField.setText(u"PersonChooserField à écrire !")
        self.errorField = Label("")
        self.errorString = u""

        self.fields = StackedFields()
        self.fields.add(self.labelField)
        self.fields.add(self.amountField)
        self.fields.add(self.errorField)
        self.fields.add(self.personsField)
        self.fields.add(Label(u""))
        self.fields.add(ActivableLabel(u"Valider"))

    def layout(self, win):
        Widget.layout(self, win)
        self.fields.layout(win.derwin(0, 0))

    def draw(self):
        self.fields.draw()

    def onInput(self, ch, key):
        self.errorField.setText(self.errorString, WHITE)
        action = self.fields.onInput(ch, key)
        if action == "ACCEPT":
            try:
                self.item.label = self.labelField.getUserInput()

                amount = self.amountField.getUserInput().strip()
                if len(amount) > 0:
                    RE = ur"^ *(\d+)(?:[,.](\d{1,2}))?(?: *€? *)?$"
                    result = re.findall(RE, amount)
                    euros = result[0][0]
                    cents = result[0][1]
                    if len(cents) == 0:
                        cents = 0

                    amount = int(euros) * 100 + int(cents)
                else:
                    amount = 0
                    
                self.item.amount = amount
                self.item.persons = self.personsField.persons

                if self.item not in self.outlay.items:
                    self.outlay.items.add(self.item)
                db = getDB()
                db.saveDebtManager(self.dm)
                return 1
            except IndexError:
                self.errorString = u"Veuillez entrer un montant valide (15.55 par exemple)."
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.fields.onFocus()
            except Exception, e:
                self.errorString = e.args[0].decode(ENCODING)
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.fields.onFocus()
        elif action == "CANCEL":
            return 1
        elif action == "FOCUS_NEXT":
            self.fields.onFocus(first=True)
        elif action == "FOCUS_PREVIOUS":
            self.fields.onFocus(last=True)
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        else:
            return action
        return "OK"


class PaymentEditForm(BaseForm):
    def __init__(self, dm, outlay, payment):
        self.outlay = outlay
        self.dm = dm
        self.payment = payment

        self.amountField = InputField(u"Montant payé : ", getAmountAsString(payment.amount) if payment.amount != 0 else u"")
        self.personsField = PersonChooserField(self.dm, u"Par qui ? ", payment.persons)
        self.errorField = Label("")
        self.errorString = u""

        self.fields = StackedFields()
        self.fields.add(self.amountField)
        self.fields.add(self.errorField)
        self.fields.add(self.personsField)
        self.fields.add(Label(u""))
        self.fields.add(ActivableLabel(u"Valider"))

    def layout(self, win):
        Widget.layout(self, win)
        self.fields.layout(win.derwin(0, 0))

    def draw(self):
        self.fields.draw()

    def onInput(self, ch, key):
        self.errorField.setText(self.errorString, WHITE)
        action = self.fields.onInput(ch, key)
        if action == "ACCEPT":
            try:
                amount = self.amountField.getUserInput().strip()
                if len(amount) > 0:
                    RE = ur"^ *(\d+)(?:[,.](\d{1,2}))?(?: *€? *)?$"
                    result = re.findall(RE, amount)
                    euros = result[0][0]
                    cents = result[0][1]
                    if len(cents) == 0:
                        cents = 0

                    amount = int(euros) * 100 + int(cents)
                else:
                    amount = 0

                self.payment.amount = amount
                self.payment.persons = self.personsField.persons

                if self.payment not in self.outlay.payments:
                    self.outlay.payments.add(self.payment)
                db = getDB()
                db.saveDebtManager(self.dm)
                return 1
            except IndexError:
                self.errorString = u"Veuillez entrer un montant valide (15.55 par exemple)."
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.fields.onFocus()
            except Exception, e:
                self.errorString = e.args[0].decode(ENCODING)
                self.errorField.setText(self.errorString, RED | curses.A_BOLD)
                self.fields.onFocus()
        elif action == "CANCEL":
            return 1
        elif action == "FOCUS_NEXT":
            self.fields.onFocus(first=True)
        elif action == "FOCUS_PREVIOUS":
            self.fields.onFocus(last=True)
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        else:
            return action
        return "OK"


class OutlayManagementForm(BaseForm):
    def __init__(self, dm, outlay):
        self.outlay = outlay
        self.dm = dm

        self.leftPane = OutlayItemsManagementForm(self.dm, self.outlay)
        self.rightPane = OutlayDetailsForm(self.dm, self.outlay)

        self.splitter = Splitter()
        self.splitter.addLeftPane(self.leftPane, u"Dépenses : %s" % self.outlay.label)
        self.splitter.addRightPane(self.rightPane, u"Informations")

    def layout(self, win):
        self.splitter.layout(win)
        
    def draw(self):
        self.splitter.draw()

    def onInput(self, ch, key):
        action = self.splitter.onInput(ch, key)
        if action is None:
            return BaseForm.onInput(self, ch, key)
        elif action == "FOCUS_NEXT":
            self.splitter.onFocus()
        elif action == "FOCUS_PREVIOUS":
            self.splitter.onFocus()
        return action

    def onFocus(self):
        self.splitter.leftTitle = u"Dépenses : %s" % self.outlay.label
        self.splitter.onFocus()

class PotCommunCursesApplication(object):

    def __init__(self, mainWindow):
        self.form = WelcomeForm()
        self.formStack = []
        self.mainWindow = mainWindow
        self.workspace = self.createWorkspace()
        self.form.layout(self.workspace)
        self.mainWindow.notimeout(True)
        self.workspace.notimeout(True)
        self.workspace.keypad(True)
        self.lastKey = "None"

    def createWorkspace(self):
        return self.mainWindow.derwin(2, 0)

    def drawAppTitle(self, win, title):
        my, mx = win.getmaxyx()
        x = mx // 2 - len(title) // 2
        win.addstr(0, x, title.encode(ENCODING), WHITE | c.A_BOLD)
        for n in range(mx):
            win.addch(1, n, curses.ACS_HLINE, CYAN)

        win.addstr(0, mx - 1 - len(self.lastKey), self.lastKey, GREEN)

    def draw(self, resized):
        self.mainWindow.erase()
        self.drawAppTitle(self.mainWindow, u"Pot Commun V %s" % potcommun.__version__)

        if resized:
            del self.workspace
            self.workspace = self.createWorkspace()
            self.form.layout(self.workspace)
        self.form.draw()

    def formatKey(self, ch, key):

        if key is None:
            r = "None - XXX - XXX"
        else:
            r = key + " - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
        return r

    def main(self):
        ch = 0
        action = None
        while self.form:
            try:
                self.draw(action == "LAYOUT")
            except Exception, e:
                try:
                    self.mainWindow.addstr(0, 0, "EE " + e.args[0], RED | c.A_BOLD)
                    self.mainWindow.addstr(2, 0, traceback.format_exc(), WHITE | c.A_BOLD)
                except:
                    self.mainWindow.addstr(0, 0, "EE", RED | c.A_BOLD)

            curses.doupdate()
            ch, key = self.prompt()
            self.lastKey = self.formatKey(ch, key)
            if key is None:
                return 1
            action = self.form.onInput(ch, key)
            if action == "QUIT":
                return 0
            elif type(action) == type(1):
                try:
                    for i in range(action):
                        self.form = self.formStack.pop()
                        #import sys
                        #print >>sys.stderr, self.form
                    self.form.onFocus()
                    action = "LAYOUT"
                except IndexError:
                    return 0
            elif isinstance(action, BaseForm):
                self.formStack.append(self.form)
                self.form = action
                self.form.onFocus()
                action = "LAYOUT"
            if ch == curses.KEY_RESIZE:
                action = "LAYOUT"


    def prompt(self):
        ## See http://bugs.python.org/issue1687125
        try:
            try:
                ch = -1
                while ch == -1:
                    ch = self.mainWindow.getch()
                    if ch == -1:
                        curses.doupdate()
                        continue
                    curses.ungetch(ch)
                    try:
                        key = self.mainWindow.getkey()
                    except Exception, e:
                        key = str(e.args)

                if ch == 13:
                    key = "KEY_RETURN"
                elif ch == 27:
                    key = "KEY_ESCAPE"
                elif ch == 9:
                    key = "KEY_TAB"
                elif ch == 32:
                    key = "KEY_SPACE"

                return ch, key
            except KeyboardInterrupt:
                return None, None
        except KeyboardInterrupt:
            return None, None


def purgeUselessPersons():
    # Yes, it's quick and dirty :
    # We have to remove useless persons that can't be removed
    # by sqlalchemy cascading feature due to the fact that
    # persons can be inserted in abstract payments, but in
    # transactions too.

    # It is easier to work at the table level.

    dmPersons = set()
    for dm in getDB().getManagers():
        dmPersons.update([p.oid for p in dm.getPersons()])
    engine = getDB().engine
    from sqlalchemy.sql import select
    result = engine.execute(select([sqlstorage.Person.oid]))
    allPersons = set([r[0] for r in result])
    uselessPersons = allPersons - dmPersons
    for p in uselessPersons:
        engine.execute(sqlstorage.Person.__table__.delete().where(sqlstorage.Person.oid == p))

_db = None
def getDB():
    global _db
    if _db is None:
        _db = sqlstorage.Handler(echo=False)
    return _db


def main(mainWindow):
    init_forms()
    global RED, GREEN, BLUE, YELLOW, MAGENTA, CYAN, WHITE
    RED = curses.color_pair(1)
    GREEN = curses.color_pair(2)
    BLUE = curses.color_pair(3)
    YELLOW = curses.color_pair(4)
    MAGENTA = curses.color_pair(5)
    CYAN = curses.color_pair(6)
    WHITE = curses.color_pair(7)

    app = PotCommunCursesApplication(mainWindow)

    app.main()

    purgeUselessPersons()

curses.wrapper(main)

