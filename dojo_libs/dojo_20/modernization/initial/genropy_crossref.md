# Giojo.js — Cross-Reference GenroPy <-> Dojo

## Contesto

Analisi delle dipendenze reali tra il layer JavaScript di GenroPy (`gnrjs/gnr_d11/js/`) e Dojo/dijit/dojox. Identifica esattamente quali moduli Dojo sono usati e come.

---

## Panoramica

- **25 file JavaScript GenroPy**, ~1.9 MB totali
- **23 file su 25 (95%)** usano API Dojo
- **~1.300 occorrenze** totali di `dojo.*`, `dijit.*`, `dojox.*`
- **75+ widget dijit/dojox** wrappati direttamente
- **13+ monkey-patch** critiche su classi Dojo

**Conclusione: GenroPy e' INTRINSECAMENTE LEGATO a Dojo 1.x. Senza Dojo, GenroPy non funziona.**

---

## 1. File GenroPy per Dimensione e Ruolo

| File | Dimensione | Righe | Ruolo | Dipendenza Dojo |
|------|-----------|-------|-------|-----------------|
| **genro_components.js** | 355K | 8.075 | Componenti UI (Palette, Frame, Form) | ALTA - dojo.declare, dojo.connect |
| **genro_widgets.js** | 241K | 6.056 | Wrapper 75+ widget dijit/dojox | CRITICA - tutto |
| **genro_grid.js** | 204K | 5.051 | Grid (wrappa dojox.grid) | CRITICA - dojox.grid.* + patch |
| **genro_frm.js** | 128K | 3.328 | Form handler, validazione | ALTA - dojo.Deferred, dijit.form |
| **genro_extra.js** | 100K | — | Funzionalita' extra | MEDIA |
| **genro_wdg.js** | 94K | 2.324 | Widget factory + catalogo | CRITICA - mappa 75+ widget |
| **genro.js** | 88K | 2.493 | Core GenroPy | ALTA - 100+ occorrenze dojo.* |
| **genro_dom.js** | 82K | — | DOM manipulation | ALTA - dojo.query, dojo.style |
| **gnrbag.js** | 81K | — | Bag (struttura dati core) | MEDIA - dojo.declare, Deferred |
| **gnrdomsource.js** | 80K | — | DOM source / data binding | MEDIA - dojo.declare, connect |
| **gnrlang.js** | 70K | — | Language/formatting utilities | ALTA - dojo.date.locale, dojo.number |
| **genro_dev.js** | 68K | — | Developer tools | MEDIA |
| **genro_dlg.js** | 62K | 1.444 | Dialogs, floating messages | ALTA - dijit.Dialog, dojo.fx |
| **genro_patch.js** | 59K | 1.423 | Monkey-patch Dojo | CRITICA - 13+ patch |
| **genro_rpc.js** | 41K | — | RPC/comunicazione server | ALTA - dojo.xhr*, Deferred |
| **genro_tree.js** | 41K | 989 | Tree widget | ALTA - dijit.Tree |
| **gnrstores.js** | 30K | — | Data stores (dojo.data API) | ALTA - implementa dojo.data.* |
| **genro_src.js** | 24K | — | Source handler | MEDIA |
| **gnrwebsocket.js** | 24K | — | WebSocket | BASSA - solo declare + Deferred |
| **genro_google.js** | 8K | — | Google integration | BASSA |
| **genro_mobile.js** | 10K | 245 | Mobile/touch support | MEDIA - patch dijit per touch |
| **genro_uo.js** | 8K | — | User objects | BASSA |
| **gnrsharedobjects.js** | 7K | — | Shared objects | BASSA |
| **genro_cordova.js** | 6K | — | Cordova integration | BASSA |

---

## 2. Gerarchia Widget GenroPy

```
gnr.widgets.baseHtml (base di tutti)
    +-- gnr.widgets.baseDojo
    |   +-- Dialog
    |   +-- Editor
    |   +-- SimpleTextarea
    |   +-- ProgressBar
    |   +-- StackContainer
    |   |   +-- TabContainer
    |   +-- BorderContainer
    |   +-- TitlePane
    |   +-- ResizeHandle
    |   +-- FloatingPane
    |   +-- ContentPane
    |   +-- Menu
    |   +-- Tooltip
    |   +-- Button (+ LightButton)
    |   +-- RadioButton
    |   +-- CheckBox
    |   +-- _BaseTextBox
    |   |   +-- TextBox
    |   |   +-- DateTextBox -> DatetimeTextBox
    |   |   +-- TimeTextBox
    |   |   +-- NumberTextBox -> CurrencyTextBox, NumberSpinner
    |   |   +-- Slider (Horizontal, Vertical)
    |   +-- BaseCombo
    |   |   +-- GeoCoderField
    |   |   +-- DynamicBaseCombo -> dbBaseCombo, LocalBaseCombo, RemoteBaseCombo
    |   |   +-- FilteringSelect
    |   |   +-- ComboBox
    |   |   +-- DropDownButton
    |   +-- DojoGrid -> VirtualGrid, VirtualStaticGrid -> IncludedView -> NewIncludedView
    |   +-- Tree
    |
    +-- htmliframe, flexbox, gridbox, iframe, canvas, video
    +-- baseExternalWidget
    +-- uploadable -> img
    +-- fileInput -> fileInputBlind, fileUploader
    +-- StaticMap, GoogleMap
    +-- embed
    |
    +-- gnrwdg (componenti custom)
        +-- TooltipPane -> TooltipMultivalue
        +-- MenuDiv
        +-- ColorTextBox, ColorFiltering
        +-- Palette, PalettePane
        +-- FramePane
        +-- _BaseForm -> BoxForm, FrameForm
        +-- GroupletForm
        +-- PaletteMap, PaletteGrid
        +-- TreeFrame -> PaletteTree
        +-- PaletteImporter
        +-- VideoPickerPalette
```

---

## 3. Catalogo Widget Dijit/Dojox Wrappati

### dijit.form (16 widget)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| CheckBox | dijit.form.CheckBox |
| RadioButton | dijit.form.CheckBox |
| ComboBox | dijit.form.ComboBox |
| CurrencyTextBox | dijit.form.CurrencyTextBox |
| DateTextBox | dijit.form.DateTextBox |
| FilteringSelect | dijit.form.FilteringSelect |
| NumberSpinner | dijit.form.NumberSpinner |
| NumberTextBox | dijit.form.NumberTextBox |
| HorizontalSlider | dijit.form.Slider |
| VerticalSlider | dijit.form.Slider |
| SimpleTextarea | dijit.form.SimpleTextarea |
| MultiSelect | dijit.form.MultiSelect |
| TextBox | dijit.form.TextBox |
| TimeTextBox | dijit.form.TimeTextBox |
| ValidationTextBox | dijit.form.ValidationTextBox |
| Button, ToggleButton, ComboButton, DropDownButton | dijit.form.Button |

### dijit.layout (7 container)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| AccordionContainer | dijit.layout.AccordionContainer |
| ContentPane | dijit.layout.ContentPane |
| BorderContainer | dijit.layout.BorderContainer |
| LayoutContainer | dijit.layout.LayoutContainer |
| SplitContainer | dijit.layout.SplitContainer |
| StackContainer | dijit.layout.StackContainer |
| TabContainer | dijit.layout.TabContainer |

### dijit (altri widget, 11)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| Menu, MenuItem, MenuSeparator, PopupMenuItem | dijit.Menu |
| Toolbar, ToolbarSeparator | dijit.Toolbar |
| Dialog, TooltipDialog | dijit.Dialog |
| ProgressBar | dijit.ProgressBar |
| TitlePane | dijit.TitlePane |
| Tooltip | dijit.Tooltip |
| ColorPalette | dijit.ColorPalette |
| Editor | dijit.Editor + plugins (LinkDialog, FontChoice, TextColor) |
| Tree | dijit.Tree |
| InlineEditBox | dijit.InlineEditBox |

### dojox.layout (4 widget)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| FloatingPane, Dock | dojox.layout.FloatingPane |
| RadioGroup | dojox.layout.RadioGroup |
| ResizeHandle | dojox.layout.ResizeHandle |
| SizingPane | dojox.layout.SizingPane |

### dojox.widget (8 widget)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| FisheyeList | dojox.widget.FisheyeList |
| Loader | dojox.widget.Loader |
| Toaster | dojox.widget.Toaster |
| FileInput | dojox.widget.FileInput |
| FileInputBlind, FileInputAuto | dojox.widget.FileInputAuto |
| ColorPicker | dojox.widget.ColorPicker |
| SortList | dojox.widget.SortList |
| TimeSpinner | dojox.widget.TimeSpinner |

### dojox.image (4 widget)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| Gallery | dojox.image.Gallery |
| Lightbox | dojox.image.Lightbox |
| SlideShow | dojox.image.SlideShow |
| ThumbnailPicker | dojox.image.ThumbnailPicker |

### dojox.presentation (2 widget)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| Deck | dojox.presentation.Deck |
| Slide | dojox.presentation.Slide |

### dojox.grid (2 widget)

| Widget GenroPy | Widget Dojo |
|---------------|-------------|
| DojoGrid | dojox.grid.DataGrid |
| VirtualGrid | dojox.grid.VirtualGrid |

---

## 4. API Dojo Core Usate (per frequenza)

### Infrastructure (usate ovunque)

| API | Occorrenze | File | Equivalente moderno |
|-----|-----------|------|---------------------|
| `dojo.declare` | ~40+ | 18 file | ES6 `class` |
| `dojo.hitch` | ~20+ | 4 file | `.bind()` o arrow functions |
| `dojo.connect` | ~60+ | 9 file | `addEventListener` |
| `dojo.forEach` | ~40+ | 6 file | `Array.prototype.forEach` |
| `dojo.query` | ~20+ | 4 file | `querySelectorAll` |
| `dojo.byId` | ~25+ | 6 file | `getElementById` |
| `dojo.subscribe/publish` | ~7+ | 2 file | Custom EventEmitter |
| `dojo.Deferred` | ~10+ | 3 file | `Promise` |

### DOM & Styling

| API | File | Equivalente moderno |
|-----|------|---------------------|
| `dojo.style` | genro_dom.js, genro_widgets.js | `element.style` |
| `dojo.addClass/removeClass/hasClass` | 4 file | `classList` API |
| `dojo.coords/marginBox` | genro_patch.js, genro_mobile.js | `getBoundingClientRect()` |
| `dojo.getComputedStyle` | genro_grid.js | `getComputedStyle()` |
| `dojo.body` | genro.js, genro_widgets.js | `document.body` |
| `dojo.stopEvent` | 4 file | `e.preventDefault(); e.stopPropagation()` |

### Data & Formatting

| API | File | Equivalente moderno |
|-----|------|---------------------|
| `dojo.date.locale.format/parse` | gnrlang.js | `Intl.DateTimeFormat` |
| `dojo.number.format/parse` | gnrlang.js | `Intl.NumberFormat` |
| `dojo.currency.format` | gnrlang.js | `Intl.NumberFormat` con currency |
| `dojo.data.api.*` | gnrstores.js | Custom store / REST |
| `dojo.cookie` | genro.js | `document.cookie` o Cookie API |

### HTTP & Network

| API | File | Equivalente moderno |
|-----|------|---------------------|
| `dojo.xhrGet/Post/Put/Delete` | genro_rpc.js | `fetch()` API |
| `dojo.rawXhrPost/Put` | genro_rpc.js | `fetch()` con body raw |

### Effects & DnD

| API | File | Equivalente moderno |
|-----|------|---------------------|
| `dojo.fx.wipeIn/wipeOut` | genro_dlg.js | CSS transitions |
| `dojo.fx.fadeIn/fadeOut` | genro_dom.js | CSS transitions |
| `dojo.dnd.Moveable` | genro_widgets.js, genro_mobile.js | HTML5 Drag API o libreria |

### Widget Utilities

| API | File | Equivalente moderno |
|-----|------|---------------------|
| `dijit.byId` | 5 file | Custom registry |
| `dijit.getEnclosingWidget` | 5 file | Custom DOM traversal |
| `dijit.placeOnScreenAroundElement` | genro_patch.js, genro_dlg.js | Popper.js / Floating UI |
| `dijit.popup.open/close` | genro_patch.js | Custom popup manager |
| `dijit.focus/getFocus` | genro_patch.js | `document.activeElement` |
| `dijit._MasterTooltip` | genro.js | Custom tooltip |

---

## 5. Monkey-Patch Critiche (genro_patch.js)

File dedicato agli override di classi Dojo. **Queste patch sono fix strutturali, non cosmetici.**

| # | Classe Patchata | Cosa Modifica | Motivo |
|---|----------------|---------------|--------|
| 1 | `dijit.placeOnScreenAroundElement` | Posizionamento popup | Fix viewport overflow |
| 2 | `dojo.forEach` | Validazione array nullo | Error handling |
| 3 | `dojo.indexOf` | Date.getTime() comparison | GenroPy usa Date nei dati |
| 4 | `dijit.form._FormWidget._setStateClass` | Controllo stateNode/domNode | Evita errori widget custom |
| 5 | `dijit.getDocumentWindow` | Safari/IE window refs in iframe | Cross-browser fix |
| 6 | `XMLHttpRequest.sendAsBinary` | Polyfill binary send | Upload file |
| 7 | `dojo.toJson` | Custom serialization GnrBag | GenroPy ha tipo GnrBag |
| 8 | `dojo.dnd.Moveable.onMouseDown` | Disabilita drag pulsante destro | UX context menu |
| 9 | `dijit.layout.StackController.onCloseButtonClick` | Hook chiusura tab | Customization tab |
| 10 | `dijit.Menu._openMyself` | Riscrittura completa apertura menu | Timing e focus GenroPy |
| 11 | `dijit.form._ComboBoxMenu` | Multi-column dropdown | Droplist GenroPy con colonne |
| 12 | `dijit.form.ComboBoxMixin._onKeyPress` | Keyboard handling combo | Custom keyboard nav |
| 13 | `dijit.layout.BorderContainer` | Riscrittura layout + splitter | Layout custom GenroPy |
| 14 | `dijit.layout._Splitter` | Persistenza size su cookie | Drag + salvataggio stato |

---

## 6. Moduli Dojo/Dijit/Dojox Effettivamente Usati

### Da dojo/ (USATI)

| Modulo | Usato in | Note |
|--------|---------|------|
| **dojo._base.declare** | Ovunque | Sistema classi — CRITICO |
| **dojo._base.lang** | Ovunque | hitch, isString, isArray, etc. |
| **dojo._base.array** | Ovunque | forEach, map, filter, indexOf |
| **dojo._base.connect** | Ovunque | connect, subscribe, publish |
| **dojo._base.Deferred** | gnrstores, gnrbag, genro_rpc | Async — CRITICO |
| **dojo._base.query** | 4+ file | CSS selectors |
| **dojo._base.html** | 6+ file | byId, addClass, style, coords |
| **dojo._base.event** | 4+ file | stopEvent |
| **dojo._base.xhr** | genro_rpc | HTTP requests — CRITICO |
| **dojo._base.json** | genro_patch | toJson (patchato) |
| **dojo.fx** | genro_dlg, genro_dom | wipeIn/Out, fadeIn/Out |
| **dojo.date.locale** | gnrlang | Date formatting — CRITICO |
| **dojo.number** | gnrlang | Number formatting |
| **dojo.currency** | gnrlang | Currency formatting |
| **dojo.cookie** | genro, genro_tree | Cookie storage |
| **dojo.dnd** | genro_widgets, genro_mobile | Moveable, Mover |
| **dojo.data.api** | gnrstores | Read, Write, Identity, Notification |
| **dojo.i18n** | genro | Locale normalization |
| **dojo.keys** | genro | Keyboard constants |

### Da dojo/ (NON USATI — eliminabili)

| Modulo | Note |
|--------|------|
| dojo._firebug | Console debug — obsoleto |
| dojo.rpc | RPC framework — non usato |
| dojo.io.iframe | iframe transport — non usato |
| dojo.io.script | JSONP — non usato |
| dojo.back | History management — non usato |
| dojo.behavior | CSS behavior binding — non usato |
| dojo.OpenAjax | Pub/sub spec defunta |
| dojo.jaxer | Jaxer integration — morto |
| dojo.AdapterRegistry | Registry pattern — non usato |
| dojo.DeferredList | Deferred aggregator — non usato direttamente |
| dojo.string | String utilities — non usato |
| dojo.regexp | RegExp utilities — non usato direttamente |
| dojo.colors | Extended colors — non usato |
| dojo.parser | Widget parser (usato indirettamente da dijit) |

### Da dijit/ (USATI)

| Modulo | Wrappato in |
|--------|------------|
| **dijit._base (focus, manager, place, popup, wai)** | Infrastructure di tutti i widget |
| **dijit.form.TextBox** | genro_wdg.js |
| **dijit.form.ValidationTextBox** | genro_wdg.js |
| **dijit.form.NumberTextBox** | genro_wdg.js |
| **dijit.form.CurrencyTextBox** | genro_wdg.js |
| **dijit.form.DateTextBox** | genro_wdg.js |
| **dijit.form.TimeTextBox** | genro_wdg.js |
| **dijit.form.ComboBox** | genro_wdg.js + patch |
| **dijit.form.FilteringSelect** | genro_wdg.js |
| **dijit.form.CheckBox** | genro_wdg.js |
| **dijit.form.Button** | genro_wdg.js |
| **dijit.form.Slider** | genro_wdg.js |
| **dijit.form.SimpleTextarea** | genro_wdg.js |
| **dijit.form.MultiSelect** | genro_wdg.js |
| **dijit.form.NumberSpinner** | genro_wdg.js |
| **dijit.layout.BorderContainer** | genro_wdg.js + heavy patch |
| **dijit.layout.TabContainer** | genro_wdg.js |
| **dijit.layout.StackContainer** | genro_wdg.js + patch |
| **dijit.layout.ContentPane** | genro_wdg.js |
| **dijit.layout.AccordionContainer** | genro_wdg.js |
| **dijit.layout.SplitContainer** | genro_wdg.js |
| **dijit.layout.LayoutContainer** | genro_wdg.js |
| **dijit.Dialog** | genro_wdg.js, genro_dlg.js |
| **dijit.Menu** | genro_wdg.js + heavy patch |
| **dijit.Tree** | genro_tree.js + genro_wdg.js |
| **dijit.tree.ForestStoreModel** | genro_tree.js |
| **dijit.Toolbar** | genro_wdg.js |
| **dijit.Tooltip** | genro.js, genro_wdg.js |
| **dijit.TitlePane** | genro_wdg.js |
| **dijit.ProgressBar** | genro_wdg.js |
| **dijit.ColorPalette** | genro_wdg.js |
| **dijit.Editor** + plugins | genro_wdg.js |
| **dijit.InlineEditBox** | genro_wdg.js |

### Da dijit/ (NON USATI)

| Modulo | Note |
|--------|------|
| dijit._Calendar | Non wrappato direttamente (usato da DateTextBox) |
| dijit._TimePicker | Non wrappato direttamente (usato da TimeTextBox) |
| dijit.Declaration | Non usato |
| dijit.bench, dijit.demos | Test/demo |

### Da dojox/ (USATI)

| Modulo | Wrappato in |
|--------|------------|
| **dojox.grid.DataGrid** | genro_grid.js (+ heavy patching) |
| **dojox.grid.VirtualGrid** | genro_grid.js |
| **dojox.grid._grid.builder** | genro_grid.js (patch) |
| **dojox.layout.FloatingPane** | genro_wdg.js |
| **dojox.layout.ResizeHandle** | genro_wdg.js |
| **dojox.layout.RadioGroup** | genro_wdg.js |
| **dojox.layout.SizingPane** | genro_wdg.js |
| **dojox.widget.FisheyeList** | genro_wdg.js |
| **dojox.widget.Loader** | genro_wdg.js |
| **dojox.widget.Toaster** | genro_wdg.js, genro_dlg.js |
| **dojox.widget.FileInput/Auto** | genro_wdg.js |
| **dojox.widget.ColorPicker** | genro_wdg.js |
| **dojox.widget.SortList** | genro_wdg.js |
| **dojox.widget.TimeSpinner** | genro_wdg.js |
| **dojox.image.Gallery** | genro_wdg.js |
| **dojox.image.Lightbox** | genro_wdg.js |
| **dojox.image.SlideShow** | genro_wdg.js |
| **dojox.image.ThumbnailPicker** | genro_wdg.js |
| **dojox.presentation.Deck/Slide** | genro_wdg.js |
| **dojox.validate.web** | genro.js |

### Da dojox/ (NON USATI — eliminabili)

| Modulo | Note |
|--------|------|
| **dojox.charting** | Non referenziato in GenroPy JS |
| **dojox.gfx** | Non referenziato direttamente |
| **dojox.data** (extended stores) | GenroPy ha gnrstores.js proprio |
| **dojox.fx** | Non usato (solo dojo.fx base) |
| **dojox.wire** | Non usato |
| **dojox.dtl** | Non usato |
| **dojox.rpc** | Non usato |
| **dojox.highlight** | Non usato |
| **dojox.string** | Non usato |
| **dojox.lang** | Non usato |
| **dojox.encoding** | Non usato |
| **dojox.crypto** | Non usato |
| **dojox.collections** | Non usato |
| **dojox.form** (extended) | Non usato |
| **dojox.storage** | Obsoleto (Gears/Flash) |
| **dojox.off** | Obsoleto (Gears) |
| **dojox.flash** | Obsoleto |
| **dojox.av** | Obsoleto |
| **dojox._sql** | Obsoleto |
| **dojox.cometd** | Obsoleto |
| **dojox.sketch** | Non usato |
| **dojox.gfx3d** | Non usato |
| **dojox.analytics** | Non usato |
| **dojox.help** | Non usato |
| **dojox.color** | Non usato |
| **dojox.uuid** | Non usato |
| **dojox.timing** | Non usato |
| **dojox.date** | Non usato |
| **dojox.math** | Non usato |
| **dojox.jsonPath** | Non usato |
| **dojox.xml** | Non usato |
| **dojox.io** | Non usato |
| **dojox.validate** (oltre .web) | Non usato |

---

## 7. Riepilogo: Perimetro Reale da Mantenere in Giojo

### dojo/ — Moduli necessari

```
_base/lang.js          -> declare, hitch, isString, clone, etc.
_base/declare.js       -> sistema classi OOP
_base/connect.js       -> connect, subscribe, publish
_base/Deferred.js      -> async pattern
_base/array.js         -> forEach, map, filter, indexOf
_base/html.js          -> byId, addClass, style, coords
_base/query.js         -> CSS selectors
_base/event.js         -> stopEvent, fixEvent
_base/xhr.js           -> xhrGet/Post/Put/Delete
_base/json.js          -> toJson (patchato da GenroPy)
_base/fx.js            -> Animation base
_base/Color.js         -> Color (usato da fx)
_base/NodeList.js      -> NodeList (usato da query)
_base/window.js        -> body(), doc, global
fx.js                  -> wipeIn, wipeOut, combine, chain
date.js + date/locale  -> date formatting
number.js              -> number formatting
currency.js            -> currency formatting
cookie.js              -> cookie storage
dnd/                   -> Moveable, Mover
data/                  -> dojo.data API (Read, Write, Identity, Notification)
i18n.js                -> locale loading
```

### dijit/ — Widget necessari

```
_base/ (tutti)         -> focus, manager, place, popup, wai, typematic
form/TextBox            form/ValidationTextBox    form/NumberTextBox
form/CurrencyTextBox    form/DateTextBox          form/TimeTextBox
form/ComboBox           form/FilteringSelect      form/CheckBox
form/Button             form/Slider               form/SimpleTextarea
form/MultiSelect        form/NumberSpinner        form/_FormWidget
layout/BorderContainer  layout/TabContainer       layout/StackContainer
layout/ContentPane      layout/AccordionContainer layout/SplitContainer
layout/LayoutContainer  layout/_LayoutWidget      layout/_Splitter
Dialog                  Menu                      Tree + tree/ForestStoreModel
Toolbar                 Tooltip                   TitlePane
ProgressBar             ColorPalette              Editor + _editor/plugins
InlineEditBox
```

### dojox/ — Moduli necessari

```
grid/ (DataGrid, VirtualGrid, _grid/builder, etc.)
layout/FloatingPane     layout/ResizeHandle       layout/RadioGroup
layout/SizingPane
widget/FisheyeList      widget/Loader             widget/Toaster
widget/FileInput        widget/FileInputAuto      widget/ColorPicker
widget/SortList         widget/TimeSpinner
image/Gallery           image/Lightbox            image/SlideShow
image/ThumbnailPicker
presentation/Deck       presentation/Slide
validate/web
```

### dojox/ — NON necessari (eliminabili ~7 MB)

```
charting/    gfx/        gfx3d/      data/ (extended)
dtl/         wire/       rpc/        highlight/
string/      lang/       encoding/   crypto/
collections/ form/ (ext) fx/         storage/
off/         flash/      av/         _sql/
cometd/      sketch/     analytics/  help/
color/       uuid/       timing/     date/
math/        jsonPath/   xml/        io/
```

---

## 8. Nota su dojox.charting e dojox.gfx

**Sorpresa**: `dojox.charting` e `dojox.gfx` NON sono referenziati nel codice JavaScript di GenroPy (`gnr_d11/js/`). Se GenroPy li usa, potrebbe essere:
- Caricati via HTML/template server-side
- Usati in file JS esterni non in questa directory
- Non effettivamente usati

Da verificare con ricerca piu' ampia nel codebase GenroPy.
