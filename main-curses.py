#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import curses
import curses as c
import curses.wrapper
import potcommun
import traceback

import sqlstorage

import locale
locale.setlocale(locale.LC_ALL, '')

## Tip : export ESCDELAY var to reduce time to interpret escape key (10 is fine)

class BaseForm(object):
    def draw(self, win):
        """
            Draw the screen of the form
        """
        win.erase()

    def onInput(self, ch, key):
        """
            Called when an input has been received
            @return the new form to display (self is right), or None to quit, or
            an int corresponding to the forms to unstack (usualy 1).
        """
        # noop
        if ch == 27:
            return 1
        elif key in ("q", "Q"):
            return None
        return self

    def drawBox(self, win, y, x, height, width, color):
        """
            Draw a box.

            Height must be a least 3 to have one line inside it. Same for width.
        """
        ## corners
        #win.addstr(0,0,str(width))

        my, mx = win.getmaxyx()
        if mx < x + width or my < y + height or x < 0 or y < 0:
            return

        win.addch(y, x, c.ACS_ULCORNER , WHITE)
        win.addch(y, x + width - 1, c.ACS_URCORNER , WHITE)
        win.addch(y + height - 1, x + width - 1, c.ACS_LRCORNER , WHITE)
        win.addch(y + height - 1, x, c.ACS_LLCORNER , WHITE)
        for n in range(width - 2):
            win.addch(y, x + n + 1, c.ACS_HLINE, WHITE)
            #win.addstr(y, x + n + 1, str(n)[-1], WHITE)
            win.addch(y + height - 1, x + n + 1, c.ACS_HLINE, WHITE)

        for n in range(height - 2):
            win.addch(y + n + 1, x, c.ACS_VLINE, WHITE)
            win.addch(y + n + 1, x + width - 1, c.ACS_VLINE, WHITE)

        #for i in range(60):
            #win.addstr(2, i, str(i)[-1], WHITE)
        #win.addstr(1,0,str(x + width - 1))

    def drawAutoResizeBox(self, win, y, height, margin, color):
        my, mx = win.getmaxyx()
        self.drawBox(win, y, margin, height, mx - margin * 2, color)
        return mx - margin * 2 - 4

    def drawMenu(self, win, items, selectedRow, color):
        maxlen = self.drawAutoResizeBox(win, 4, len(items) + 2, 4, WHITE)
        for i, item in enumerate(items):
            label = " " + item[0][:maxlen]
            label += " " * (maxlen - len(label))
            win.addstr(5 + i, 6, label, color | c.A_REVERSE if i == selectedRow else 0)


    def drawTitle(self, win, title, color):
        my, mx = win.getmaxyx()
        minWidth = len(title) + 3
        maxX = mx // 2 - minWidth // 2 - 1
        x = mx // 4 if mx // 4 < maxX else maxX
        width = mx // 2 if mx // 2 > minWidth else minWidth
        y = 0
        height = 3
        self.drawBox(win, y, x, height, width, WHITE)
        x = mx // 2 - len(title) // 2
        win.addstr(1, x, title, WHITE)

    def manageKeyMenu(self, key, total):
        if key == "KEY_DOWN":
            self.selected += 1
            self.selected %= total
        elif key == "KEY_UP":
            self.selected -= 1
            if self.selected < 0:
                self.selected = total - 1

class InputField(BaseForm):
    def __init__(self, prompt, y):
        self.prompt = prompt
        self.y = y
        self.pos = 0
        self.userInput = u""
        self.unicodeBuffer = ""

    def draw(self, win):
        win.addstr(self.y, 0, self.prompt + self.userInput.encode("utf-8"), WHITE)
        win.move(self.y, len(self.prompt) + self.pos)

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
    def draw(self, win):
        BaseForm.draw(self, win)
        title = "Bienvenue ! Appuyez sur Entrée pour commencer."
        my, mx = win.getmaxyx()
        x = mx // 2 - len(title) // 2
        y = my // 2
        win.addstr(y, x, title, YELLOW | c.A_BOLD)

    def onInput(self, ch, key):
        if ch == 27 or key in ('q', 'Q'):
            return 1
        elif ch == 13:
            return DebtManagerSelection()
        else:
            return self



class DebtManagerSelection(BaseForm):

    selected = 0

    def __init__(self):
        self.dms = None
        self.dmToBeDeleted = None

    def draw(self, win):
        BaseForm.draw(self, win)
        self.drawTitle(win, "Sélection du pot commun", WHITE)
        if self.dms is None:
            self.dms = self.getDMs()
        self.drawDM(win, self.dms)

    def drawDM(self, win, dms):
        if self.getSelectedDM() is self.dmToBeDeleted and self.dmToBeDeleted is not None:
            color = RED | c.A_BOLD
        else:
            color = WHITE
        self.drawMenu(win, dms, self.selected, color)

    def onInput(self, ch, key):
        if ch == 27:
            return 1
        elif key in ('q', 'Q'):
            return None
        elif key in ("KEY_DOWN", "KEY_UP"):
            self.dmToBeDeleted = None
            self.manageKeyMenu(key, len(self.dms))
        elif key == "KEY_RETURN":
            dm = self.getSelectedDM()
            if dm is None:
                self.dms = None
                return NewDebtManagerForm()
            elif dm == self.dmToBeDeleted:
                self.deleteDM(dm)
                self.dmToBeDeleted = None
                self.dms = None
            else:
                return DebtManagerForm(dm)
        elif key == "KEY_DC":
            dm = self.getSelectedDM()
            self.dmToBeDeleted = dm

        return self

    def getDMs(self):
        db = getDB()
        
        r = [(dm.name, dm) for dm in db.getManagers()]
        r.append(
            ("Nouveau pot commun...", None),
        )

        return r

    def getSelectedDM(self):
        return self.dms[self.selected][1]

    def deleteDM(self, dm):
        db = getDB()
        db.deleteDebtManager(dm)
        

class NewDebtManagerForm(BaseForm):

    def __init__(self):
        self.inputField = InputField("Nom : ", 5)

    def draw(self, win):
        self.drawTitle(win, "Nouveau pot commun", WHITE)
        self.inputField.draw(win)

    def onInput(self, ch, key):
        if self.inputField.onInput(ch, key):
            return self
        elif key == "KEY_RETURN":
            dm = sqlstorage.DebtManager(self.inputField.getUserInput())
            db = getDB()
            db.saveDebtManager(dm)
            return 1

class PotCommunCursesApplication(object):

    def __init__(self, mainWindow):
        self.form = WelcomeForm()
        self.formStack = []
        self.mainWindow = mainWindow
        self.workspace = self.createWorkspace()
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
        self.form.draw(self.workspace)

        self.mainWindow.noutrefresh()
        self.workspace.noutrefresh()

    def formatKey(self, ch, key):

        if key is None:
            r = "None - XXX - XXX"
        else:
            r = key + " - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
        fd = open("/tmp/log", "a")
        fd.write("-> %s" % r)
        fd.close()
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
                    except IndexError:
                        return 0
                else:
                    self.formStack.append(self.form)
                    self.form = newForm

    def prompt(self):
        ## See http://bugs.python.org/issue1687125
        try:
            try:
                fd = open("/tmp/log", "a")

                ch = -1
                while ch == -1:
                    ch = self.mainWindow.getch()
                    fd.write("ch -> %d\n" % (ch))
                    if ch == -1:
                        curses.doupdate()
                        fd.write("doupdate\n")
                        continue
                    curses.ungetch(ch)
                    try:
                        key = self.mainWindow.getkey()
                    except Exception, e:
                        key = str(e.args)
                    fd.write("key -> %s\n" % key)

                fd.write("\n")
                fd.close()
                if ch == 13:
                    key = "KEY_RETURN"
                elif ch == 27:
                    key = "KEY_ESCAPE"

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
