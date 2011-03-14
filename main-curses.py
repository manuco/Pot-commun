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
sys.stderr = open("/dev/pts/6", "w")
print >>sys.stderr, "\n" * 10

## Tip : export ESCDELAY var to reduce time to interpret escape key (10 is fine)

def getAmountAsString(amount):
    return u"%d,%02d €" % (amount // 100, amount % 100)

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
        self.inputField.layout(win.derwin(*InputField.getSubwinParams(5, win)))

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
        self.errorMsg = Label(1, 90)
        self.errorString = ""
        self.stack.add(self.nameField)
        self.stack.add(self.dateField)
        self.stack.add(self.errorMsg)

    def layout(self, win):
        self.win = win
        xmax = win.getmaxyx()[1]
        self.workspace = self.win.derwin(3, xmax, 5, 0)
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

        elif action == "FOCUS_NEXT":
            self.stack.onFocus()
            return "OK"
        elif action == "FOCUS_PREVIOUS":
            self.stack.onFocus(last=True)
            return "OK"
        else:
            return BaseForm.onInput(self, ch, key)


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
            return ItemEditForm(self.dm, self.outlay, item)
        elif action == "DELETE":
            self.outlay.items.remove(item)
            db = getDB()
            db.saveDebtManager(self.dm)
            self.onFocus()
            return "OK"

    def getItems(self):
        items = [
            (u"Nouvel élément...", "new_item"),
            (u"Nouveau paiment...", "new_payment"),
        ]

        items.extend([(u"%s (%s)" % (i.label, getAmountAsString(i.amount)), i) for i in self.outlay.items])

        #import sys
        #print >>sys.stderr, items

        return items


class PersonChooserField(Widget):
    pass

class ItemEditForm(BaseForm):
    def __init__(self, dm, outlay, item):
        self.outlay = outlay
        self.dm = dm
        self.item = item

        self.labelField = InputField(u"Intitulé : ", item.label)
        self.amountField = InputField(u"Montant : ", getAmountAsString(item.amount) if item.amount != 0 else u"")
        self.personsField = PersonChooserField(u"Qui ? ", item.label)
        #self.personsField = Label(1, 30)
        #self.personsField.setText(u"PersonChooserField à écrire !")
        self.errorField = Label(1, 90)
        self.errorString = u""

        self.fields = StackedFields()
        self.fields.add(self.labelField)
        self.fields.add(self.amountField)
        self.fields.add(self.errorField)
        self.fields.add(self.personsField)

    def layout(self, win):
        Widget.layout(self, win)
        self.fields.layout(win.derwin(0, 0))

    def draw(self):
        self.fields.draw()

    def onInput(self, ch, key):
        self.errorField.setText(self.errorString, WHITE)
        action = self.fields.onInput(ch, key)
        if action == "ACCEPT":
            pass
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
            self.fields.onFocus()
        elif action == "FOCUS_PREVIOUS":
            self.fields.onFocus(last=True)
            
        elif action is None:
            return BaseForm.onInput(self, ch, key)
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
        while self.form:
            try:
                self.draw(ch == curses.KEY_RESIZE)
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
                        # force new layout
                        ch = curses.KEY_RESIZE
                except IndexError:
                    return 0
            elif isinstance(action, BaseForm):
                self.formStack.append(self.form)
                self.form = action
                self.form.onFocus()
                # force new layout
                ch = curses.KEY_RESIZE


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

