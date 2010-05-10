#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import curses
import curses.wrapper
import potcommun

## Tip : export ESCDELAY var to reduce time to interpret escape key

class BaseForm(object):
    def draw(self, win):
        """
            Draw the screen of the form
        """
        win.erase()

    def onInput(self, ch, key):
        """
            Called when an input has been received
            @return the new form to display (self is right), or None to quit
        """
        # noop
        return self

class WelcomeForm(BaseForm):
    def draw(self, win):
        BaseForm.draw(self, win)
        title = "Bienvenue ! Appuyez sur Entrée pour commencer."
        my, mx = win.getmaxyx()
        x = mx // 2 - len(title) // 2
        y = my // 2
        win.addstr(y, x, title, curses.COLOR_YELLOW)

    def onInput(self, ch, key):
        return self

class PotCommunCursesApplication(object):

    def __init__(self, mainWindow):
        self.form = WelcomeForm()
        self.mainWindow = mainWindow
        self.workspace = self.createTitle()
        self.mainWindow.notimeout(True)
        self.workspace.notimeout(True)
        self.workspace.keypad(True)
        self.lastKey = "None"

    def createTitle(self):
        return self.mainWindow.subwin(2, 0)

    def draw(self):
        self.mainWindow.erase()
        title = "Pot Commun V %s" % potcommun.__version__
        my, mx = self.mainWindow.getmaxyx()
        x = mx // 2 - len(title) // 2
        self.mainWindow.addstr(0, x, title, curses.COLOR_WHITE | curses.A_BOLD)
        for n in range(mx):
            self.mainWindow.addch(1, n, curses.ACS_HLINE)
        my, mx = self.mainWindow.getmaxyx()
        self.mainWindow.addstr(0, mx - 1 - len(self.lastKey), self.lastKey, curses.COLOR_GREEN)
        self.form.draw(self.workspace)

        self.mainWindow.noutrefresh()
        self.workspace.noutrefresh()

    def main(self):
        while self.form:
            ch, key = self.prompt()
            if key is None:
                return 1
            elif ch == 13:
                self.lastKey = "RETURN - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
            else:
                self.lastKey = key + " - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
            self.form.onInput(ch, key)

    def prompt(self):
        ## See http://bugs.python.org/issue1687125
        try:
            try:
                self.draw()
                curses.doupdate()
                ch = self.mainWindow.getch()
                curses.ungetch(ch)
                key = self.mainWindow.getkey()
                return ch, key
            except KeyboardInterrupt:
                return None, None
        except KeyboardInterrupt:
            return None, None


def main(mainWindow):
    curses.nonl()
    app = PotCommunCursesApplication(mainWindow)
    app.main()

curses.wrapper(main)
