#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import  division

import curses
import curses as c
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
            @return the new form to display (self is right), or None to quit, or
            an int corresponding to the forms to unstack (usualy 1).
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
        win.addstr(y, x, title, YELLOW | c.A_BOLD)

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

    def draw(self, resized):
        self.mainWindow.erase()
        title = "Pot Commun V %s" % potcommun.__version__
        my, mx = self.mainWindow.getmaxyx()
        x = mx // 2 - len(title) // 2
        self.mainWindow.addstr(0, x, title, WHITE | c.A_BOLD)
        for n in range(mx):
            self.mainWindow.addch(1, n, curses.ACS_HLINE, WHITE)
        my, mx = self.mainWindow.getmaxyx()
        self.mainWindow.addstr(0, mx - 1 - len(self.lastKey), self.lastKey, CYAN)
        if resized:
            del self.workspace
            self.workspace = self.createWorkspace()
        self.form.draw(self.workspace)

        self.mainWindow.noutrefresh()
        self.workspace.noutrefresh()

    def formatKey(self, ch, key):
        fd = open("/tmp/log", "a")
        if key is None:
            r = "None - XXX - XXX"
        elif ch == 13:
            r = "RETURN - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
        else:
            r = key + " - " + str(ch) + " - '" + curses.unctrl(ch) + "'"
        fd.write(r + "\n")
        fd.close()

        return r



    def main(self):
        ch = 0
        while self.form:
            try:
                self.draw(ch == curses.KEY_RESIZE)
            except Exception, e:
                self.mainWindow.addstr(0, 0, "EE")

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
                ch = self.mainWindow.getch()
                if ch == -1:
                    ch = self.mainWindow.getch()
                curses.ungetch(ch)
                try:
                    key = self.mainWindow.getkey()
                except Exception, e:
                    key = str(e.args)
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
