# Giojo.js — Report Analisi src/dojox/

## Contesto

Dojox (Dojo eXtensions) e' la libreria estesa di Dojo Toolkit 1.1.2, contenente componenti avanzati, sperimentali e specializzati. E' la parte piu' grande del codebase (~1104 file) ma anche quella con la maggior percentuale di codice obsoleto.

---

## Panoramica Generale

- **1104 file** totali in `src/dojox/`
- **40 moduli** principali
- **~9.1 MB** di codice sorgente
- Architettura modulare: ogni modulo e' un namespace indipendente

---

## 1. Mappa Completa dei Moduli

| # | Modulo | File | Dimensione | Categoria |
|---|--------|------|-----------|-----------|
| 1 | data | 106 | 1.1M | Data Stores |
| 2 | widget | 102 | 608K | Widget UI |
| 3 | grid | 89 | 684K | Data Grid |
| 4 | gfx | 80 | 1.2M | Grafica Vettoriale |
| 5 | dtl | 63 | 452K | Template Engine |
| 6 | charting | 59 | 416K | Grafici |
| 7 | wire | 55 | 312K | Wiring MVC |
| 8 | highlight | 51 | 228K | Syntax Highlighting |
| 9 | rpc | 48 | 308K | RPC/Servizi |
| 10 | layout | 46 | 316K | Layout Avanzati |
| 11 | image | 37 | 864K | Image Widgets |
| 12 | fx | 36 | 240K | Effects |
| 13 | encoding | 35 | 168K | Encoding |
| 14 | lang | 23 | 96K | Utility Linguaggio |
| 15 | gfx3d | 23 | 144K | 3D Graphics |
| 16 | sketch | 20 | 148K | Drawing |
| 17 | storage | 19 | 740K | Storage Provider |
| 18 | collections | 19 | 88K | Data Structures |
| 19 | off | 18 | 460K | Offline Support |
| 20 | form | 15 | 96K | Form Extensions |
| 21 | validate | 13 | 92K | Validazione |
| 22 | string | 13 | 92K | String Utility |
| 23 | analytics | 13 | 84K | Analytics |
| 24 | presentation | 12 | 68K | Presentazioni |
| 25 | flash | 9 | 68K | Flash Integration |
| 26 | av | 9 | 56K | Audio/Video |
| 27 | io | 8 | 56K | I/O Utility |
| 28 | color | 8 | 72K | Color Utils |
| 29 | uuid | 7 | 64K | UUID Generation |
| 30 | timing | 7 | 32K | Timing Utils |
| 31 | date | 6 | 44K | Date Utility |
| 32 | jsonPath | 5 | 36K | JSONPath Query |
| 33 | resources | 4 | 44K | Risorse |
| 34 | math | 4 | 24K | Math Utils |
| 35 | help | 4 | 28K | Help System |
| 36 | crypto | 4 | 16K | Cryptography |
| 37 | cometd | 4 | 44K | Comet Protocol |
| 38 | _sql | 4 | 52K | SQL (Google Gears) |
| 39 | xml | 2 | 16K | XML Utils |

---

## 2. Moduli Probabilmente Usati da GenroPy (Priorita' Alta)

### 2.1 grid/ (89 file, 684K) — Data Grid Avanzata

Componente complesso per visualizzazione e editing tabellare.

**Architettura**:

| Componente | Scopo |
|------------|-------|
| **VirtualGrid.js** (21.5K) | Base grid con scroll virtuale, rendering dinamico load-on-demand |
| **Grid.js** (9.8K) | Wrapper + data model binding con dojox.data stores |

**Sottosistemi** (`_grid/`, 13 file):

| File | Scopo |
|------|-------|
| scroller.js | Virtual scrolling engine |
| view.js, views.js | Rendering system (multi-view per column groups) |
| layout.js | Layout engine (width, column spans) |
| rows.js | Row rendering |
| cell.js | Cell rendering e formatting |
| edit.js | In-cell editing (combobox, textbox, custom editors) |
| selection.js | Single/multi select, checkbox rows |
| focus.js | Focus management, keyboard navigation |
| drag.js | Column drag/reorder |
| rowbar.js | Row header bar |

**Data layer** (`_data/`, 6 file):
- model.js — Data model interface (observer pattern)
- editors.js — Editor definitions per tipo dato
- dijitEditors.js — Integrazione con dijit widgets
- fields.js — Field metadata

**Rilevanza GenroPy**: **ALTA** — Grid e' probabilmente il componente dojox piu' usato per visualizzazione tabellare.

---

### 2.2 gfx/ (80 file, 1.2M) — Libreria Grafica Vettoriale

Backend per charting e grafica vettoriale.

**API principale**: `dojox.gfx.createSurface(node, width, height)` -> surface per disegnare

**Core**:
- `shape.js` — Base shape class (fill, stroke, transform)
- `path.js` — Path drawing (SVG-like)
- `arc.js` — Arc drawing
- `matrix.js` — Matrix transformations
- `Moveable.js`, `Mover.js` — Drag/move system

**Renderer supportati** (multi-backend):

| Renderer | File | Target |
|----------|------|--------|
| **SVG** | svg.js, svg_attach.js | Browser moderni |
| **VML** | vml.js, vml_attach.js | IE6-8 (obsoleto) |
| **Canvas** | canvas.js, canvas_attach.js | HTML5 Canvas |
| **Silverlight** | silverlight.js, silverlight_attach.js | Obsoleto (EOL 2021) |

**Rilevanza GenroPy**: **MEDIA-ALTA** — Backend di charting. VML e Silverlight eliminabili.

---

### 2.3 charting/ (59 file, 416K) — Libreria Grafici

**Core**:
- `Chart2D.js` — API principale per grafici 2D (usa dojox.gfx)
- `Chart3D.js` — Versione 3D (deprecata)
- `Theme.js`, `Series.js`, `Element.js` — Styling e dati
- `scaler.js` — Algoritmi di scaling

**Tipi di grafici** (`plot2d/`, 19 file):

| Tipo | Varianti |
|------|----------|
| Lines | Lines, StackedLines |
| Areas | Areas, StackedAreas |
| Bars | Bars, StackedBars, ClusteredBars |
| Columns | Columns, StackedColumns, ClusteredColumns |
| Scatter | Scatter, MarkersOnly |
| Pie | Pie |
| Grid | Grid (sfondo) |

**Temi** (`themes/`, 14 file): PlotKit, Tufte, e altri.

**Rilevanza GenroPy**: **MEDIA** — Per dashboard e visualizzazioni dati.

---

## 3. Moduli di Utility

### 3.1 data/ (106 file, 1.1M) — Extended Data Stores

**Store per API esterne**:
- FlickrStore, FlickrRestStore — Flickr API
- PicasaStore — Google Picasa API
- SnapLogicStore — SnapLogic API
- AtomReadStore — Atom feed
- OpmlStore — OPML feed

**Store per formati dati**:
- CsvStore — File CSV
- HtmlTableStore — Tabelle HTML
- HtmlStore — Documenti HTML
- XmlStore — XML generico
- jsonPathStore — JSONPath query

**Store query/REST**:
- QueryReadStore — Server-side query con paging
- KeyValueStore — Semplice key-value

**Rilevanza**: **MEDIA-BASSA** — GenroPy usa principalmente dojo.data e REST.

### 3.2 string/ (13 file, 92K) — String Utility

- `sprintf.js` — C-style sprintf
- `tokenize.js` — Tokenization
- `Builder.js` — String builder pattern

**Rilevanza**: **BASSA**

### 3.3 lang/ (23 file, 96K) — Language Utilities

- `functional.js` — Functional programming (curry, compose)
- `utils.js` — Misc utilities

**Rilevanza**: **BASSA**

### 3.4 encoding/ (35 file, 168K) — Encoding

- `base64.js`, `easy64.js`, `ascii85.js`, `bits.js`

**Rilevanza**: **BASSA**

### 3.5 crypto/ (4 file, 16K) — Cryptography

- `MD5.js` — MD5 hash (deprecato)
- `Blowfish.js` — Blowfish cipher

**Rilevanza**: **BASSA** — Algoritmi obsoleti

### 3.6 collections/ (19 file, 88K) — Data Structures

- ArrayList, Dictionary, Stack, Queue, BinaryTree, SortedList, Set

**Rilevanza**: **BASSA** — Strutture dati JS native sono sufficienti

---

## 4. Moduli Widget e UI

### 4.1 widget/ (102 file, 608K) — Widget Vari

**UI Widgets**:
- ColorPicker — HSV color picker
- Rating — Star rating
- Toaster — Toast notification
- Wizard — Wizard dialog

**List Widgets**:
- FisheyeList — Fisheye effect
- SortList — Sortable list

**Input Widgets**:
- MultiComboBox — Multi-select combobox
- FileInput, FileInputAuto — File upload
- TimeSpinner — Time picker

**Rilevanza**: **MEDIA-BASSA** — Widget specializzati

### 4.2 layout/ (46 file, 316K) — Layout Avanzati

- BorderContainer.js — **OBSOLETO** (moved to dijit)
- FloatingPane — Window flottante
- ExpandoPane — Pane espandibile
- ScrollPane — Scroll customizzato
- DragPane — Pane draggabile
- ResizeHandle — Handle per resize

**Rilevanza**: **BASSA** — BorderContainer moved to dijit, resto specializzato

### 4.3 image/ (37 file, 864K) — Image Widgets

- Gallery — Image gallery
- Lightbox — Lightbox viewer
- SlideShow — Slideshow
- Magnifier — Image zoom
- ThumbnailPicker — Thumbnail selector

**Rilevanza**: **BASSA** — Specializzati

### 4.4 form/ (15 file, 96K) — Form Extensions

- CheckedMultiSelect — Multi-select con checkbox
- DropDownSelect — Dropdown select
- PasswordValidator — Password strength

**Rilevanza**: **BASSA** — Estensioni minori

---

## 5. Moduli Template/MVC

### 5.1 dtl/ (63 file, 452K) — Django Template Language

Port JavaScript di Django Template Language.
- Sintassi: `{{ var }}`, `{% tag %}`, `{{ value|filter }}`
- Mixin `_Templated` e `_HtmlTemplated` per widget
- Server-side o client-side rendering

**Rilevanza**: **BASSA** — GenroPy usa template server-side Python

### 5.2 wire/ (55 file, 312K) — Wiring MVC

- Declarative data binding
- Model <-> View sync
- Property/attribute binding
- Adapters: TextAdapter, TableAdapter, TreeAdapter

**Rilevanza**: **MEDIA-BASSA** — Pattern MVC, GenroPy potrebbe usarlo client-side

### 5.3 rpc/ (48 file, 308K) — RPC Extended

- SMD-based RPC
- JSON-RPC 2.0
- REST store: JsonRestStore, CouchDBRestStore

**Rilevanza**: **MEDIA** — REST store potrebbe essere usato da GenroPy

---

## 6. Effects e Animations

### fx/ (36 file, 240K) — Effects Avanzati

- easing.js — 20+ easing curves
- scroll.js — Scroll animations
- style.js — Style animations
- Shadow.js — Shadow effect

**Rilevanza**: **BASSA** — CSS animations sono lo standard moderno

---

## 7. Moduli Specializzati

| Modulo | File | Dimensione | Scopo | Rilevanza |
|--------|------|-----------|-------|-----------|
| highlight | 51 | 228K | Syntax highlighting (40+ linguaggi) | Bassa |
| gfx3d | 23 | 144K | 3D vector graphics | Bassa |
| presentation | 12 | 68K | Slideshow/presentazioni | Bassa |
| sketch | 20 | 148K | Drawing canvas | Bassa |
| color | 8 | 72K | Color manipulation, gradienti | Bassa-Media |
| jsonPath | 5 | 36K | JSONPath query | Bassa-Media |
| uuid | 7 | 64K | UUID generation (v1, v4) | Bassa |
| timing | 7 | 32K | ThreadPool, Sequence | Bassa |
| date | 6 | 44K | POSIX, PHP date formats | Bassa |
| math | 4 | 24K | Matrix, curves | Bassa |
| analytics | 13 | 84K | Analytics tracking (legacy) | Bassa |
| help | 4 | 28K | Help console | Bassa |
| xml | 2 | 16K | XML DOM parser | Bassa |
| validate | 13 | 92K | Form validation | Bassa |
| io | 8 | 56K | XHR multipart | Bassa |

---

## 8. Moduli Obsoleti — Eliminabili Subito

| Modulo | File | Dimensione | Motivo | Tecnologia morta |
|--------|------|-----------|--------|------------------|
| **storage** | 19 | 740K | Google Gears, Flash, Adobe AIR | Gears EOL 2008, Flash EOL 2020, AIR EOL |
| **off** | 18 | 460K | Offline via Google Gears | Gears EOL 2008 |
| **flash** | 9 | 68K | Flash integration | Flash EOL 2020 |
| **av** | 9 | 56K | Audio/video via Flash | Flash EOL 2020, HTML5 `<audio>/<video>` |
| **_sql** | 4 | 52K | SQL via Google Gears | Gears EOL 2008, IndexedDB |
| **cometd** | 4 | 44K | Comet long-polling | WebSocket standard |
| **gfx/silverlight.js** | 2 | ~20K | Silverlight renderer | Silverlight EOL 2021 |
| **gfx/vml.js** | 2 | ~30K | VML renderer per IE6-8 | IE morto |

**Totale eliminabile**: **~1.47 MB (16% del codice dojox)**

### Sostituzione moderna per moduli obsoleti

| Obsoleto | Sostituzione |
|----------|-------------|
| storage (Gears/Flash) | `localStorage`, `IndexedDB` |
| off (Gears offline) | Service Workers |
| flash, av | HTML5 `<audio>`, `<video>`, Web Audio API |
| _sql (Gears SQL) | IndexedDB, sql.js |
| cometd | WebSocket, Server-Sent Events |
| Silverlight renderer | SVG/Canvas (gia' supportati) |
| VML renderer | SVG (supportato ovunque) |

---

## 9. Classificazione Finale per Azioni

### A. Usati probabilmente da GenroPy (mantenere)

| Modulo | Motivo |
|--------|--------|
| **grid** | Visualizzazione tabellare, editing inline |
| **gfx** (SVG+Canvas) | Backend per charting |
| **charting** | Dashboard, visualizzazioni dati |

### B. Potenzialmente utili (verificare con cross-reference)

| Modulo | Motivo |
|--------|--------|
| **data** | Store specializzati (CSV, XML, REST) |
| **rpc** | REST store, JSON-RPC |
| **wire** | Data binding client-side |
| **widget** | Toast, Wizard, ColorPicker |
| **image** | Gallery, Lightbox (se usati) |

### C. Utility minori (mantenere se usati)

| Modulo | Motivo |
|--------|--------|
| color, jsonPath, validate, form | Uso case-specific |

### D. Eliminabili subito (~1.47 MB)

| Modulo | Dimensione |
|--------|-----------|
| storage | 740K |
| off | 460K |
| flash | 68K |
| av | 56K |
| _sql | 52K |
| cometd | 44K |
| gfx/silverlight + gfx/vml | ~50K |

### E. Eliminabili se non usati

| Modulo | Dimensione | Motivo |
|--------|-----------|--------|
| dtl | 452K | Template engine (GenroPy usa Python) |
| highlight | 228K | Syntax highlighting specializzato |
| presentation | 68K | Slideshow |
| sketch | 148K | Drawing canvas |
| analytics | 84K | Tracking legacy |
| help | 28K | Help console |

---

## 10. Riepilogo Dimensioni

```
Totale dojox:           ~9.1 MB
Eliminabile subito:     ~1.47 MB (16%)
Eliminabile se non usato: ~1.0 MB (11%)
Core da preservare:     ~2.3 MB (grid + gfx + charting)
Resto (utility/widget): ~4.3 MB (47%)
```
