# -*- coding: utf-8 -*-
import curses
import curses as c
import curses.wrapper

ENCODING = "utf-8"

def init_forms():
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


class Widget(object):
    focusable = False
    def drawBox(self, y, x, height, width, color=None):
        """
            Draw a box.

            Height must be a least 3 to have one line inside it. Same for width.
        """
        ## corners
        color = WHITE if color is None else color
        my, mx = self.win.getmaxyx()
        if mx < x + width or my < y + height or x < 0 or y < 0:
            return

        self.win.addch(y, x, c.ACS_ULCORNER , color)
        self.win.addch(y, x + width - 1, c.ACS_URCORNER , color)
        try: # The lower right caracter raises an exception, but is drawn...
            self.win.addch(y + height - 1, x + width - 1, c.ACS_LRCORNER , color)
        except Exception:
            pass
        self.win.addch(y + height - 1, x, c.ACS_LLCORNER , color)
        for n in range(width - 2):
            self.win.addch(y, x + n + 1, c.ACS_HLINE, color)
            self.win.addch(y + height - 1, x + n + 1, c.ACS_HLINE, color)

        for n in range(height - 2):
            self.win.addch(y + n + 1, x, c.ACS_VLINE, color)
            self.win.addch(y + n + 1, x + width - 1, c.ACS_VLINE, color)

    def drawAutoResizeBox(self, y, height, margin, color):
        my, mx = self.win.getmaxyx()
        self.drawBox(y, margin, height, mx - margin * 2, color)
        return mx - margin * 2 - 4

    def drawTitle(self, title, color=None):
        if title is None:
            return
        color = WHITE if color is None else color
        my, mx = self.win.getmaxyx()
        minWidth = len(title) + 3
        maxX = mx // 2 - minWidth // 2 - 1
        x = mx // 4 if mx // 4 < maxX else maxX
        width = mx // 2 if mx // 2 > minWidth else minWidth
        y = 0
        height = 3
        self.drawBox(y, x, height, width, color)
        x = mx // 2 - len(title) // 2
        self.win.addstr(1, x, title.encode(ENCODING), color)

    def drawStr(self, label, color=None):
        self.win.addstr(0, 0, label.encode(ENCODING), color if color is not None else WHITE)

    def onInput(self, ch, key):
        """
            return
            None if key was not handled
            a new *BaseForm* if a new baseform has to be stacked
            an integer if one or more baseform has to be unstack
            "OK" if key was succesfully handled, and no more action has to be performed
            "QUIT" if user request exiting
            "FOCUS_NEXT" if the widget gives its focus to its next widget
            "FOCUS_PREVIOUS" if the widget gives its focus to its previous widget
            or others strings given the action to perform.
        """
        return None


    def draw(self):
        """
            Draw the form on the screen.

            Should be implemented by any child
        """
        self.win.erase()

    def layout(self, win):
        """
            Called when the form layout has changed. You should recompute your geometry.

            To be implemented by any child
        """
        self.win = win

    def onFocus(self):
        """
            Called when your form will receive onInputEvents.

            Should be implemented by any child
        """
        pass

    def onFocusLost(self):
        """
            Called when your form will stop receiving onInputEvents.

            Should be implemented by any child
        """
        pass


class BaseForm(Widget):
    """
        The base form is the base of any forms.

        It should implemtents the 4 following methods.

    """

    def onInput(self, ch, key):
        """
            Called when an input has been received
            @return the new form to display (self is right), or None to quit, or
            an int corresponding to the forms to unstack (usualy 1).

            To be implemented by any child
        """
        if ch == 27:
            return 1
        elif key in ("q", "Q"):
            return "QUIT"
        return None


class Label(Widget):
    def __init__(self, height, width):
        self.height = height
        self.width = width
        self.text = ""
        self.color = WHITE

    def setText(self, text, color=None):
        self.text = text[:self.width]
        self.color = WHITE if color is None else color

    def draw(self):
        self.win.addstr(0, 0, self.text.encode(ENCODING), self.color)

    def getSubwinParams(self, y, win):
        return self.height, self.width, y, 2

class BaseMenu(Widget):

    selected = 0
    focusable = True

    def refresh(self, items, selected=None):
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

            if item is not None and item is self.itemToBeDeleted:
                return "DELETE"
            else:
                return "ACCEPT"
        elif key == "KEY_DC":
            item = self.getSelectedItem()
            if item is not None and type(item) != type(""):
                self.itemToBeDeleted = item
        elif key == "KEY_TAB":
            return "FOCUS_NEXT"
        elif key == "KEY_BTAB":
            return "FOCUS_PREVIOUS"
        else:
            return None
        return "OK"

    def getSelectedItem(self):
        return self.items[self.selected][1]

    def getSelectedIndex(self):
        return self.selected

    def draw(self):
        if self.getSelectedItem() is self.itemToBeDeleted and self.itemToBeDeleted is not None:
            color = RED
        else:
            color = WHITE
        self.drawMenu(self.items, self.selected, color)

    def drawMenu(self, items, selectedRow, color):
        maxlen = self.drawAutoResizeBox(0, len(items) + 2, 4, WHITE)
        for i, item in enumerate(items):
            label = " " + item[0][:maxlen]
            label += " " * (maxlen - len(label))
            self.win.addstr(1 + i, 6, label.encode(ENCODING), color | c.A_REVERSE if i == selectedRow else 0)

class Splitter(Widget):
    def __init__(self):
        self.focusLeftPane = True
        self.leftPane = BaseForm()
        self.rightPane = BaseForm()
        self.leftColor = WHITE
        self.rightColor = WHITE
        self.leftTitle = None
        self.rightTitle = None

    @property
    def focusable(self):
        return self.leftPane.focusable or self.rightPane.focusable

    def addLeftPane(self, field, title=None, color=None):
        self.leftPane = field
        self.leftTitle = title
        self.leftColor = WHITE if color is None else color

    def layout(self, win):
        self.win = win
        self.xmax = xmax = win.getmaxyx()[1]
        self.ymax = ymax = win.getmaxyx()[0]

        middle = xmax // 2

        self.leftWin = win.derwin(ymax - 2, middle - 4, 1, 2)
        self.rightWin = win.derwin(ymax - 2, middle - 4, 1, middle + 2)
        if self.leftPane is not None:
            self.leftPane.layout(self.leftWin)
        if self.rightPane is not None:
            self.rightPane.layout(self.rightWin)


    def draw(self):
        middle = self.xmax // 2
        self.drawBox(0, 0, self.ymax, middle, RED)
        self.drawBox(0, middle, self.ymax, middle, GREEN)

        x = middle // 2 - len(self.leftTitle + u"  ") // 2
        if self.leftTitle is not None:
            self.win.addstr(0, x, " " + self.leftTitle.encode(ENCODING) + " ", WHITE)

        self.leftPane.draw()
        self.rightPane.draw()

    def onInput(self, ch, key):
        if self.focusLeftPane:
            action = self.leftPane.onInput(ch, key)
        else:
            action = self.rightPane.onInput(ch, key)

        if action in ("FOCUS_NEXT", "FOCUS_PREVIOUS"):
            focusedPane = self.leftPane if action == "FOCUS_NEXT" else self.rightPane
            paneToFocus = self.leftPane if action == "FOCUS_PREVIOUS" else self.rightPane
            self.focusLeftPane = action == "FOCUS_PREVIOUS"

            focusedPane.lostFocus()
            if paneToFocus.focusable:
                paneToFocus.onFocus()
            else:
                return action
        else:
            return action

    def onFocus(self):
        if self.focusLeftPane:
            self.leftPane.onFocus()
        else:
            self.rightPane.onFocus()


class StackedFields(Widget):

    def __init__(self):
        self.fields = []
        self.focusedFieldIndex = 0

    @property
    def focusable(self):
        for field in self.fields:
            if field.focusable:
                return True
        return False

    def add(self, field):
        self.fields.append(field)

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

    def onFocus(self, last=False):
        if last:
            self.focusedFieldIndex = len(self.fields) - 1
            while self.focusedFieldIndex > -1 and\
                not self.fields[self.focusedFieldIndex].focusable:
                self.focusedFieldIndex -= 1

            if self.focusedFieldIndex < 0:
                return "FOCUS_PREVIOUS"
        else:
            self.focusedFieldIndex = 0
            while self.focusedFieldIndex < len(self.fields) and\
                not self.fields[self.focusedFieldIndex].focusable:
                self.focusedFieldIndex += 1
            if self.focusedFieldIndex == len(self.fields):
                return "ACCEPT" if action == "ACCEPT" else "FOCUS_NEXT"

    def onInput(self, ch, key):
        action = self.fields[self.focusedFieldIndex].onInput(ch, key)
        if action in ("ACCEPT", "FOCUS_NEXT"):
            self.focusedFieldIndex += 1
            while self.focusedFieldIndex < len(self.fields) and\
                not self.fields[self.focusedFieldIndex].focusable:
                self.focusedFieldIndex += 1
            if self.focusedFieldIndex == len(self.fields):
                return action
            return "OK"
        elif action == "FOCUS_PREVIOUS":
            self.focusedFieldIndex -= 1
            while self.focusedFieldIndex > -1 and\
                not self.fields[self.focusedFieldIndex].focusable:
                self.focusedFieldIndex -= 1
            if self.focusedFieldIndex < 0:
                return "FOCUS_PREVIOUS"
            else:
                return "OK"
        return action

class InputField(Widget):
    focusable = True
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
        elif key == "KEY_LEFT":
            self.pos -= 1 if self.pos > 0 else 0
        elif key == "KEY_RIGHT":
            self.pos += 1 if self.pos < len(self.userInput) else 0
        elif key == "KEY_BACKSPACE":
            if self.pos > 0:
                self.userInput = self.userInput[:self.pos - 1] + self.userInput[self.pos:]
                self.pos -= 1
        elif key == "KEY_DC":
            if self.pos < len(self.userInput):
                self.userInput = self.userInput[:self.pos] + self.userInput[self.pos + 1:]
        elif key == "KEY_HOME":
            self.pos = 0
        elif key == "KEY_END":
            self.pos = len(self.userInput)
        elif key == "KEY_RETURN":
            return "ACCEPT"
        elif key == "KEY_ESCAPE":
            return "CANCEL"
        elif key in ("KEY_TAB", "KEY_DOWN"):
            return "FOCUS_NEXT"
        elif key in ("KEY_BTAB", "KEY_UP"):
            return "FOCUS_PREVIOUS"
        else:
            return None
        return "OK"

        