# -*- coding: utf-8 -*-

"CodeMirror 6 Playground"

SAMPLE_SQL = """SELECT
    customer.id,
    customer.name,
    SUM(invoice.total) AS total_billed
FROM customer
LEFT JOIN invoice ON invoice.customer_id = customer.id
WHERE customer.active = true
GROUP BY customer.id, customer.name
ORDER BY total_billed DESC
LIMIT 50;
"""

SAMPLE_PYTHON = """from dataclasses import dataclass


@dataclass
class Customer:
    id: int
    name: str
    active: bool = True

    def greet(self) -> str:
        if not self.active:
            return f"Customer {self.name} is inactive."
        return f"Hello, {self.name}!"


def main():
    cs = [Customer(1, 'Alice'), Customer(2, 'Bob', active=False)]
    for c in cs:
        print(c.greet())


if __name__ == '__main__':
    main()
"""

SAMPLE_JAVASCRIPT = """function fibonacci(n) {
    if (n < 2) return n;
    let a = 0, b = 1;
    for (let i = 2; i <= n; i += 1) {
        const next = a + b;
        a = b;
        b = next;
    }
    return b;
}

const result = [...Array(10)].map((_, i) => fibonacci(i));
console.log(result);
"""

SAMPLE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <title>Sample</title>
</head>
<body>
    <h1>Hello, world!</h1>
    <p>This is a paragraph with <strong>bold</strong> text.</p>
</body>
</html>
"""

SAMPLE_CSS = """:root {
    --primary: #4a90e2;
    --radius: 6px;
}

.btn {
    background: var(--primary);
    border-radius: var(--radius);
    color: white;
    padding: 8px 16px;
}

.btn:hover {
    filter: brightness(1.1);
}
"""

SAMPLE_JSON = """{
    "name": "genropy",
    "version": "26.3.9",
    "features": ["webpages", "th", "batch"],
    "active": true
}
"""

SAMPLE_XML = """<?xml version="1.0"?>
<catalog>
    <book id="bk101" lang="en">
        <author>Gambardella, Matthew</author>
        <title>XML Developer's Guide</title>
        <price>44.95</price>
    </book>
</catalog>
"""

SAMPLE_MARKDOWN = """# CodeMirror 6 demo

A short paragraph with **bold**, *italic* and `inline code`.

## Lists

- one
- two
    - nested item
    - another nested
- three

## Code

```python
def fibonacci(n):
    if n < 2:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
```

> Block quote with [a link](https://example.com).

| Header A | Header B |
|----------|----------|
| cell 1   | cell 2   |
"""

SAMPLE_YAML = """app:
    name: invoice_demo
    version: 1.0.0
    debug: true
servers:
    - host: db.example.com
      port: 5432
      role: primary
    - host: replica.example.com
      port: 5432
      role: replica
features:
    auth: oidc
    cache:
        backend: redis
        ttl: 3600
"""

SAMPLES = {
    'sql': SAMPLE_SQL,
    'python': SAMPLE_PYTHON,
    'javascript': SAMPLE_JAVASCRIPT,
    'html': SAMPLE_HTML,
    'css': SAMPLE_CSS,
    'json': SAMPLE_JSON,
    'xml': SAMPLE_XML,
    'markdown': SAMPLE_MARKDOWN,
    'yaml': SAMPLE_YAML,
}


class GnrCustomWebPage(object):
    py_requires = "gnrcomponents/testhandler:TestHandlerBase"

    def test_0_playground(self, pane):
        "Live playground: change language, theme and options on the fly. Read-only switches without rebuild; other changes recreate the editor."
        pane.data('.config.mode', 'sql')
        pane.data('.config.theme', '')
        pane.data('.config.lineNumbers', True)
        pane.data('.config.keyMap', 'softTab')
        pane.data('.config.indentUnit', 4)
        pane.data('.config.readOnly', False)
        pane.data('.config.editable', True)
        pane.data('.config.lineWrapping', False)
        pane.data('.config.fontSize', '13px')
        pane.data('.config.fontFamily', '')
        pane.data('.source', SAMPLES['sql'])

        bc = pane.borderContainer(height='820px', width='100%',
                                  border='1px solid silver')
        controls = bc.contentPane(region='right', width='280px',
                                  splitter=True, padding='8px',
                                  border_left='1px solid silver',
                                  background='#f7f7f7')
        controls.div('Editor settings',
                     font_weight='bold', padding_bottom='6px')
        fb = controls.formbuilder(cols=1, border_spacing='4px', width='100%')
        fb.filteringSelect(value='^.config.mode', lbl='Language',
                           values=','.join(sorted(SAMPLES.keys())))
        fb.filteringSelect(value='^.config.theme', lbl='Theme',
                           values=':(default light),'
                                  'oneDark:One Dark,'
                                  'amy:Amy,'
                                  'ayuLight:Ayu Light,'
                                  'barf:Barf,'
                                  'bespin:Bespin,'
                                  'birdsOfParadise:Birds of Paradise,'
                                  'boysAndGirls:Boys and Girls,'
                                  'clouds:Clouds,'
                                  'cobalt:Cobalt,'
                                  'coolGlow:Cool Glow,'
                                  'dracula:Dracula,'
                                  'espresso:Espresso,'
                                  'noctisLilac:Noctis Lilac,'
                                  'rosePineDawn:Rose Pine Dawn,'
                                  'smoothy:Smoothy,'
                                  'solarizedLight:Solarized Light,'
                                  'tomorrow:Tomorrow')
        fb.filteringSelect(value='^.config.keyMap', lbl='Key map',
                           values='softTab:softTab (spaces),:default (tab)')
        fb.numberTextBox(value='^.config.indentUnit', lbl='Indent unit',
                         min=1, max=8)
        fb.filteringSelect(value='^.config.fontSize', lbl='Font size',
                           values='11px,12px,13px,14px,15px,16px,18px,20px')
        fb.filteringSelect(value='^.config.fontFamily', lbl='Font family',
                           values=':default,'
                                  'Menlo, monospace:Menlo,'
                                  '"Source Code Pro", monospace:Source Code Pro,'
                                  '"JetBrains Mono", monospace:JetBrains Mono,'
                                  '"Fira Code", monospace:Fira Code,'
                                  '"Courier New", monospace:Courier New')
        fb.checkbox(value='^.config.lineNumbers', label='Line numbers')
        fb.checkbox(value='^.config.lineWrapping', label='Line wrapping')
        fb.checkbox(value='^.config.readOnly', label='Read only')
        fb.checkbox(value='^.config.editable', label='Editable (focus + cursor)')
        controls.dataController("SET .source = SAMPLES.getItem(mode);",
                                mode='^.config.mode',
                                SAMPLES=SAMPLES)
        editor_pane = bc.contentPane(region='center', overflow='hidden',
                                     padding='4px')
        editor_pane.codemirror(value='^.source',
                               config_mode='^.config.mode',
                               config_theme='^.config.theme',
                               config_lineNumbers='^.config.lineNumbers',
                               config_keyMap='^.config.keyMap',
                               config_indentUnit='^.config.indentUnit',
                               config_fontSize='^.config.fontSize',
                               config_fontFamily='^.config.fontFamily',
                               readOnly='^.config.readOnly',
                               editable='^.config.editable',
                               lineWrapping='^.config.lineWrapping',
                               height='100%', width='100%')
        mirror = bc.contentPane(region='bottom', height='200px',
                                splitter=True, padding='6px',
                                border_top='1px solid silver',
                                background='#fafbfc')
        mirror.div('Mirror (simpleTextArea bound to the same datapath ^.source)',
                   font_weight='bold', font_size='0.9em',
                   padding_bottom='4px', color='#555')
        mirror.simpleTextArea(value='^.source', width='100%', height='160px',
                              font_family='monospace', font_size='12px')
