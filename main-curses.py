#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import re

import curses
import curses as c
import curses.wrapper
import potcommun
import traceback
import datetime

import sqlstorage

import locale
locale.setlocale(locale.LC_ALL, '')

from forms import *

import sys
sys.stderr = open("/dev/pts/5", "w")
print >>sys.stderr, "\n" * 10

## Tip : export ESCDELAY var to reduce time to interpret escape key (10 is fine)

def getAmountAsString(amount):
    return u"%d,%02d €" % (amount // 100, amount % 100)

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
        self.onFocus()
        
    def getOutlays(self):
        r = [(o.label, o) for o in self.dm.transactions]
        r.append((u"Nouvelle dépense...", "new_outlay"))
        r.append((u"Nouveau remboursement...", "new_refund"))
        return r
        
    def layout(self, win):
        BaseForm.layout(self, win)
        self.menu.layout(self.win.derwin(4, 0))
       
    def draw(self):
        BaseForm.draw(self)
        self.drawTitle(u"Pot commun : %s" % self.dm.name, WHITE)
        self.menu.draw()
        
    def onInput(self, ch, key):
        action = self.menu.onInput(ch, key)
        if action == "DELETE":
            self.dm.transactions.remove(self.menu.getSelectedItem())
            db = getDB()
            db.saveDebtManager(self.dm)
            self.onFocus()
            return "OK"
        elif action == "ACCEPT":
            outlay = self.menu.getSelectedItem()
            if outlay is "new_outlay":
                outlay = sqlstorage.Outlay(datetime.datetime.now(), "")
                return OutlayEditForm(self.dm, outlay)
            return OutlayManagementForm(self.dm, outlay)
        else:
            return BaseForm.onInput(self, ch, key)

    def onFocus(self):
        self.outlays = self.getOutlays()
        self.menu.refresh(self.outlays)



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
                return NewDebtManagerForm()
            else:
                return DebtManagerForm(dm)
        elif action is None:
            return BaseForm.onInput(self, ch, key)

    def getDMs(self):
        db = getDB()
        
        r = [(dm.name, dm) for dm in db.getManagers()]
        r.append(
            (u"Nouveau pot commun...", None),
        )

        return r


    def deleteDM(self, dm):
        db = getDB()
        db.deleteDebtManager(dm)
        

class NewDebtManagerForm(BaseForm):

    def __init__(self):
        self.inputField = InputField(u"Nom : ")

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
            dm = sqlstorage.DebtManager(self.inputField.getUserInput())
            db = getDB()
            db.saveDebtManager(dm)
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
            self.stack.onFocus()
            return "OK"
        elif action == "FOCUS_PREVIOUS":
            self.stack.onFocus(last=True)
            return "OK"
        elif action is None:
            return BaseForm.onInput(self, ch, key)
        return action


class OutlayItemsManagementForm(Widget):
    """
        Left pane of the outlay
    """

    def __init__(self, dm, outlay):
        self.dm = dm
        self.outlay = outlay
        self.menu = BaseMenu()
        self.onFocus()

    def layout(self, win):
        Widget.layout(self, win)
        self.menu.layout(win.derwin(0, 0))


    def onFocus(self):
        self.menu.refresh(self.getItems(), 0)

    def draw(self):
        self.menu.draw()


    def onInput(self, ch, key):
        action = self.menu.onInput(ch, key)
        item = self.menu.getSelectedItem()
        if action == "ACCEPT":
            if item == "new_item":
                item = sqlstorage.Item(set(), u"", 0)
            if isinstance(item, sqlstorage.Item):
                return ItemEditForm(self.dm, self.outlay, item)
            if item == "new_payment":
                item = sqlstorage.Payment(set(), 0)
            if isinstance(item, sqlstorage.Payment):
                return PaymentEditForm(self.dm, self.outlay, item)
            if item == "new_persons":
                self.new_persons

        elif action == "DELETE":
            self.outlay.items.remove(item)
            db = getDB()
            db.saveDebtManager(self.dm)
            self.onFocus()
            return "OK"

    def getItems(self):
        items = []
        items.append((u"Nouvel achat...", "new_item"))
        items.extend([(u"%s - %s (%s)" % (i.label, getAmountAsString(i.amount), getPersonsAsString(i.persons)), i) for i in self.outlay.items])
        items.append((u"Nouveau paiment...", "new_payment"))
        items.extend([(u"%s (%s)" % (getAmountAsString(p.amount), getPersonsAsString(p.persons)), p) for p in self.outlay.payments])
        items.append((u"Nouveau participant...", "new_persons"))
        items.extend([(u"%s" % p.name, p) for p in self.outlay.persons])
        #import sys
        #print >>sys.stderr, items

        return items



class PersonChooserField(Widget):
    """
        This is a simple widget that allow user to call the PersonChooserForm by pressing enter
    """
    focusable = True
    def __init__(self, dm, label, persons):
        self.dm = dm
        self.label = label
        self.persons = set(persons)

    def getPreferredSize(self):
        return 1, 1000

    def draw(self):
        text = self.label + ", ".join([p.name for p in self.persons])
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
            return PersonChooserForm(self.dm, self.persons)
        elif key == "KEY_ESCAPE":
            return "CANCEL"
        elif key in ("KEY_TAB", "KEY_DOWN"):
            return "FOCUS_NEXT"
        elif key in ("KEY_BTAB", "KEY_UP"):
            return "FOCUS_PREVIOUS"
        else:
            return None
        return "OK"



class PersonChooserForm(BaseForm):
    def __init__(self, dm, persons):
        self.dm = dm
        self.persons = persons

    def getAllPersons(self):
        return set(self.dm.persons)

    def updateSelectedPersons(self):
        self.persons.clear()
        for person, field in self.fields:
            if field.state:
                self.persons.add(person)

    def onFocus(self):
        self.fields = []
        self.stack = StackedFields()

        for person in self.getAllPersons():
            field = Checkbox(person.name)
            field.state = person in self.persons
            self.fields.append((person, field))
            self.stack.add(field)

        self.stack.add(Label(u""))
        self.stack.add(ActivableLabel(u"Valider", "ACCEPT_FORM"))
        self.stack.add(ActivableLabel(u"Ajouter une personne...", "ADD_PERSON"))

    def layout(self, win):
        self.stack.layout(win)

    def draw(self):
        self.stack.draw()

    def onInput(self, ch, key):
        action = self.stack.onInput(ch, key)
        if action == "ADD_PERSON":
            return PersonEditForm(self.dm, sqlstorage.Person(u""))
        elif action in ("ACCEPT", "ACCEPT_FORM"):
            self.updateSelectedPersons()
            return 1
        elif action == "FOCUS_NEXT":
            self.stack.onFocus()
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
            if self.person not in self.dm.persons:
                self.dm.persons.add(self.person)
            db = getDB()
            db.saveDebtManager(self.dm)
            return 1

        elif action == "CANCEL":
            return 1
        elif action == "FOCUS_NEXT":
            self.stack.onFocus()
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
                    self.outlay.addItem(self.item)
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
            self.fields.onFocus()
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
                    self.outlay.addPayment(self.payment)
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
            self.fields.onFocus()
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

        self.splitter = Splitter()
        self.splitter.addLeftPane(self.leftPane, u"Dépenses : %s" % self.outlay.label)

    def layout(self, win):
        self.splitter.layout(win)
        
    def draw(self):
        self.splitter.draw()

    def onInput(self, ch, key):
        action = self.splitter.onInput(ch, key)
        if action is None:
            return BaseForm.onInput(self, ch, key)
        return action

    def onFocus(self):
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
        my, mx = win.getmaxyx()
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

curses.wrapper(main)

