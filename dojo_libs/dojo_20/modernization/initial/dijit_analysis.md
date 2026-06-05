# Giojo.js — Report Analisi src/dijit/

## Contesto

Dijit e' il framework UI widget di Dojo Toolkit 1.1.2. Contiene widget completi per form, layout, dialog, tree, editor e altro. E' il cuore dell'interfaccia utente utilizzata da GenroPy.

---

## Panoramica Generale

- **863 file** totali in `src/dijit/`
- **490 file (57%) sono CSS themes** — candidato principale per cleanup
- **~74 file JavaScript** core (escludendo nls/ e uncompressed)
- **~16K righe di codice** JS (escludendo localization)
- **16 lingue** supportate per localizzazione

---

## 1. Fondamenti (_base/) — Mixin e Infrastructure

Il sistema si basa su mixin composabili via `dojo.declare()`.

| File | Righe | Scopo | API principali |
|------|-------|-------|----------------|
| **focus.js** | 342 | Focus management, widget activation stack | `dijit.focus()`, `dijit._curFocus`, `dijit._activeStack` |
| **manager.js** | 194 | Widget registry (singleton) | `dijit.registry.add()`, `dijit.byId()`, `dijit.WidgetSet` |
| **place.js** | 213 | Positioning/placement on screen | `dijit.placeOnScreen()`, `dijit.placeOnScreenAroundElement()` |
| **popup.js** | 269 | Popup widget lifecycle, z-index stacking | `dijit.popup.open()`, `dijit.popup.close()` |
| **typematic.js** | 139 | Keyboard/mouse repeat events | `dijit.typematic.trigger()` |
| **wai.js** | 143 | ARIA/WAI accessibility attributes | `dijit.setWaiRole()`, `dijit.setWaiState()` |
| **window.js** | 47 | Window/iframe utilities | `dijit.getDocumentWindow()` |
| **scroll.js** | 29 | Scroll utilities | `dijit.scrollIntoView()` |
| **sniff.js** | 45 | Browser detection | CSS classes (dj_ie, dj_opera, dj_gecko) |
| **bidi.js** | 13 | Right-to-left support | `dijitRtl` class |

### Architettura chiave

- **Widget Registry**: `dijit.registry` (istanza di `dijit.WidgetSet`) traccia tutti i widget attivi per ID
- **Focus Stack**: `dijit._activeStack` — array di widget ID che rappresentano il percorso di focus (es. Dialog -> Button)
- **Popup System**: Gestisce z-index, background iframe, posizionamento attorno ai target (Menu, ComboBox, Tooltip)

---

## 2. Widget Standalone (root di dijit/)

| Widget | Righe | Mixins | Scopo |
|--------|-------|--------|-------|
| **Dialog.js** | ~600 | `_Widget`, `_Templated`, `ContentPane` | Modal dialog con underlay, form support, draggable |
| **Menu.js** | ~300 | `_Widget`, `_Templated`, `_KeyNavContainer` | Context/dropdown menu con keyboard nav |
| **Tree.js** | ~500 | `_Widget`, `_Templated`, `_Container` | Tree hierarchical con lazy loading, expand/collapse |
| **Editor.js** | ~400 | `_editor.RichText` | Rich-text editor con toolbar e plugin system |
| **Tooltip.js** | ~200 | `_Widget`, `_Templated` | Tooltips con posizionamento smart |
| **TitlePane.js** | ~300 | `_Widget`, `_Templated`, `_Container` | Collapsible pane con titolo |
| **Toolbar.js** | ~200 | `_Widget`, `_Container` | Horizontal toolbar container |
| **ProgressBar.js** | ~150 | `_Widget`, `_Templated` | Progress bar con percentuale |
| **ColorPalette.js** | ~200 | `_Widget`, `_Templated` | Color picker grid |
| **InlineEditBox.js** | ~300 | `_Widget`, `_Templated` | Inline editable text |
| **_Calendar.js** | ~300 | `_Widget`, `_Templated`, `_Container` | Date picker calendar |
| **_TimePicker.js** | ~250 | `_Widget`, `_Templated` | Time spinner selector |
| **Declaration.js** | ~100 | — | Marker per dichiarare widget da markup |

### Pattern unificato di dichiarazione widget

```javascript
dojo.declare("dijit.WidgetName",
  [dijit._Widget, dijit._Templated, ...],
  {
    templateString: "...",        // HTML inline o da file
    postCreate: function() { },   // Hook di init
    startup: function() { }       // Hook post-layout
  }
);
```

---

## 3. Form Widget (form/) — 18 widget

### Gerarchia base

```
dijit.form._FormWidget (340 righe)
  +-- state management (_onMouse, _setStateClass)
  +-- attributeMap per DOM sync
  +-- setAttribute() per disabled/readOnly/tabIndex

dijit.form._FormValueWidget extends _FormWidget
  +-- value storage, getValue(), setValue()
```

### Widget disponibili

| Widget | Righe | Tipo | Scopo |
|--------|-------|------|-------|
| **Button.js** | 425 | Pulsanti | Button, SubmitButton, ResetButton con state styling |
| **TextBox.js** | 185 | Input text | Base per tutti i textbox (trim, uppercase, format) |
| **ValidationTextBox.js** | 308 | Input validato | Regex validation, error state, tooltip errore |
| **Textarea.js** | 261 | Textarea | Multi-line text con auto-resize |
| **SimpleTextarea.js** | ~50 | Textarea | Simple textarea senza resize |
| **CheckBox.js** | 133 | Checkbox | Checkbox e RadioButton con state styling |
| **ComboBox.js** | 1060 | Autocomplete | Autocomplete dropdown con dojo.data query |
| **FilteringSelect.js** | 242 | Select filtrato | Select con filtering + validazione |
| **MultiSelect.js** | 84 | Multi-select | Multiple selection nativa |
| **Slider.js** | 481 | Range slider | Horizontal/vertical slider con track |
| **NumberTextBox.js** | 79 | Input numerico | Validazione numerica locale |
| **CurrencyTextBox.js** | 51 | Input valuta | Formattazione valuta |
| **DateTextBox.js** | ~100 | Date picker | Input data con calendario popup |
| **TimeTextBox.js** | ~100 | Time picker | Input orario con spinner |
| **_DateTimeTextBox.js** | 175 | Base date/time | Classe base per date/time |
| **_Spinner.js** | 117 | Spinner | Pulsanti up/down per NumberSpinner |
| **NumberSpinner.js** | ~70 | Number spinner | Input numerico con +/- |
| **Form.js** | 384 | Form container | Wrapper che colleziona valori dei figli |

### Caratteristiche comuni dei form widget

- `dojoAttachEvent` per wiring event handlers al template
- `dojoAttachPoint` per collegare nodi DOM a proprieta' JS
- `attributeMap` per sincronizzare proprieta' dell'oggetto al DOM
- Validazione via `constraints` (regex, range, date format)
- State classes: `dijitHover`, `dijitActive`, `dijitFocused`, `dijitDisabled`, `dijitError`

---

## 4. Layout Widget (layout/) — 9 container

| Widget | Righe | Scopo |
|--------|-------|-------|
| **BorderContainer.js** | 515 | Layout con 5 regioni (top, bottom, left, right, center) + splitter |
| **TabContainer.js** | 184 | Tabbed interface con tab strip |
| **StackContainer.js** | 493 | Stack di pane, solo una visibile alla volta |
| **AccordionContainer.js** | 229 | Pane collassabili mutuamente esclusivi |
| **SplitContainer.js** | 553 | Container splittabile (deprecated in Dojo 1.6+) |
| **ContentPane.js** | 445 | Generic content holder con caricamento AJAX via `href` |
| **LayoutContainer.js** | 74 | Helper per child layout |
| **_LayoutWidget.js** | 188 | Base class per tutti i container layout |
| **LinkPane.js** | 36 | ContentPane con template link |

### Pattern di layout dichiarativo

```html
<div dojoType="dijit.layout.BorderContainer">
  <div dojoType="dijit.layout.ContentPane" region="top" style="height:100px">Header</div>
  <div dojoType="dijit.layout.ContentPane" region="center">Main</div>
  <div dojoType="dijit.layout.ContentPane" region="right" style="width:200px">Sidebar</div>
</div>
```

Child properties: `region` (top/bottom/left/right/center), `splitter` (boolean), `layoutAlign`

---

## 5. Editor (_editor/) — Rich Text Editor

| File | Righe | Scopo |
|------|-------|-------|
| **RichText.js** | ~800 | Core editor iframe-based (contentEditable) |
| **_Plugin.js** | ~100 | Base class per plugin |
| **html.js** | ~200 | HTML utilities, serialization |
| **selection.js** | ~200 | Selection/range manipulation |
| **range.js** | ~150 | Range object abstraction |

### Plugin disponibili

- **LinkDialog** — Insert link
- **TextColor** — Text/background color picker
- **FontChoice** — Font family/size selector
- **EnterKeyHandling** — Comportamento tasto Enter
- **AlwaysShowToolbar** — Toolbar sempre visibile su scroll
- **ToggleDir** — Toggle direzione testo (LTR/RTL)

---

## 6. Tree (_tree/) — Architettura

| File | Scopo |
|------|-------|
| **dndSource.js** | Drag-drop source mixin |
| **dndContainer.js** | Drop target mixin |
| **dndSelector.js** | Multi-select mixin |
| **model.js** | Tree model interface (usa dojo.data) |
| **Tree.html** | Template nodi tree |
| **Node.html** | Template singolo nodo |

---

## 7. Template System

### Pattern dojoAttachPoint/dojoAttachEvent

```html
<div dojoAttachPoint="containerNode" dojoAttachEvent="onmouseenter:_onMouse">
  <span dojoAttachPoint="labelNode">${label}</span>
</div>
```

- `dojoAttachPoint="name"` -> `this.name = <element>`
- `dojoAttachEvent="event:handler"` -> `this.connect(element, event, handler)`
- `${property}` -> Property substitution (escaped di default)
- `${!property}` -> Unescaped HTML injection

### Template file disponibili

| Template | Widget |
|----------|--------|
| Dialog.html | Dialog |
| Calendar.html | _Calendar |
| ColorPalette.html | ColorPalette |
| ProgressBar.html | ProgressBar |
| TitlePane.html | TitlePane |
| Tooltip.html | Tooltip |
| InlineEditBox.html | InlineEditBox |
| Tree.html, Node.html | Tree |

---

## 8. Themes

### Temi disponibili

| Tema | Stile | Note |
|------|-------|------|
| **tundra** | Blue moderno | Default in Dojo 1.3+ |
| **soria** | Blue professionale | Classic desktop look |
| **nihilo** | Gray minimalista | Light theme |

### Struttura tema tipica

```
themes/soria/
+-- soria.css (main)
+-- form/
|   +-- Common.css, Button.css, TextBox.css, CheckBox.css, ...
+-- layout/
|   +-- BorderContainer.css, TabContainer.css, ...
+-- images/
|   +-- (PNG/GIF per buttons, icons, etc.)
+-- ..._rtl.css (varianti RTL)
```

### Browser Detection CSS Classes

```css
.dj_ie, .dj_ie6, .dj_ie7, .dj_iequirks
.dj_opera, .dj_opera8, .dj_opera9
.dj_gecko, .dj_ff2
.dj_safari, .dj_khtml
```

### Note

- **490 file (57%) sono temi CSS** — candidato principale per consolidamento
- Accessibility via `.dijit_a11y` per high contrast mode
- RTL support via `dijitRtl` class e file `_rtl.css` separati

---

## 9. Localizzazione (nls/)

**16 lingue + default (ROOT):**

ar (Arabo), cs (Ceco), da (Danese), de (Tedesco), el (Greco), es (Spagnolo), fi (Finlandese), fr (Francese), he (Ebraico), hu (Ungherese), it (Italiano), ja (Giapponese), ko (Coreano), nb (Norvegese), nl (Olandese), pl (Polacco), pt/pt-br/pt-pt (Portoghese), ru (Russo), sv (Svedese), tr (Turco), zh/zh-cn/zh-tw (Cinese)

**Stringhe tradotte**: Button labels, date/time formats, error messages, number/currency formats.

---

## 10. Classificazione per Rilevanza

### Probabilmente usato da GenroPy

| Componente | Motivo |
|------------|--------|
| **Form widgets** | TextBox, CheckBox, Button, ComboBox, ValidationTextBox, Slider, DateTextBox |
| **Layout** | BorderContainer, TabContainer, ContentPane |
| **Dialog** | Modal dialogs |
| **Tree** | Strutture gerarchiche |
| **Tooltip** | Inline help |
| **Editor** | Rich-text editing |
| **_base (focus, popup, manager)** | Infrastructure di tutti i widget |

### Da preservare (valore architetturale)

| Componente | Motivo |
|------------|--------|
| **_Widget** | Base di tutti i widget, lifecycle pattern |
| **_Templated** | Template system con dojoAttachPoint binding |
| **_Container** | Parent-child relationship pattern |
| **Widget Registry** | Tracking globale dei widget |
| **Focus Stack** | Gestione focus in widget complessi |
| **Popup System** | z-index, posizionamento, overlay |

### Candidati per modernizzazione

| Componente | Equivalente moderno |
|------------|---------------------|
| Template system (`dojoAttachPoint`) | Web Components, Shadow DOM |
| `dojo.declare()` per widget | ES6 `class` + `customElements.define()` |
| State classes CSS | CSS `:hover`, `:focus`, `:disabled` pseudo-classes |
| Browser sniffing | Feature detection, `@supports` |
| Widget registry | Custom Elements registry nativo |
| Accessibility (WAI) | ARIA attributes nativi |

### Eliminabili/consolidabili

| Componente | Motivo |
|------------|--------|
| **SplitContainer** | Deprecated, usare BorderContainer |
| **Temi non usati** | Tenere solo il tema usato da GenroPy |
| **Browser CSS classes** | dj_ie6, dj_ie7 — browser morti |
| **bench/, demos/** | File di test/demo |

---

## 11. Note Architetturali

### Lifecycle di un widget dijit

```
constructor() -> postMixInProperties() -> buildRendering() ->
postCreate() -> startup() -> ... -> destroy()
```

### Pattern chiave

1. **Mixin composition**: Widget composti da multipli mixin via `dojo.declare()`
2. **Template binding**: HTML template con `dojoAttachPoint` per referenze DOM
3. **Attribute mapping**: `attributeMap` sincronizza proprieta' JS con attributi DOM
4. **State management**: CSS classes per stati (hover, active, focused, disabled, error)
5. **Focus management**: Stack di widget attivi, navigazione keyboard
6. **Popup management**: z-index centralizzato, posizionamento smart

---

## 12. Metriche di Build

| File | Dimensione | Tipo |
|------|-----------|------|
| **dijit.js** | ~500KB | Minified completo |
| **dijit.js.uncompressed.js** | ~2MB | Uncompressed per debug |
| **dijit-all.js** | ~1.5MB | Completo con localization |
| **dijit-all_XX.js** | ~300KB ciascuno | Build per lingua specifica |
