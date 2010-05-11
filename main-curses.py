#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import curses
import curses as c
import curses.wrapper
import potcommun
import traceback

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
    def draw(self, win):
        BaseForm.draw(self, win)
        self.drawTitle(win, "Sélection du pot commun", WHITE)

    def onInput(self, ch, key):
        if ch == 27 or key in ('q', 'Q'):
            return 1
        elif ch == 13:
            return self
        else:
            return self



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
        elif ch == 13:
            r = "RETURN - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
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

                return ch, key
            except KeyboardInterrupt:
                return None, None
        except KeyboardInterrupt:
            return None, None


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
