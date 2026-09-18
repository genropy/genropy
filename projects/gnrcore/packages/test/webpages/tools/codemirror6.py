# -*- coding: utf-8 -*-

"CodeMirror 6"


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerFull"

    def test_0_sql(self, pane):
        "CodeMirror with SQL syntax highlighting"
        pane.data('.sql', 'SELECT id, name, total\nFROM invoice\nWHERE total > 100\nORDER BY id;')
        pane.codemirror(value='^.sql',
                        config_mode='sql', config_lineNumbers=True,
                        config_keyMap='softTab', config_indentUnit=4,
                        height='220px', width='600px')

    def test_1_python_readonly(self, pane):
        "CodeMirror in read-only mode with Python and oneDark theme"
        pane.data('.py', 'def fibonacci(n):\n    if n < 2:\n        return n\n    return fibonacci(n - 1) + fibonacci(n - 2)\n')
        pane.codemirror(value='^.py',
                        config_mode='python', config_theme='oneDark',
                        config_lineNumbers=True, readOnly=True,
                        height='220px', width='600px')

    def test_2_javascript_search(self, pane):
        "CodeMirror JavaScript with built-in search panel (Ctrl/Cmd+F)"
        pane.data('.js', 'function greet(name) {\n    console.log("Hello, " + name);\n}\n\ngreet("world");\n')
        pane.codemirror(value='^.js',
                        config_mode='javascript', config_lineNumbers=True,
                        config_keyMap='softTab', config_indentUnit=2,
                        height='220px', width='600px')

    def test_3_shared_datapath(self, pane):
        "Two editors sharing the same datapath: edits in one update the other"
        pane.data('.shared', 'SELECT * FROM customer WHERE active = true;')
        bc = pane.borderContainer(height='240px', width='100%', border='1px solid silver')
        left = bc.contentPane(region='left', width='50%', splitter=True)
        left.div('Editor A', font_weight='bold', padding='4px')
        left.codemirror(value='^.shared', config_mode='sql',
                        config_lineNumbers=True, height='200px')
        right = bc.contentPane(region='center')
        right.div('Editor B', font_weight='bold', padding='4px')
        right.codemirror(value='^.shared', config_mode='sql',
                         config_lineNumbers=True, height='200px')
