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
            "LAYOUT" if a new layout is needed
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

            May be implemented by any child (Not used for now)
        """
        pass


class Checkbox(Widget):
    """
        A checkbox that can contain two (maybe three in the future) states :
        True or False
    """
    focusable = True
    def __init__(self, label, unique=False):
        self.label = label
        self.color = WHITE
        self.state = False
        self.unique = unique

    def setLabel(self, label, color=None):
        self.label = label[:self.size]
        self.color = WHITE if color is None else color

    def draw(self):
        if self.unique:
            text = "(%s) %s" % ("*" if self.state else " ", self.label)
        else:
            text = "[%s] %s" % ("X" if self.state else " ", self.label)
        self.win.addstr(0, 0, text.encode(ENCODING), self.color)
        #import sys
        #print >>sys.stderr, self.label.encode(ENCODING)

    def layout(self, win):
        Widget.layout(self, win)
        self.size = win.getmaxyx()[1] - 4

    def getPreferredSize(self):
        return 1, 1000

    def onInput(self, ch, key):
        if key in ("KEY_BACKSPACE", "KEY_DC"):
            self.state = False
        elif key == "KEY_RETURN":
            self.state = True
            return "FOCUS_NEXT"
        elif key == "KEY_SPACE":
            self.state = not self.state
        elif key == "KEY_ESCAPE":
            return "CANCEL"
        elif key in ("KEY_TAB", "KEY_DOWN"):
            return "FOCUS_NEXT"
        elif key in ("KEY_BTAB", "KEY_UP"):
            return "FOCUS_PREVIOUS"
        else:
            return None
        return "OK"

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
    def __init__(self, label):
        self.height = 1
        self.width = 1000
        self.text = label
        self.color = WHITE

    def setText(self, text, color=None):
        self.text = text[:self.width]
        self.color = WHITE if color is None else color

    def draw(self):
        self.win.addstr(0, 0, self.text.encode(ENCODING), self.color)

    def getPreferredSize(self):
        return self.height, 1000

class MultiLinesLabel(Label):
    focusable = True
    def __init__(self, text):
        self.height = 2
        self.width = 1000
        self.text = text
        self.displayText = None
        self.color = WHITE
        self.scroll = 0
        self.focus = False

    def onFocus(self):
        self.focus = True

    def onFocusLost(self):
        self.focus = False

    def setText(self, text, color=None):
        self.color = WHITE if color is None else color
        self.text = text
        self.displayText = None

    def computeText(self):
        self.displayText = []
        self.height = 0
        lines = self.text.split("\n")
        for line in lines:
            while len(line) > self.maxWidth:
                self.displayText.append(line[:self.maxWidth])
                self.height += 1
                line = line[self.maxWidth:]
            self.displayText.append(line)
            self.height += 1

    def getPreferredSize(self):
        return self.text.count("\n") + 1, 1000

    def layout(self, win):
        Label.layout(self, win)
        self.maxHeight, self.maxWidth = win.getmaxyx()
        self.computeText()

    def draw(self):
        for i, line in enumerate(self.displayText[self.scroll:self.scroll + self.maxHeight]):
            try:
                self.win.addstr(i, 0, line.encode(ENCODING), self.color)
            except Exception:
                #import sys
                #print >>sys.stderr, len(line), "'%s'" % line.encode(ENCODING)
                if i + 1 != self.maxHeight or len(line) != self.maxWidth:
                    raise

        if self.focus:
            self.win.move(0, 0)
            self.win.cursyncup()

    def onInput(self, ch, key):
        if key == "KEY_ESCAPE":
            return "CANCEL"
        elif key == "KEY_TAB":
            return "FOCUS_NEXT"
        elif key == "KEY_BTAB":
            return "FOCUS_PREVIOUS"
        elif key == "KEY_DOWN":
            if self.maxHeight + self.scroll < self.height:
                self.scroll += 1
        elif key == "KEY_UP":
            if self.scroll > 0:
                self.scroll -= 1
        else:
            return None
        return "OK"


class ActivableLabel(Label):
    focusable = True

    def __init__(self, label, command="ACCEPT"):
        Label.__init__(self, label)
        self.command = command

    def onInput(self, ch, key):
        if key == "KEY_RETURN":
            return self.command
        elif key == "KEY_ESCAPE":
            return "CANCEL"
        elif key in ("KEY_TAB", "KEY_DOWN"):
            return "FOCUS_NEXT"
        elif key in ("KEY_BTAB", "KEY_UP"):
            return "FOCUS_PREVIOUS"
        else:
            return None
        return "OK"


class BaseMenu(Widget):

    selected = 0
    focusable = True
    scroll = 0

    def refresh(self, items, selected=None, margin=4):
        """
        items should be [(label, item), ..]
        """
        self.margin = margin
        self.items = items
        self.total = len(items)
        if selected is not None:
            if type(selected) == type(1):
                self.selected = selected
            else:
                self.selected = [i for a, i in items].index(selected)
        else:
            self.selected = min(self.selected, len(self.items) - 1)
        self.itemToBeDeleted = None

    def adjustScrolling(self):
        if self.selected > self.maxItem + self.scroll - 1:
            self.scroll = self.selected - self.maxItem + 1

        if self.selected < self.scroll:
            self.scroll = self.selected

        if self.scroll > len(self.items) - self.maxItem:
            self.scroll = max(0, len(self.items) - self.maxItem)

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
        self.adjustScrolling()
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
        self.drawMenu(self.items, self.selected, color, self.margin)

    def layout(self, win):
        Widget.layout(self, win)
        self.maxItem = win.getmaxyx()[0] - 2
        self.adjustScrolling()

    def drawMenu(self, items, selectedRow, color, margin):
        lines = min(len(items), self.maxItem) + 2
        maxWidth = self.drawAutoResizeBox(0, lines, margin, WHITE)
        for i, item in enumerate(items[self.scroll:self.maxItem + self.scroll]):
            label = " " + item[0][:maxWidth]
            label += " " * (maxWidth - len(label))
            self.win.addstr(1 + i, 2 + self.margin, label.encode(ENCODING), color | c.A_REVERSE if i + self.scroll == selectedRow else 0)
            if i + self.scroll == selectedRow:
                self.win.move(1 + i, 1 + self.margin)
                self.win.cursyncup()


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

    def addRightPane(self, field, title=None, color=None):
        self.rightPane = field
        self.rightTitle = title
        self.rightColor = WHITE if color is None else color


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

        if self.leftTitle is not None:
            leftTitle = self.leftTitle[:middle - 4]
            x = middle // 2 - len(leftTitle + u"  ") // 2
            self.win.addstr(0, x, " " + leftTitle.encode(ENCODING) + " ", WHITE | curses.A_BOLD if self.focusLeftPane else 0)
        if self.rightTitle is not None:
            rightTitle = self.rightTitle[:middle - 4]
            x = middle + middle // 2 - len(rightTitle + u"  ") // 2
            self.win.addstr(0, x, " " + rightTitle.encode(ENCODING) + " ", WHITE | curses.A_BOLD if not self.focusLeftPane else 0)

        self.leftPane.draw()
        self.rightPane.draw()

    def onInput(self, ch, key):
        if self.focusLeftPane:
            action = self.leftPane.onInput(ch, key)
        else:
            action = self.rightPane.onInput(ch, key)
        focusedPane = self.leftPane if self.focusLeftPane else self.rightPane
        if action == "FOCUS_NEXT":
            focusedPane.onFocusLost()
            if self.focusLeftPane and self.rightPane is not None and self.rightPane.focusable:
                focusedPane=self.rightPane
                self.focusLeftPane = False
                focusedPane.onFocus()
            else:
                self.focusLeftPane = True
                return "FOCUS_NEXT"
        elif action == "FOCUS_PREVIOUS":
            focusedPane.onFocusLost()
            if not self.focusLeftPane and self.leftPane is not None and self.leftPane.focusable:
                focusedPane=self.leftPane
                self.focusLeftPane = True
                focusedPane.onFocus()
            else:
                self.focusLeftPane = False
                return "FOCUS_PREVIOUS"
        else:
            return action
        return "OK"

    def onFocus(self):
        if self.focusLeftPane:
            self.leftPane.onFocus()
        else:
            self.rightPane.onFocus()


class StackedFields(Widget):
    focusedFieldIndex = 0
    def __init__(self):
        self.clear()

    @property
    def focusable(self):
        for field in self.fields:
            if field.focusable:
                return True
        return False

    def clear(self):
        self.fields = []

    def add(self, field):
        self.fields.append(field)

    @property
    def currentField(self):
        return self.fields[self.focusedFieldIndex]

    def layout(self, win):
        self.win = win
        self.subwins = []
        y = 0
        for field in self.fields:
            lines, cols = field.getPreferredSize()
            mlines, mcols = win.getmaxyx()
            subwin = self.win.derwin(lines, min(cols, mcols - 2), y, 2)
            y += lines
            field.layout(subwin)
            self.subwins.append(subwin)
        self.onFocus()

    def draw(self):
        if len(self.fields) == 0:
            return
        self.win.addstr(self.focusedFieldIndex, 0, ">")
        self.win.move(self.focusedFieldIndex, 0)
        self.win.cursyncup()
        for i, field in enumerate(self.fields):
            if i != self.focusedFieldIndex:
                field.draw()
        ## the focused field is drawn last
        self.fields[self.focusedFieldIndex].draw()


    def adjustIndex(self, backward=False):
        if backward:
            while self.focusedFieldIndex >= len(self.fields):
                self.focusedFieldIndex -= 1

            while self.focusedFieldIndex > -1 and\
                not self.fields[self.focusedFieldIndex].focusable:
                self.focusedFieldIndex -= 1
                import sys
                print >>sys.stderr, self.focusedFieldIndex
            if self.focusedFieldIndex < 0:
                return "FOCUS_PREVIOUS"
        else:
            while self.focusedFieldIndex < 0:
                self.focusedFieldIndex += 1
            while self.focusedFieldIndex < len(self.fields) and\
                not self.fields[self.focusedFieldIndex].focusable:
                self.focusedFieldIndex += 1
            if self.focusedFieldIndex == len(self.fields):
                return "FOCUS_NEXT"

    def onFocus(self, index=None, first=False, last=False):
        if last:
            self.focusedFieldIndex = len(self.fields) - 1
            if self.adjustIndex(backward=True) == "FOCUS_PREVIOUS":
                return "FOCUS_PREVIOUS"
            return
        elif first:
            self.focusedFieldIndex = 0
            if self.adjustIndex() == "FOCUS_NEXT":
                return "ACCEPT" if action == "ACCEPT" else "FOCUS_NEXT"
            return
        if index is not None:
            self.focusedFieldIndex = index

        index = self.focusedFieldIndex
        if self.adjustIndex() == "FOCUS_NEXT":
            self.focusedFieldIndex = index
            if self.adjustIndex(backward=True) == "FOCUS_PREVIOUS":
                raise RuntimeError("Unfocusable.")

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

    def __len__(self):
        return len(self.fields)

class InputField(Widget):
    focusable = True
    def __init__(self, prompt, defaultValue=u""):
        if type(prompt) != type(u""):
            raise UnicodeError("prompt must be unicode")
        self.prompt = prompt
        self.pos = len(defaultValue)
        self.userInput = defaultValue
        self.unicodeBuffer = ""
        self.scroll = 0

    def draw(self):
        text = self.prompt + self.userInput[self.scroll : self.size + self.scroll]
        self.win.addstr(0, 0, text.encode("utf-8"), WHITE)
        self.win.move(0, len(self.prompt) + self.pos - self.scroll)
        self.win.cursyncup()

    @staticmethod
    def getPreferredSize():
        return (1, 100)

    def getUserInput(self):
        return self.userInput

    def layout(self, win):
        Widget.layout(self, win)
        self.size = win.getmaxyx()[1] - len(self.prompt) - 1
        if self.pos > self.size + self.scroll:
            self.scroll += self.pos - self.size - self.scroll

    def onInput(self, ch, key):
        if ch >= 32 and ch < 256:
            self.unicodeBuffer += chr(ch)
            try:
                uc = self.unicodeBuffer.decode("utf-8")
                self.userInput = self.userInput[:self.pos] + uc + self.userInput[self.pos:]
                self.unicodeBuffer = ""
                self.pos += 1
                if self.pos >= self.size - self.scroll:
                    self.scroll += 1
            except UnicodeDecodeError:
                pass
        elif key == "KEY_LEFT":
            self.pos -= 1 if self.pos > 0 else 0
            if self.pos < self.scroll:
                self.scroll = self.pos
        elif key == "KEY_RIGHT":
            self.pos += 1 if self.pos < len(self.userInput) else 0
            if self.pos > self.size + self.scroll -1:
                self.scroll += 1
        elif key == "KEY_BACKSPACE":
            if self.pos > 0:
                self.userInput = self.userInput[:self.pos - 1] + self.userInput[self.pos:]
                self.pos -= 1
            if self.pos < self.scroll:
                self.pos = self.scroll
        elif key == "KEY_DC":
            if self.pos < len(self.userInput):
                self.userInput = self.userInput[:self.pos] + self.userInput[self.pos + 1:]
        elif key == "KEY_HOME":
            self.pos = 0
            self.scroll = 0
        elif key == "KEY_END":
            self.pos = len(self.userInput)
            if self.pos > self.size:
                self.scroll = self.pos - self.size + 1
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

        