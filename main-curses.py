#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import curses
import curses as c
import curses.wrapper
import potcommun
import traceback
import datetime

import sqlstorage

import locale
locale.setlocale(locale.LC_ALL, '')

## Tip : export ESCDELAY var to reduce time to interpret escape key (10 is fine)

class BaseForm(object):
    def draw(self):
        """
            Draw the screen of the form
        """
        self.win.erase()

    def layout(self, win):
        self.win = win

    def onInput(self, ch, key):
        """
            Called when an input has been received
            @return the new form to display (self is right), or None to quit, or
            an int corresponding to the forms to unstack (usualy 1).
        """
        if ch == 27:
            return 1
        elif key in ("q", "Q"):
            return None
        return self

    def onFocus(self):
        pass

    def drawBox(self, y, x, height, width, color):
        """
            Draw a box.

            Height must be a least 3 to have one line inside it. Same for width.
        """
        ## corners
        #win.addstr(0,0,str(width))

        my, mx = self.win.getmaxyx()
        if mx < x + width or my < y + height or x < 0 or y < 0:
            return

        self.win.addch(y, x, c.ACS_ULCORNER , WHITE)
        self.win.addch(y, x + width - 1, c.ACS_URCORNER , WHITE)
        self.win.addch(y + height - 1, x + width - 1, c.ACS_LRCORNER , WHITE)
        self.win.addch(y + height - 1, x, c.ACS_LLCORNER , WHITE)
        for n in range(width - 2):
            self.win.addch(y, x + n + 1, c.ACS_HLINE, WHITE)
            #win.addstr(y, x + n + 1, str(n)[-1], WHITE)
            self.win.addch(y + height - 1, x + n + 1, c.ACS_HLINE, WHITE)

        for n in range(height - 2):
            self.win.addch(y + n + 1, x, c.ACS_VLINE, WHITE)
            self.win.addch(y + n + 1, x + width - 1, c.ACS_VLINE, WHITE)

        #for i in range(60):
            #win.addstr(2, i, str(i)[-1], WHITE)
        #win.addstr(1,0,str(x + width - 1))

    def drawAutoResizeBox(self, y, height, margin, color):
        my, mx = self.win.getmaxyx()
        self.drawBox(y, margin, height, mx - margin * 2, color)
        return mx - margin * 2 - 4

    def drawTitle(self, title, color):
        my, mx = self.win.getmaxyx()
        minWidth = len(title) + 3
        maxX = mx // 2 - minWidth // 2 - 1
        x = mx // 4 if mx // 4 < maxX else maxX
        width = mx // 2 if mx // 2 > minWidth else minWidth
        y = 0
        height = 3
        self.drawBox(y, x, height, width, WHITE)
        x = mx // 2 - len(title) // 2
        self.win.addstr(1, x, title, WHITE)

    def drawStr(self, label, color=None):
        self.win.addstr(0, 0, label, color if color is not None else WHITE)

class Label(BaseForm):
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.text = ""
        self.color = WHITE
        
    def setText(self, text, color=None):
        self.text = (text[:self.width]).encode("utf-8")
        self.color = WHITE if color is None else color

    def draw(self):
        self.win.addstr(0, 0, self.text, self.color)

    def getSubwinParams(self, y, win):
        return self.height, self.width, y, 2

class BaseMenu(BaseForm):
    def __init__(self, items, selected=None):
        """
        items should be [(label, item), ..]
        """
        self.items = items
        self.total = len(items)
        if selected is not None:
            if type(selected) == type(1):
                self.selected = selected
            else:
                self.selected = [i for a, i in items].index(selected)
        else:
            self.selected = 0
        self.itemToBeDeleted = None
        
    def onInput(self, ch, key):
        if key == "KEY_DOWN":
            self.itemToBeDeleted = None
            self.selected += 1
            self.selected %= self.total
        elif key == "KEY_UP":
            self.itemToBeDeleted = None
            self.selected -= 1
            if self.selected < 0:
                self.selected = self.total - 1
        elif key == "KEY_RETURN":
            item = self.getSelectedItem()
            
            if item is not None and item == self.itemToBeDeleted:
                return "DELETE"
            else:
                return "ACCEPT"
        elif key == "KEY_DC":
            self.itemToBeDeleted = self.getSelectedItem()

    def getSelectedItem(self):
        return self.items[self.selected][1]

    def getSelectedIndex(self):
        return self.selected

    def draw(self):
        if self.getSelectedItem() is self.itemToBeDeleted and self.itemToBeDeleted is not None:
            color = RED | c.A_BOLD
        else:
            color = WHITE
        self.drawMenu(self.items, self.selected, color)
        
    def drawMenu(self, items, selectedRow, color):
        maxlen = self.drawAutoResizeBox(0, len(items) + 2, 4, WHITE)
        for i, item in enumerate(items):
            label = " " + item[0][:maxlen]
            label += " " * (maxlen - len(label))
            self.win.addstr(1 + i, 6, label, color | c.A_REVERSE if i == selectedRow else 0)

class StackedFields(BaseForm):
    def __init__(self):
        self.fields = []
        self.focus_ok = []
        self.focusedFieldIndex = 0
        
    def add(self, field, focusable=True):
        self.fields.append(field)
        self.focus_ok.append(focusable)
        
    def layout(self, win):
        self.win = win
        self.subwins = []
        y = 0
        for field in self.fields:
            params = field.getSubwinParams(y, win)
            subwin = self.win.derwin(*params)
            y += params[0] ## nb lines
            field.layout(subwin)
            self.subwins.append(subwin)
            
    def draw(self):
        for i, field in enumerate(self.fields):
            if i != self.focusedFieldIndex:
                field.draw()
        ## the focused field is drawn last
        self.fields[self.focusedFieldIndex].draw()
        self.win.addstr(self.focusedFieldIndex, 0, ">")

    def resetFocus(self):
        self.focusedFieldIndex = 0

    def onInput(self, ch, key):
        if key in ("KEY_TAB", "KEY_RETURN", "KEY_DOWN"):
            self.focusedFieldIndex += 1
            while self.focusedFieldIndex < len(self.fields) and\
                not self.focus_ok[self.focusedFieldIndex]:
                self.focusedFieldIndex += 1    
            if self.focusedFieldIndex == len(self.fields):
                return "ACCEPT" if key == "KEY_RETURN" else "LAST_FIELD_FOCUS"
        elif key in ("KEY_BTAB", "KEY_UP"):
            # Focus management has to be improved here
            self.focusedFieldIndex -= 1
            if self.focusedFieldIndex < 0:
                self.focusedFieldIndex = len(self.fields) - 1
        else:
            return self.fields[self.focusedFieldIndex].onInput(ch, key)
        return True

class InputField(BaseForm):
    def __init__(self, prompt, defaultValue=u""):
        if type(prompt) != type(u""):
            raise UnicodeError("prompt must be unicode")
        self.prompt = prompt
        self.pos = len(defaultValue)
        self.userInput = defaultValue
        self.unicodeBuffer = ""

    def draw(self):
        self.win.addstr(0, 0, (self.prompt + self.userInput).encode("utf-8"), WHITE)
        self.win.move(0, len(self.prompt) + self.pos)
        self.win.cursyncup()

    @staticmethod
    def getSubwinParams(y, win):
        xmax = win.getmaxyx()[1]
        return (1, xmax - 4, y, 2)

    def getUserInput(self):
        return self.userInput

    def onInput(self, ch, key):
        if ch >= 32 and ch < 256:
            self.unicodeBuffer += chr(ch)
            try:
                uc = self.unicodeBuffer.decode("utf-8")
                self.userInput = self.userInput[:self.pos] + uc + self.userInput[self.pos:]
                self.unicodeBuffer = ""
                self.pos += 1
            except UnicodeDecodeError:
                pass
            return True
        elif key == "KEY_LEFT":
            self.pos -= 1 if self.pos > 0 else 0
            return True
        elif key == "KEY_RIGHT":
            self.pos += 1 if self.pos < len(self.userInput) else 0
            return True
        elif key == "KEY_BACKSPACE":
            if self.pos > 0:
                self.userInput = self.userInput[:self.pos - 1] + self.userInput[self.pos:]
                self.pos -= 1
            return True
        elif key == "KEY_DC":
            if self.pos < len(self.userInput):
                self.userInput = self.userInput[:self.pos] + self.userInput[self.pos + 1:]
            return True
        elif key == "KEY_HOME":
            self.pos = 0
            return True
        elif key == "KEY_END":
            self.pos = len(self.userInput)
            return True

        return False

class WelcomeForm(BaseForm):
    def draw(self):
        BaseForm.draw(self)
        title = "Bienvenue ! Appuyez sur Entrée pour commencer."
        my, mx = self.win.getmaxyx()
        x = mx // 2 - len(title) // 2
        y = my // 2
        self.win.addstr(y, x, title, YELLOW | c.A_BOLD)

    def onInput(self, ch, key):
        if ch == 27 or key in ('q', 'Q'):
            return 1
        elif ch == 13:
            return DebtManagerSelection()
        else:
            return self


class DebtManagerForm(BaseForm):
    def __init__(self, dm):
        self.dm = dm
        self.onFocus()        
                
    def getOutlays(self):
        r = [(o.label.encode("utf-8"), o) for o in self.dm.outlays]
        r.append(("Nouvelle dépense...", None))
        return r
        
    def layout(self, win):
        BaseForm.layout(self, win)
        self.menu.layout(self.win.subwin(6, 0))
       
    def draw(self):
        BaseForm.draw(self)
        self.drawTitle("Pot commun : %s" % self.dm.name.encode("utf-8"), WHITE)
        self.menu.draw()
        
    def onInput(self, ch, key):
        action = self.menu.onInput(ch, key)
        if action == "DELETE":
            self.dm.outlays.remove(self.menu.getSelectedItem())
            db = getDB()
            db.saveDebtManager(self.dm)

            self.onFocus()
            self.layout(self.win)
            return self
        elif action == "ACCEPT":
            outlay = self.menu.getSelectedItem()
            if outlay is None:
                outlay = sqlstorage.Outlay(datetime.datetime.now(), "")
            return OutlayEditForm(self.dm, outlay)
        else:
            return BaseForm.onInput(self, ch, key)

    def onFocus(self):
        self.outlays = self.getOutlays()
        self.menu = BaseMenu(self.outlays)



class DebtManagerSelection(BaseForm):

    def __init__(self):
        self.dms = None
        self.dmToBeDeleted = None
        self.menu = None

    def onFocus(self):
        self.menu = BaseMenu(self.getDMs(), self.menu.getSelectedIndex() if self.menu is not None else 0)

    def layout(self, win):
        BaseForm.layout(self, win)
        self.menu.layout(self.win.subwin(6, 0))

    def draw(self):
        BaseForm.draw(self)
        self.drawTitle("Sélection du pot commun", WHITE)
        if self.dms is None:
            self.dms = self.getDMs()
        self.menu.draw()


    def onInput(self, ch, key):
        if ch == 27:
            return 1
        elif key in ('q', 'Q'):
            return None
        else:
            action = self.menu.onInput(ch, key)
            if action == "DELETE":
                self.deleteDM(self.menu.getSelectedItem())
                self.menu = BaseMenu(self.getDMs(), self.menu.getSelectedIndex())
                self.layout(self.win)
            elif action == "ACCEPT":
                dm = self.menu.getSelectedItem()
                if dm is None:
                    return NewDebtManagerForm()
                else:
                    return DebtManagerForm(dm)
 
        return self

    def getDMs(self):
        db = getDB()
        
        r = [(dm.name.encode("utf-8"), dm) for dm in db.getManagers()]
        r.append(
            ("Nouveau pot commun...", None),
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
        self.drawTitle("Nouveau pot commun", WHITE)
        self.inputField.draw()

    def onInput(self, ch, key):
        if self.inputField.onInput(ch, key):
            return self
        elif key == "KEY_RETURN":
            dm = sqlstorage.DebtManager(self.inputField.getUserInput())
            db = getDB()
            db.saveDebtManager(dm)
            return 1
        elif key == "KEY_ESCAPE":
            return 1
    	return self

class OutlayEditForm(BaseForm):
    def __init__(self, dm, outlay):
        self.dm = dm
        self.outlay = outlay
        self.stack = StackedFields()
        self.nameField = InputField(u"Nom : ", outlay.label)
        self.dateField = InputField(u"Date : ", unicode(outlay.date.strftime("%Y-%m-%d %H:%M:%S")))
        self.errorMsg = Label(1, 90)
        self.stack.add(self.nameField)
        self.stack.add(self.dateField)
        self.stack.add(self.errorMsg, focusable=False)
        
        
    def layout(self, win):
        self.win = win
        xmax = win.getmaxyx()[1]
        self.workspace = self.win.derwin(3, xmax, 5, 0)
        self.stack.layout(self.workspace)

    def draw(self):
        self.drawTitle("Édition d'une dépense", WHITE)
        self.stack.draw()
        
    def onInput(self, ch, key):
        self.errorMsg.setText(u"")
        action = self.stack.onInput(ch, key)
        if action == "ACCEPT":
            try:
                self.outlay.label = self.nameField.getUserInput()
                self.outlay.date = datetime.datetime.strptime(self.dateField.getUserInput(), "%Y-%m-%d %H:%M:%S")
                self.dateField.getUserInput()
                if self.outlay not in self.dm.outlays:
                    self.dm.outlays.add(self.outlay)
                db = getDB()
                db.saveDebtManager(self.dm)
                return 1
            except Exception, e:
                self.errorMsg.setText(e.args[0].decode("utf-8"), RED)
                self.stack.resetFocus()
                return self                
            
            
        if action == "LAST_FIELD_FOCUS":
            self.stack.resetFocus()
            return self
        elif action is True:
            return self
        else:
            return 1


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
        return self.mainWindow.subwin(2, 0)

    def drawAppTitle(self, win, title):
        my, mx = win.getmaxyx()
        x = mx // 2 - len(title) // 2
        win.addstr(0, x, title, WHITE | c.A_BOLD)
        for n in range(mx):
            win.addch(1, n, curses.ACS_HLINE, CYAN)
        my, mx = win.getmaxyx()
        win.addstr(0, mx - 1 - len(self.lastKey), self.lastKey, GREEN)

    def draw(self, resized):
        self.mainWindow.erase()
        self.drawAppTitle(self.mainWindow, "Pot Commun V %s" % potcommun.__version__)

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
            newForm = self.form.onInput(ch, key)
            if self.form is not newForm:
                if newForm is None:
                    return 0
                if type(newForm) == type(1):
                    try:
                        for i in range(newForm):
                            self.form = self.formStack.pop()
                            self.form.onFocus()
                    except IndexError:
                        return 0
                else:
                    self.formStack.append(self.form)
                    self.form = newForm
                    self.form.onFocus()
                self.form.layout(self.workspace)

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
    curses.nonl()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_RED, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_BLUE, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_MAGENTA, -1)
    curses.init_pair(6, curses.COLOR_CYAN, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)
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

