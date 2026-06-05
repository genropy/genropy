# Giojo Grid — Catalogo Completo delle Feature

## Panoramica

La Grid di Giojo (derivata da dojox.grid di Dojo 1.1) e' un componente tabellare completo
con virtualizzazione, editing inline, selezione, drag, ordinamento e multi-view layout.

**25 file JS**, organizzati in:
- `dojox/grid/` — entry point (`VirtualGrid.js`, `Grid.js`)
- `dojox/grid/_grid/` — moduli core (rendering, layout, interazione)
- `dojox/grid/_data/` — data model, fields, editors

---

## Architettura

```
Grid (extends VirtualGrid)
 |
 +-- VirtualGrid (extends dijit._Widget + dijit._Templated)
      |
      +-- scroller.columns    (virtualizzazione scroll)
      +-- layout              (struttura colonne/views)
      +-- views               (container di view)
      |    +-- GridView[]      (una per blocco colonne)
      |    |    +-- headerBuilder  (rendering header)
      |    |    +-- contentBuilder (rendering righe)
      |    +-- GridRowView     (barra selezione righe)
      +-- rows                (styling righe)
      +-- focus               (navigazione focus)
      +-- selection            (selezione righe)
      +-- edit                 (editing inline)
      +-- publicEvents         (dispatch eventi)
```

---

## 1. Virtual Scrolling

La grid non renderizza tutte le righe: usa un sistema a pagine virtuali.

### Caratteristiche
- **Paginazione virtuale**: le righe sono organizzate in pagine (`rowsPerPage`, default 25)
- **Cache pagine**: mantiene fino a `keepRows` righe in memoria (default 75)
- **Stack FIFO**: le pagine piu' vecchie vengono rimosse quando la cache e' piena
- **Scroll veloce** (`fastScroll`): feedback ritardato durante scroll rapido
- **Scroll ritardato** (`delayScroll`): opzione per scroll con delay
- **Soglia ridisegno** (`scrollRedrawThreshold`): pixel minimo per triggerare redraw
- **Pacificazione**: durante scroll intenso mostra indicatore di caricamento

### Scroller multi-colonna
- `scroller.columns`: gestisce scroll sincronizzato su piu' view (colonne bloccate)
- Ogni view ha il proprio content node ma lo scroll verticale e' sincronizzato

### API
```
scrollTo(inTop)              // Scroll a posizione pixel
scrollToRow(inRowIndex)      // Scroll a riga specifica
setScrollTop(inTop)          // Imposta posizione scroll
updateRowCount(inRowCount)   // Cambia numero righe (ri-virtualizza)
```

---

## 2. Layout Multi-View

La grid supporta layout complessi con colonne bloccate e strutture multi-livello.

### Caratteristiche
- **View multiple**: ogni blocco di colonne puo' essere una "view" separata
- **View elastica** (`elasticView`): una view si espande per riempire lo spazio
- **Colonne bloccate**: views con `noscroll: true` non scrollano orizzontalmente
- **Row bar**: colonna laterale (`GridRowView`) per selezione righe
- **Subrows**: ogni view puo' avere piu' righe (header multi-livello)
- **ColSpan/RowSpan**: celle possono occupare piu' colonne/righe

### Struttura definition
La struttura e' un array di view definitions, ognuna contenente rows di cells:
```javascript
structure = [
  { // view bloccata
    noscroll: true,
    cells: [
      [{ name: "ID", field: 0, width: "5em" }]
    ]
  },
  { // view scrollabile
    cells: [
      [
        { name: "Nome", field: 1, width: "10em" },
        { name: "Email", field: 2, width: "auto" }
      ]
    ]
  }
]
```

### Larghezze colonne
- Supporta `em`, `px`, `%`, `auto`
- Conversione automatica px -> em (ratio 16)
- Celle flex: `width: "auto"` o `%` si adattano

### API
```
setStructure(inStructure)     // Imposta layout
getCell(inIndex)              // Ottiene cell object
setCellWidth(inIndex, width)  // Imposta larghezza colonna
getCellName(inCell)           // Nome colonna
```

---

## 3. Rendering

### Header
- Generato da `headerBuilder`
- Supporta multi-row headers (subrows)
- Indicatore di ordinamento (freccia asc/desc)
- Resize colonne via drag sull'header

### Content
- Generato da `contentBuilder`
- Pre-compilazione HTML: i template delle celle vengono preparati una volta
- Ogni riga e' una tabella HTML
- Supporta custom formatters per cella
- Callback `onBeforeRow` prima di ogni riga

### Styling righe
Il sistema di styling applica classi CSS basate sullo stato:
- `dojoxGrid-row-odd` — righe dispari (zebra striping)
- `dojoxGrid-row-selected` — righe selezionate
- `dojoxGrid-row-over` — riga sotto il mouse
- `dojoxGrid-row-editing` — riga in editing
- `dojoxGrid-cell-focus` — cella con focus
- `dojoxGrid-cell-over` — cella sotto il mouse
- Custom classes/styles per riga e cella via `onStyleRow`

### API
```
render()                      // Render completo
renderRow(inRowIndex)         // Render singola riga
updateRow(inRowIndex)         // Aggiorna singola riga
updateRowStyles(inRowIndex)   // Aggiorna solo stili
rowHeightChanged(inRowIndex)  // Notifica cambio altezza
```

---

## 4. Ordinamento (Sorting)

### Caratteristiche
- Click su header colonna per ordinare
- Toggle ascendente/discendente
- Indicatore visuale nell'header (freccia)
- Ordinamento delegato al data model
- `canSort(inSortInfo)` per controllare quali colonne sono ordinabili

### API
```
setSortIndex(inIndex, inAsc)  // Ordina per colonna
setSortInfo(inSortInfo)       // Imposta info ordinamento
getSortIndex()                // Indice colonna corrente
getSortAsc()                  // true = ascendente
sort()                        // Esegue ordinamento
canSort(inSortInfo)           // Controlla se ordinabile
```

---

## 5. Selezione Righe

### Modalita'
- **Selezione singola**: click seleziona una riga (deseleziona le altre)
- **Selezione multipla** (`multiSelect: true`, default): Ctrl+Click aggiunge alla selezione
- **Selezione range**: Shift+Click seleziona da ultima selezione a click corrente

### Feedback visuale
- Classe CSS `dojoxGrid-row-selected` sulle righe selezionate
- Row bar laterale con highlight
- Stili custom via `onStyleRow`

### Pre-conditions
- `onCanSelect(inRowIndex)` — puo' impedire selezione
- `onCanDeselect(inRowIndex)` — puo' impedire deselezione

### API
```
selection.select(inIndex)           // Seleziona singola
selection.addToSelection(inIndex)   // Aggiungi a selezione
selection.deselect(inIndex)         // Deseleziona
selection.toggleSelect(inIndex)     // Toggle
selection.unselectAll()             // Deseleziona tutto
selection.shiftSelect(from, to)     // Range select
selection.isSelected(inIndex)       // Controlla
selection.getSelected()             // Array indici selezionati
selection.getSelectedCount()        // Conteggio
selection.getFirstSelected()        // Primo selezionato
selection.getNextSelected(prev)     // Prossimo selezionato
```

### Eventi
```
onSelected(inRowIndex)              // Dopo selezione
onDeselected(inRowIndex)            // Dopo deselezione
onSelectionChanged()                // Cambio selezione
```

---

## 6. Focus e Navigazione Tastiera

### Navigazione
- **Tab / Shift+Tab**: naviga tra celle (esce dalla grid ai bordi)
- **Frecce**: muove focus tra celle adiacenti
- **Page Up / Page Down**: scroll di una pagina e muove focus
- **Enter**: avvia/applica editing
- **Escape**: cancella editing

### Focus tracking
- Focus virtuale (non DOM focus): la grid tiene traccia di cella/riga corrente
- Classe CSS `dojoxGrid-cell-focus` sulla cella focussata
- Scroll automatico per portare la cella in focus nel viewport

### API
```
focus.setFocusCell(inCell, inRowIndex)  // Focus su cella
focus.setFocusIndex(inRow, inCol)       // Focus per indici
focus.next()                            // Prossima cella
focus.previous()                        // Cella precedente
focus.move(rowDelta, colDelta)          // Movimento relativo
focus.scrollIntoView()                  // Scroll per visibilita'
focus.isFocusCell(cell, row)            // Controlla focus
focus.isFirstFocusCell()                // E' la prima?
focus.isLastFocusCell()                 // E' l'ultima?
```

---

## 7. Editing Inline

### Modalita'
- **Double-click** (default): doppio click su cella avvia editing
- **Single-click** (`singleClickEdit: true`): click singolo avvia editing
- **Programmatico**: `doStartEdit(cell, rowIndex)`

### Ciclo di vita
1. `canEdit(cell, rowIndex)` — controlla se cella e' editabile
2. `doStartEdit(cell, rowIndex)` — avvia editing
3. Utente modifica valore nell'editor
4. `doApplyCellEdit(value, rowIndex, fieldIndex)` — applica modifica
5. `doApplyEdit(rowIndex)` — commit riga
6. Oppure: `doCancelEdit(rowIndex)` — annulla

### Editor save/restore
- L'editor salva il suo stato prima di scroll/re-render
- Lo stato viene ripristinato quando la riga torna visibile
- Gestisce il caso di edit durante scroll virtuale

### IE Boomerang Fix
- Workaround per il bug IE dove il focus "rimbalza" durante editing

### API
```
edit.isEditing()                     // In editing?
edit.isEditCell(row, col)            // Cella specifica in editing?
edit.isEditRow(row)                  // Riga in editing?
edit.start(cell, rowIndex)           // Avvia editing
edit.apply()                         // Applica e esci
edit.cancel()                        // Cancella e esci
edit.save(rowIndex, view)            // Salva stato editor
edit.restore(view, rowIndex)         // Ripristina stato editor
```

### Eventi
```
onStartEdit(cell, rowIndex)                      // Inizio editing
onApplyCellEdit(value, rowIndex, fieldIndex)      // Cella modificata
onApplyEdit(rowIndex)                             // Riga committata
onCancelEdit(rowIndex)                            // Editing cancellato
```

---

## 8. Editor Types

La grid include un sistema completo di editor per celle.

### Gerarchia Editor

```
dojox.grid.editors.Base
 +-- dojox.grid.editors.Input        (text input)
 |    +-- dojox.grid.editors.Bool    (checkbox)
 |    +-- dojox.grid.editors.Select  (dropdown select)
 +-- dojox.grid.editors.Dijit        (wrapper dijit widgets)
      +-- dojox.grid.editors.DateTextBox
      +-- dojox.grid.editors.CheckBox
      +-- dojox.grid.editors.Editor
      +-- dojox.grid.editors.ComboBox
```

### Editor Base
Ogni editor ha:
- `format(inDatum, inRowIndex)` — renderizza cella (edit mode o display mode)
- `getValue(inRowIndex)` — ottiene valore corrente
- `setValue(inRowIndex, inValue)` — imposta valore
- `save(inRowIndex)` — salva stato
- `restore(inRowIndex)` — ripristina stato
- `apply(inRowIndex)` — applica modifica alla grid
- `cancel(inRowIndex)` — cancella modifica
- `focus(inRowIndex)` — focus sull'editor
- `dispatchEvent(m, e)` — dispatch eventi
- `alwaysOn` — se true l'editor e' sempre visibile (non solo in edit mode)

### Editor Input
- Campo text standard HTML
- Supporta `selectOnEdit` per selezionare tutto al focus

### Editor Bool
- Checkbox HTML
- `alwaysOn: true` — sempre visibile come checkbox
- Toggle al click

### Editor Select
- Dropdown HTML `<select>`
- `options: []` — array di opzioni

### Editor Dijit (wrapper per widget dijit)
- Wrappa qualsiasi dijit widget come editor di cella
- **DateTextBox**: selettore data con calendario
- **CheckBox**: dijit checkbox
- **Editor** (RichText): editor rich text
- **ComboBox**: combo box con autocompletamento

---

## 9. Data Model

### Gerarchia

```
Model (base astratta)
 +-- Rows (gestione righe)
      +-- Table (dati array 2D)
      |    +-- Objects (dati array di oggetti)
      +-- Dynamic (caricamento lazy)
           +-- DojoData (integrazione dojo.data stores)
```

### Model Base
- Pattern Observer: notifica cambiamenti a tutti gli osservatori
- Batch updates: `beginUpdate()` / `endUpdate()` per raggruppare notifiche
- Interface: `getRowCount()`, `canSort()`, metodi astratti per dati

### Table Model
- Dati come array 2D (`data[row][col]`)
- Ordinamento in-memory con supporto locale-aware
- CRUD: `setData()`, `insert(data, rowIndex)`, `remove(indices)`
- Stato righe: `fields`, `count`, ecc.

### Dynamic Model
- Caricamento asincrono a pagine (`requestRows(from, count)`)
- Cache delle pagine gia' caricate
- Stato per-riga: `null` (non caricata), dati, "inflight" (in caricamento), "error"
- Gestione inserimenti/rimozioni con ricostruzione cache

### DojoData Model
- Integrazione con `dojo.data` stores (`ItemFileReadStore`, `ItemFileWriteStore`)
- Fetch asincrono con callback
- Supporto `query` per filtrare dati
- Sincronizzazione bidirezionale con lo store
- Ordinamento delegato allo store
- `save()` e `revert()` per persistenza

### API Model
```
model.getRowCount()                    // Numero righe
model.getDatum(rowIndex, fieldIndex)   // Valore cella
model.setDatum(value, rowIndex, field) // Imposta valore
model.insert(data, rowIndex)           // Inserisci riga
model.remove(indices)                  // Rimuovi righe
model.sort(field)                      // Ordina
model.canSort()                        // Ordinabile?
model.beginUpdate() / endUpdate()      // Batch
```

---

## 10. Fields (Definizione Colonne)

### Caratteristiche
- Definizione colonne con nome e tipo
- Accesso per indice o per nome
- `get(inIndex)` — ottiene definizione campo
- `indexOf(name)` — indice per nome

---

## 11. Resize Colonne via Drag

### Caratteristiche
- Drag sull'header per ridimensionare colonne
- Zona di resize: 4px dal bordo destro della cella header
- Larghezza minima: 1px
- Supporto per colSpan: ridimensiona tutte le celle spanning
- Hysteresis: 2px per evitare resize accidentali
- Cursor `col-resize` durante hover sulla zona di resize
- Previene click spurio dopo resize (`bogusClickTime`)

### API
```
headerBuilder.canResize(e)            // Controlla se resizable
headerBuilder.beginColumnResize(e)    // Avvia drag resize
```

---

## 12. Row Bar (Barra Selezione Righe)

### Caratteristiche
- View laterale (`GridRowView`) con larghezza fissa (default 3em)
- No scroll verticale (`noscroll: true`)
- Highlight per selezione e hover
- Classi CSS: `dojoxGrid-rowbar`, `dojoxGrid-rowbar-over`, `dojoxGrid-rowbar-selected`

---

## 13. Batch Update

### Caratteristiche
- `beginUpdate()` / `endUpdate()` per raggruppare modifiche
- Durante batch: le invalidazioni vengono accodate
- Al termine: tutte le invalidazioni vengono applicate insieme
- Evita re-render multipli per operazioni bulk

### API
```
beginUpdate()                 // Inizio batch
endUpdate()                   // Fine batch (applica tutto)
```

---

## 14. Auto-sizing

### Caratteristiche
- `autoWidth`: la grid calcola la larghezza dai contenuti
- `autoHeight`: la grid calcola l'altezza dal numero di righe
- Resize responsive: `resize()` si adatta al container
- Adattamento automatico scrollbar
- Text size polling: rileva cambiamenti font size del browser

### API
```
resize()                      // Ricalcola dimensioni
adaptWidth()                  // Adatta larghezza
adaptHeight()                 // Adatta altezza
```

---

## 15. Eventi Mouse

### Eventi Cella
```
onCellClick(e)                // Click su cella
onCellDblClick(e)             // Double-click su cella
onCellContextMenu(e)          // Right-click su cella
onCellMouseOver(e)            // Hover su cella
onCellMouseOut(e)             // Mouse esce da cella
onCellMouseDown(e)            // Mouse down su cella
```

### Eventi Riga
```
onRowClick(e)                 // Click su riga
onRowDblClick(e)              // Double-click su riga
onRowContextMenu(e)           // Right-click su riga
onRowMouseOver(e)             // Hover su riga
onRowMouseOut(e)              // Mouse esce da riga
onRowMouseDown(e)             // Mouse down su riga
onMouseOverRow(e)             // Mouse entra in riga (include rowbar)
onMouseOutRow(e)              // Mouse esce da riga (include rowbar)
```

### Eventi Header
```
onHeaderClick(e)              // Click su header
onHeaderDblClick(e)           // Double-click su header
onHeaderContextMenu(e)        // Right-click su header
onHeaderCellClick(e)          // Click su header cell
onHeaderCellDblClick(e)       // Double-click su header cell
onHeaderCellContextMenu(e)    // Right-click su header cell
onHeaderCellMouseOver(e)      // Hover su header cell
onHeaderCellMouseOut(e)       // Mouse esce da header cell
onHeaderCellMouseDown(e)      // Mouse down su header cell
onHeaderMouseOver(e)          // Mouse su header row
onHeaderMouseOut(e)           // Mouse esce da header row
```

### Evento decorato
Ogni evento e' "decorato" con proprieta' aggiuntive:
```javascript
e.grid           // riferimento alla grid
e.sourceView     // view sorgente
e.cellNode       // nodo DOM della cella
e.cellIndex      // indice cella
e.cell           // cell object
e.rowNode        // nodo DOM della riga
e.rowIndex       // indice riga (-1 per header)
```

---

## 16. Keyboard Events

```
onKeyDown(e)                  // Keydown (handler principale)
onKeyEvent(e)                 // Tutti i key events
```

### Tasti gestiti
| Tasto | Azione |
|-------|--------|
| Escape | Cancella editing |
| Enter | Applica/avvia editing |
| Tab | Prossima cella (esce a fine grid) |
| Shift+Tab | Cella precedente (esce a inizio grid) |
| Freccia Su | Riga sopra |
| Freccia Giu' | Riga sotto |
| Freccia Sinistra | Cella sinistra |
| Freccia Destra | Cella destra |
| Page Up | Scroll su + focus |
| Page Down | Scroll giu' + focus |

---

## 17. Drag & Drop (basso livello)

### Caratteristiche
- Namespace `dojox.grid.drag` con utility generiche
- Hysteresis: 2px prima di considerare un movimento come drag
- Capture/release mouse a livello document
- Usato internamente per resize colonne header

### API
```
drag.start(element, onDrag, onEnd, event, onStart)
drag.end()
drag.calcDelta(event)         // deltaX, deltaY
drag.hasMoved(event)          // Supera hysteresis?
```

---

## 18. Utility (lib.js)

### DOM Navigation
- `getTr`, `getTd`, `getTrIndex`, `getTdIndex` — navigazione table
- `findTable(node)` — risale al TABLE padre
- `ascendDom(node, while)` — risale il DOM

### Style
- `setStyleText`, `getStyleText` — cssText diretto
- `setStyle`, `setStyleHeightPx` — stili singoli

### Event Funneling
- `funnelEvents(node, object, method)` — connette tutti gli eventi mouse+keyboard a un handler

### Job Manager
- `jobs.job(name, delay, fn)` — setTimeout con nome (auto-cancella precedente)
- `jobs.cancel(handle)`, `jobs.cancelJob(name)` — cancella

### Scrollbar Detection
- `getScrollbarWidth()` — misura larghezza scrollbar (cached)

### Text Size Polling
- `initTextSizePoll()` — rileva cambio font size del browser

---

## 19. Markup Factory

La grid supporta creazione dichiarativa da HTML:

```html
<table dojoType="dojox.Grid" store="myStore">
  <colgroup span="1" width="100px"/>
  <thead>
    <tr>
      <th field="name">Nome</th>
      <th field="email" width="200px">Email</th>
    </tr>
  </thead>
</table>
```

Il parser (`Grid.markupFactory`) converte:
- `<colgroup>` in width definitions
- `<thead><tr><th>` in cell definitions
- Attributi `field`, `width`, `cellType`, `options` ecc.

---

## Riepilogo Feature

| Categoria | Feature |
|-----------|---------|
| **Rendering** | Virtual scrolling, paginazione, cache pagine, pre-compilazione HTML |
| **Layout** | Multi-view, colonne bloccate, subrows, colSpan/rowSpan, view elastica |
| **Sizing** | Auto width/height, resize colonne drag, text size polling |
| **Selezione** | Singola, multipla (Ctrl), range (Shift), pre-conditions |
| **Focus** | Navigazione tastiera, focus virtuale, scroll automatico |
| **Editing** | Inline single/double-click, editor types (Input, Bool, Select, Dijit), save/restore |
| **Ordinamento** | Click header, asc/desc toggle, delegato a model |
| **Data Model** | Table (array 2D), Objects, Dynamic (lazy), DojoData (dojo.data stores) |
| **Eventi** | 30+ eventi mouse/keyboard, eventi decorati con context |
| **Batch** | beginUpdate/endUpdate per operazioni bulk |
| **DnD** | Drag per resize colonne, framework drag basso livello |
| **Markup** | Creazione dichiarativa da HTML table |
| **Styling** | Zebra striping, row states, cell states, custom CSS |
