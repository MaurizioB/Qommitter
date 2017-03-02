#!/usr/bin/env python2.7
# *-* coding: utf-8 *-*

import sys
from os import path
from commands import getoutput
from PyQt4 import QtCore, QtGui

summary_limit = 50
default_limit = 72

def local_path(name):
    return path.join(path.dirname(path.abspath(__file__)), name)

SAVED, MODIFIED, NEW = range(3)
states = ['Saved', 'Unsaved', 'New']
icons = ['save', 'warning', 'refresh']

COMMIT, UNTRACK = range(2)

class StatusIcon(QtGui.QWidget):
    def __init__(self, parent, state=NEW):
        QtGui.QWidget.__init__(self, parent)
        self.label = QtGui.QLabel(states[state], self)
        layout = QtGui.QHBoxLayout(self)
        self.setLayout(layout)
        self.icons = [QtGui.QPixmap(local_path('{}.png'.format(icon))) for icon in icons]
        self.icon = QtGui.QLabel(self)
        self.icon.setPixmap(self.icons[state])
        layout.addWidget(self.icon)
        layout.addWidget(self.label)

    def setState(self, state):
        self.label.setText(states[state])
        self.icon.setPixmap(self.icons[state])

class Highlighter(QtGui.QSyntaxHighlighter):
    def __init__(self, parent, limit=default_limit, *args, **kwargs):
        QtGui.QSyntaxHighlighter.__init__(self, parent, *args, **kwargs)
        self.limit = limit
        self.summary_line = -1
        self.valid = QtGui.QTextCharFormat()
        self.valid.setFont(QtGui.QFont('Bitstream Vera Sans Mono', 10))
        self.valid.setForeground(QtGui.QColor('black'))
        self.commit_list = QtGui.QTextCharFormat()
        self.commit_list.setForeground(QtGui.QColor('green'))
        self.untrack_list = QtGui.QTextCharFormat()
        self.untrack_list.setForeground(QtGui.QColor('red'))
        self.over = QtGui.QTextCharFormat()
        self.over.setForeground(QtGui.QColor('red'))
        self.summary = QtGui.QTextCharFormat(self.valid)
        self.summary.setFontWeight(QtGui.QFont.DemiBold)
        self.summary_over = QtGui.QTextCharFormat(self.summary)
        self.summary_over.setForeground(QtGui.QColor(120, 30, 30))
        self.summary_over.setBackground(QtGui.QColor(120, 30, 30, 50))
        self.summary_over_over = QtGui.QTextCharFormat(self.summary_over)
        self.summary_over_over.setForeground(QtGui.QColor('red'))
        self.comment = QtGui.QTextCharFormat()
        self.comment.setForeground(QtGui.QColor('gray'))
        self.tabs = QtGui.QTextCharFormat()
        self.tabs.setBackground(QtGui.QColor(220, 240, 220, 150))
        self.tab_rx = QtCore.QRegExp(r'\t')
        self.endspace = QtGui.QTextCharFormat()
        self.endspace.setBackground(QtGui.QColor(220, 220, 220))
        self.space_rx = QtCore.QRegExp(r'\ ')

    def set_summary_line(self, summary_line):
        if summary_line == self.summary_line: return
        self.summary_line = summary_line
        self.rehighlight()

    def highlightBlock(self, text):
        if text.startsWith('#'):
            self.setFormat(0, len(text), self.comment)
            if text == '# Changes to be committed:':
                self.setCurrentBlockState(COMMIT)
            elif text in ['# Untracked files:', '# Changes not staged for commit:']:
                self.setCurrentBlockState(UNTRACK)
            elif self.previousBlockState() == COMMIT:
                self.setFormat(1, len(text), self.commit_list)
                if len(text.simplified()) == 1:
                    self.setCurrentBlockState(-1)
                else:
                    self.setCurrentBlockState(COMMIT)
            elif self.previousBlockState() == UNTRACK:
                self.setFormat(1, len(text), self.untrack_list)
                if len(text.simplified()) == 1:
                    self.setCurrentBlockState(-1)
                else:
                    self.setCurrentBlockState(UNTRACK)
        if self.currentBlock().firstLineNumber() == self.summary_line:
            self.setFormat(0, len(text), self.summary)
            if len(text) > summary_limit:
                self.setFormat(summary_limit, len(text)-summary_limit, self.summary_over)
            if len(text) > self.limit:
                self.setFormat(self.limit, len(text)-self.limit, self.summary_over_over)
        elif len(text) > self.limit:
            self.setFormat(self.limit, len(text)-self.limit, self.over)
        tab_index = self.tab_rx.indexIn(text)
        while tab_index >= 0:
            self.setFormat(tab_index, 1, self.tabs)
            tab_index = self.tab_rx.indexIn(text, tab_index+1)
        if text.endsWith(' '):
            space_idx = len(text) 
            while True:
                space_idx -= 1
                if text.at(space_idx).toAscii() != ' ':
                    break
            self.setFormat(space_idx+1, space_idx, self.endspace)

class LineNumbers(QtGui.QWidget):
    def __init__(self, parent):
        self.main = parent
        QtGui.QWidget.__init__(self, parent)

    def sizeHint(self):
        return QtCore.Qsize(self.editor.lineNumbersWidth(), 0)

    def paintEvent(self, event):
        self.main.lineNumbersPaintEvent(event)

class TextEdit(QtGui.QPlainTextEdit):
    summary_line_changed = QtCore.pyqtSignal(int)
    def __init__(self, parent, limit=default_limit):
        QtGui.QPlainTextEdit.__init__(self, parent)
        self.summary_line = -1
        self.draw_summary_limit = False
        self.text_font = QtGui.QFont('Bitstream Vera Sans Mono', 10)
#        self.text_font.setStyleHint(QtGui.QFont.TypeWriter)
        self.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        self.metrics = QtGui.QFontMetrics(self.text_font)
        self.margin = self.document().documentMargin()
        self.limit = self.metrics.width('a'*limit) + self.margin
        self.setTabStopWidth(self.metrics.width(' '*8))
        self.document().setDefaultFont(self.text_font)
        self.limit_pen = QtGui.QPen(QtCore.Qt.lightGray)
        self.limit_pen.setStyle(QtCore.Qt.DotLine)

        self.highlight = Highlighter(self.document(), limit)
        self.lineNumbers = LineNumbers(self)

        self.summary_line_changed.connect(self.highlight.set_summary_line)
        self.textChanged.connect(self.changed)
        self.textChanged.connect(self.pos_update)
        self.blockCountChanged.connect(self.updateLineNumbersWidth)
        self.updateRequest.connect(self.updateLineNumbers)
        self.updateLineNumbersWidth()
        self.cursorPositionChanged.connect(self.pos_update)

    def changed(self):
        document = self.document()
        summary_line = -1
        for l in range(document.blockCount()):
            block = document.findBlockByLineNumber(l)
            if len(block.text().simplified()) > 0 and not block.text().startsWith('#'):
                summary_line = l
                break
        self.summary_line_changed.emit(summary_line)
        self.summary_line = summary_line

    def pos_update(self):
        self.draw_summary_limit = True if self.textCursor().blockNumber() == self.summary_line else False
        self.viewport().update()

    def insertFromMimeData(self, source):
        if source.hasText():
            self.insertPlainText(source.text())

    def paintEvent(self, event):
        qp = QtGui.QPainter(self.viewport())
        qp.setPen(self.limit_pen)
        qp.drawLine(self.limit, 0, self.limit, self.height())
        if self.draw_summary_limit:
            _summary_limit = self.metrics.width('a')*summary_limit
            qp.drawRect(self.contentsRect().x()-1, self.contentsRect().y()-1+(self.textCursor().blockNumber()*self.metrics.height()), _summary_limit+2, self.metrics.height()+2)
#            qp.drawLine(_summary_limit, 0, _summary_limit, self.metrics.height())
        QtGui.QPlainTextEdit.paintEvent(self, event)

    def updateLineNumbersWidth(self):
        self.setViewportMargins(self.lineNumbersWidth(), 0, 0, 0)

    def updateLineNumbers(self, rect, dy):
        if dy:
            self.lineNumbers.scroll(0, dy)
        else:
            self.lineNumbers.update(0, rect.y(), self.lineNumbers.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.updateLineNumbersWidth()

    def lineNumbersWidth(self):
        digits = 1
        count = max(1, self.blockCount())
        while count >= 10:
            count /= 10
            digits += 1
        return 10+self.metrics.width('0')*digits

    def lineNumbersPaintEvent(self, event):
        qp = QtGui.QPainter(self.lineNumbers)
        qp.setFont(self.text_font)

        block = self.firstVisibleBlock()
        block_n = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        height = self.metrics.height()

        currentBlock = self.textCursor().block()
        normal_font = qp.font()
        highlight_font = QtGui.QFont(normal_font)
        highlight_font.setWeight(QtGui.QFont.DemiBold)
        normal_color = QtGui.QColor(100, 100, 100)
        highlight_color = QtGui.QColor(50, 150, 50)
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                n = str(block_n+1)
                if block == currentBlock:
                    qp.setFont(highlight_font)
                    qp.setPen(highlight_color)
                else:
                    qp.setFont(normal_font)
                    qp.setPen(normal_color)
                qp.drawText(0, top, self.lineNumbers.width()-3, height, QtCore.Qt.AlignRight, n)
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_n += 1
        qp.end()

    def resizeEvent(self, event):
        rect = self.contentsRect()
        self.lineNumbers.setGeometry(rect.x(), rect.y(), self.lineNumbersWidth(), rect.height())

class Editor(QtGui.QMainWindow):
    def __init__(self, parent, argv, limit=default_limit):
        QtGui.QMainWindow.__init__(self, parent=None)
        self.limit = limit
        self.repo = getoutput('basename `git rev-parse --show-toplevel`')
        self.editor = TextEdit(self, limit)
#        self.text_cursor = self.editor.textCursor()
        self.document = self.editor.document()
        self.setCentralWidget(self.editor)
        self.status = QtGui.QStatusBar(self)
        self.status.setSizeGripEnabled(False)
        self.setStatusBar(self.status)
        line_lbl = QtGui.QLabel('Line: ')
        self.status.addWidget(line_lbl)
        self.line_n_lbl = QtGui.QLabel('1')
        self.line_n_lbl.setMinimumWidth(QtGui.QFontMetrics(self.line_n_lbl.font()).width('0'*4))
        self.status.addWidget(self.line_n_lbl)
        col_lbl = QtGui.QLabel('Col: ')
        self.status.addWidget(col_lbl)
        self.col_n_lbl = QtGui.QLabel('0')
        self.col_n_lbl.setMinimumWidth(QtGui.QFontMetrics(self.line_n_lbl.font()).width('0'*4))
        self.status.addWidget(self.col_n_lbl)
        len_lbl = QtGui.QLabel('Size: ')
        self.status.addWidget(len_lbl)
        self.size_lbl = QtGui.QLabel('0 bytes')
        self.status.addWidget(self.size_lbl)
        spacer = QtGui.QWidget()
        spacer.setFixedSize(20, 1)
        self.status.addWidget(spacer)
        self.valid = QtGui.QLabel()
        self.status.addWidget(self.valid)

        self.status_icon = StatusIcon(self, NEW)
        self.status.addPermanentWidget(self.status_icon)

        self.editor.cursorPositionChanged.connect(self.pos_update)
        self.editor.textChanged.connect(self.size_update)
        self.editor.textChanged.connect(self.check)
        width = self.editor.margin+self.editor.metrics.maxWidth()*(self.limit+8)
        self.resize(width, width*.75)

        if len(argv) == 1:
            self.base_commit = QtCore.QString().fromLatin1('sghhògh ààhgkjoir')
            self.editor.insertPlainText(self.base_commit)
            self.file = None
        else:
            git_status = getoutput('git status -s').split('\n')
            staged = []
            unstaged = []
            for l in git_status:
                if l.startswith(' '):
                    unstaged.append(l[3:])
                else:
                    staged.append(l[3:])
            self.git_status = staged, unstaged
            self.file = argv[1]
            with open(self.file, 'rb') as commit:
                text = QtCore.QString().fromUtf8(commit.read())
                self.base_commit = text
                self.editor.insertPlainText(text)
        self.undo = 0
        self.document.clearUndoRedoStacks()
        self.document.setModified(False)
        self.document.modificationChanged.connect(self.set_state)

        self.set_state(states[NEW])

    def set_state(self, state=None):
        if isinstance(state, str):
            state = NEW
        else:
            if state:
                state = MODIFIED
            else:
                if self.document.toPlainText() == self.base_commit:
                    state = NEW
                else:
                    state = SAVED
        self.setWindowTitle('Commit editor for "{}" ({})'.format(self.repo, states[state]))
        self.status_icon.setState(state)

    def check(self):
        content = False
        for l in str(self.document.toPlainText().toUtf8()).split('\n'):
            if l.startswith('#') or not len(l.strip()): continue
            content = True
            break
        if not content:
            self.valid.setText('Commit message empty!')
        else:
            self.valid.setText('')

    def size_update(self):
        size = len(self.document.toPlainText().toUtf8())
        fmt = 'B'
        if size > 1024:
            size /= 1024.
            size = '{:.2f}'.format(size)
            fmt = 'KB'
        self.size_lbl.setText('{} {}'.format(size, fmt))

    def closeEvent(self, event):
        event.ignore()
        self.quit()

    def save(self):
        self.document.setModified(False)
        if self.file:
            try:
                with open(self.file, 'wb') as commit:
                    text = str(self.document.toPlainText().toUtf8())
                    if text[-1] != '\n':
                        text += '\n'
                    commit.write(text)
                return True
            except Exception as err:
                QtGui.QMessageBox.warning(self, 
                                          'Error!', 
                                          'There was a problem writing the commit, the error message is:\n\n{}'.format(err)
                                          )
                return False

    def quit(self):
        if not self.document.isModified():
            QtGui.QApplication.quit()
            return
        res = QtGui.QMessageBox.question(self, 
                                         'Confirm exit', 
                                         'The commit message has been modified, save it or ignore?', 
                                         QtGui.QMessageBox.Save|QtGui.QMessageBox.Ignore|QtGui.QMessageBox.Cancel, 
                                         QtGui.QMessageBox.Save
                                         )
        if res == QtGui.QMessageBox.Cancel: return
        elif res == QtGui.QMessageBox.Ignore:
            QtGui.QApplication.quit()
            return
        if self.save():
            QtGui.QApplication.quit()

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.quit()
        if event.key() == QtCore.Qt.Key_S and event.modifiers() == QtCore.Qt.ControlModifier:
            self.save()

    @property
    def text_cursor(self):
        return self.editor.textCursor()

    def pos_update(self):
        self.line_n_lbl.setText(str(self.text_cursor.blockNumber()+1))
        column = self.text_cursor.columnNumber()
        self.col_n_lbl.setText(str(column))

def main():
    app = QtGui.QApplication(sys.argv)
#    app.setOrganizationName('jidesk')
#    app.setApplicationName('Blofix')
    w = Editor(app, sys.argv)
    w.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()


