#!/usr/bin/env python3

import sys

try:
    import config
except:
    print("Please copy config.example.py into config.py and try again.")
    sys.exit(0)

from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtGui import * 
from PyQt5.QtCore import * 
from mainwindow import Ui_MainWindow

from time import sleep

import threading
from paramiko import SSHClient, AutoAddPolicy

from lxml import etree
from io import StringIO

from email.utils import formatdate

files = []

last_index = 0

css = '''
body {
    font-family: Arial, Helvetica, sans-serif;
}
li{ margin-top: 8px; }
'''

def node_text(n):
    try:
        return etree.tostring(n, method='html', with_tail=False)
    except TypeError:
        return str(n)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.ui.listWidget.addItems(files)
        self.ui.listWidget.setCurrentRow(0)
        self.ui.listWidget.itemClicked.connect(self.downloadFile)

        self.ui.pushButton.clicked.connect(self.askFile)
        self.ui.insertDateButton.clicked.connect(self.insertNewDate)
        self.ui.deleteButton.clicked.connect(self.deleteFile)
        self.ui.regenerateDataButton.clicked.connect(self.regenerateData)

        self.ui.actionSave.triggered.connect(self.saveFile)
        self.ui.actionLoad.triggered.connect(self.downloadFile)

        self.ui.actionQuit.triggered.connect(self.close)

        self.prev = self.ui.textEdit.keyPressEvent

        self.ui.textEdit.keyPressEvent = self.handleKeyPress

        self.downloadFile()
    
    def regenerateData(self):
        ssh.exec_command(f"sh -c 'cd {config.files_path} && ./generate_blog_data.py'")

    def handleKeyPress(self, event):
        key = event.key()
        indexLeftToCursor = self.ui.textEdit.textCursor().position() - 1
        self.prev(event)

        self.updatePreview()

        if key == QtCore.Qt.Key_Enter or key == QtCore.Qt.Key_Return:
            docCont = self.ui.textEdit.toPlainText()
            if len(docCont) >= 1:
                if indexLeftToCursor >= 0 and indexLeftToCursor < len(docCont):
                    hitEnterAfterOpeningBrace = docCont[indexLeftToCursor] == '>' 
                    hitEnterAfterIndent = docCont[indexLeftToCursor] == ' '
                    if hitEnterAfterOpeningBrace:
                        inp = self.ui.textEdit.toPlainText()
                        inp = inp[inp.rfind('\n', 0, indexLeftToCursor + 1) + 1:]
                        count = len(inp) - len(inp.lstrip())
                        count += 4
                        self.ui.textEdit.insertPlainText(" " * count)
                    elif hitEnterAfterIndent:
                        inp = self.ui.textEdit.toPlainText()
                        b = inp[inp.rfind('\n', 0, indexLeftToCursor + 1) + 1:]
                        count = len(b) - (len(inp) - indexLeftToCursor) + 1
                        self.ui.textEdit.insertPlainText(" " * count)
            self.saveFile()
    
    def deleteFile(self):
        self.current_file = files[self.ui.listWidget.currentRow()]
        ftp.remove(self.current_file)
        old = self.ui.listWidget.currentRow()
        del files[old]
        self.ui.listWidget.clear()
        self.ui.listWidget.addItems(files)
        self.ui.listWidget.setCurrentRow(0)
        self.downloadFile()

    def downloadFile(self):
        ftp.get(files[self.ui.listWidget.currentRow()], '/tmp/temp_file_edit')
        with open('/tmp/temp_file_edit', 'r') as f:
            self.ui.textEdit.setText(f.read())
            f.close()
        self.current_file = files[self.ui.listWidget.currentRow()]
        self.updatePreview()

    def saveFile(self):
        with open('/tmp/temp_file_edit', 'w') as f:
            f.write(self.ui.textEdit.toPlainText())
            f.close()
        ftp.put('/tmp/temp_file_edit', files[self.ui.listWidget.currentRow()])
        self.current_file = files[self.ui.listWidget.currentRow()]
        self.updatePreview()

    def updatePreview(self):
        try: 
            x = etree.parse(StringIO(self.ui.textEdit.toPlainText()))
            html = node_text(x.find('html')).decode().replace('<html>', '').replace('</html>', '')
            title = node_text(x.find('title')).decode().replace('<title>', '').replace('</title>', '')
            date = node_text(x.find('date')).decode().replace('<date>', '').replace('</date>', '')
            category = node_text(x.find('category')).decode().replace('<category>', '').replace('</category>', '')
            self.ui.textBrowser.setHtml(f'<style>{css}</style><h1>{title}</h1><h3>Published on {date} {"| Category: " + category if category else ""}</h3><hr>' + html)
        except Exception as e:
            self.ui.textBrowser.setHtml("<b>Invalid XML</b><pre>" + str(e) + "</pre>")

    def insertNewDate(self):
        self.ui.textEdit.textCursor().insertHtml(formatdate())

    def askFile(self):
        global last_index, files
        text, ok = QtWidgets.QInputDialog.getText(self, 'Enter filename', 'What do you want the article title to be?')
        if ok:
            title = str(text)
            word = title.strip().split(' ')[0]
            filename = str(last_index).zfill(2) + '-' + word.lower() + '.xml'
            files.append(filename)
            last_index+=1
            self.ui.listWidget.addItem(filename)
            self.ui.listWidget.setCurrentRow(last_index-1)
            text = f"""<blog>
    <title>{title}</title>
    <date>{formatdate()}</date>
    <category>General</category>
    <enclosure></enclosure>
    <html>
    </html>
</blog>
"""

            with open('/tmp/temp_file_edit', 'w') as f:
                f.write(text)
                f.close()

            ftp.put('/tmp/temp_file_edit', files[self.ui.listWidget.currentRow()])
            self.ui.textEdit.setText(text)

            index = 117 + len(title) + len(formatdate())
            cur = self.ui.textEdit.textCursor()
            cur.setPosition(index)
            self.ui.textEdit.setTextCursor(cur)

            sleep(0.01)
            self.saveFile()

if __name__ == '__main__':

    ssh = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    ssh.connect(config.sftpURL, username=config.sftpUser, password=config.sftpPassword, port=config.sftpPort)

    ftp = ssh.open_sftp()
    ftp.chdir(config.files_path)

    files = ftp.listdir()

    files_new = []
    for v in files:
        if v.endswith('.xml'):
            files_new.append(v)

    files = files_new

    files.sort()

    last_index = len(files)

    app = QtWidgets.QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
