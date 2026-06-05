# Giojo.js — Piano Generale di Modernizzazione

## Visione

Giojo.js nasce come modulo vuoto incluso nel bootstrap HTML di GenroPy
**accanto** a dojo.js. Cresce progressivamente implementando equivalenti
moderni delle API Dojo usate da GenroPy. Ad ogni migrazione, una parte
di Dojo diventa inutile. Alla fine, Dojo si stacca.

```
Oggi:        [  dojo.js  ████████████████████ ]  +  [giojo.js (vuoto)]
Fase 1:      [  dojo.js  ██████████████████   ]  +  [giojo.js ██     ]
Fase 2:      [  dojo.js  █████████████        ]  +  [giojo.js ███████]
Fase N:      [  dojo.js  ███                  ]  +  [giojo.js ████████████████]
Finale:                                            [giojo.js █████████████████████]
```

Pattern "strangler fig": il nuovo cresce attorno al vecchio.

---

## Principi

1. **Sempre in produzione** — giojo.js e' incluso dal giorno zero, ogni
   modifica e' deployabile
2. **Una funzione alla volta** — ogni migrazione e' atomica e testabile
3. **Nessun big bang** — Dojo e giojo coesistono per tutto il tempo necessario
4. **Progresso misurabile** — conteggio `dojo.*` nel codice GenroPy decresce
5. **Reversibile** — se una sostituzione causa problemi, si torna a `dojo.*`

---

## Fase 0 — Setup (immediato)

### 0.1 Creare giojo.js

File `giojo.js` nella directory Dojo di Giojo, caricato dal bootstrap HTML
di GenroPy subito dopo `dojo.js`.

```javascript
// giojo.js — Modern replacement layer for Dojo APIs
// Loaded alongside dojo.js, grows progressively

var giojo = (function() {
    'use strict';
    var g = {};
    // ... funzioni aggiunte progressivamente
    return g;
})();
```

### 0.2 Includere in GenroPy

Nel template HTML di bootstrap (`gnrapp_page_handler.py` o equivalente),
aggiungere il tag script per giojo.js subito dopo dojo.js:

```html
<script src="/_dojo/11/dojo/dojo/dojo.js" ...></script>
<script src="/_dojo/11/dojo/dojo/giojo.js"></script>  <!-- NUOVO -->
```

### 0.3 Primo contenuto: namespace

```javascript
var giojo = (function() {
    'use strict';
    var g = {};
    g.version = '0.1.0';
    return g;
})();
```

Da questo momento giojo.js e' in produzione e disponibile ovunque.

---

## Fase 0b — Split e documentazione del codice GenroPy JS

Prima di modernizzare, **organizzare e documentare** il codice com'e'.
Puro refactoring strutturale: split dei file grandi in moduli tematici
+ commenti JSDoc. Zero modifiche funzionali.

### Principio

- **Solo split e commenti** — il codice non cambia di una virgola
- **Ogni step e' un commit** — deployabile e reversibile
- **I file originali diventano aggregatori** — includono i sotto-moduli
- **JSDoc su ogni classe e metodo pubblico** — cosa fa, parametri, ritorno
- **Soglia**: ogni sotto-modulo deve stare sotto le **1.000 righe**

### Stato attuale: 45.663 righe in 23 file — 15 file superano le 1.000 righe

I file >1.000 righe hanno confini naturali chiari (classi `dojo.declare`).

| File | Righe | Classi | Split proposto |
|------|-------|--------|----------------|
| `genro_components.js` | 8.075 | 75 classi widget | Per famiglia funzionale |
| `genro_widgets.js` | 6.056 | 57 classi widget | Per tipo (HTML/Dojo/form/layout) |
| `genro_grid.js` | 5.051 | 5 classi | Per classe |
| `genro_frm.js` | 3.328 | 8 classi | Handler / Validator / FormStores |
| `gnrbag.js` | 2.576 | 7 classi | BagNode / Bag / Resolver |
| `genro.js` | 2.493 | 2 classi | GenroClient sezioni logiche |
| `genro_extra.js` | 2.418 | — | Per area funzionale |
| `genro_wdg.js` | 2.324 | 5 classi | WdgHandler / RowEditor / GridEditor / FilterMgr |
| `gnrlang.js` | 2.232 | — | Utility per categoria |
| `gnrdomsource.js` | 2.100 | 3 classi | DomSourceNode / DomSource |
| `genro_dom.js` | 2.080 | 1 classe | GnrDomHandler sezioni logiche |
| `genro_dev.js` | 1.564 | — | Inspector / DevTools per sezione |
| `genro_dlg.js` | 1.444 | 1 classe | GnrDlgHandler per tipo dialog |
| `genro_patch.js` | 1.423 | — | Patch per area funzionale |
| `genro_rpc.js` | 1.046 | 2 classi | Resolver / ServerCall / Utilities |

### Step 0b.1 — `genro_components.js` (8.075 righe → ~8 file)

Il file piu' grande. 75 classi widget, tutte `gnr.widgets.*`.
Split per famiglia funzionale:

| Nuovo file | Classi | Righe circa |
|------------|--------|-------------|
| `genro_cmp_base.js` | `gnrwdg` (classe base) | ~100 |
| `genro_cmp_palette.js` | `Palette`, `PalettePane`, `PaletteGrid`, `PaletteTree`, `PaletteMap`, `PaletteGroup`, `PaletteImporter`, `PaletteBag*Editor` | ~1.200 |
| `genro_cmp_frame.js` | `FramePane`, `FrameForm`, `BoxForm`, `DocumentFrame`, `TreeFrame` | ~600 |
| `genro_cmp_editor.js` | `MultiValueEditor`, `BagNodeEditor`, `BagEditor`, `FlatBagEditor`, `QuickEditor`, `ExtendedCkeditor`, `CodeEditor` | ~800 |
| `genro_cmp_grid.js` | `QuickGrid`, `TreeGrid`, `GridGallery`, `IncludedView` related | ~1.000 |
| `genro_cmp_store.js` | `SelectionStore`, `BagStore`, `_Collection`, `BagRows`, `RpcBase`, `Selection`, `VirtualSelection` | ~1.300 |
| `genro_cmp_form.js` | `SearchBox`, `SlotBar`, `SlotButton`, `UserObject*`, `DropUploader*`, `StackButtons` | ~1.500 |
| `genro_cmp_misc.js` | `TooltipPane`, `MenuDiv`, `Color*`, `Video*`, `ComboArrow`, `Password*`, resto | ~1.500 |

Il file originale `genro_components.js` diventa un aggregatore che
include tutti i sotto-file.

### Step 0b.2 — `genro_widgets.js` (6.056 righe → ~5 file)

57 classi widget. Split per tipo:

| Nuovo file | Classi | Righe circa |
|------------|--------|-------------|
| `genro_wdg_html.js` | `baseHtml`, `htmliframe`, `flexbox`, `gridbox`, `labledbox`, `iframe`, `canvas`, `video`, `baseExternalWidget`, `LightButton`, `uploadable`, `img`, `embed` | ~1.300 |
| `genro_wdg_layout.js` | `baseDojo`, `Dialog`, `StackContainer`, `TabContainer`, `BorderContainer`, `TitlePane`, `FloatingPane`, `ContentPane`, `AccordionPane`, `ResizeHandle` | ~1.500 |
| `genro_wdg_form.js` | `_BaseTextBox`, `TextBox`, `DateTextBox`, `TimeTextBox`, `NumberTextBox`, `CurrencyTextBox`, `Slider*`, `CheckBox`, `RadioButton`, `SimpleTextarea` | ~1.200 |
| `genro_wdg_combo.js` | `BaseCombo`, `FilteringSelect`, `ComboBox`, `DynamicBaseCombo`, `dbBaseCombo`, `LocalBaseCombo`, `RemoteBaseCombo`, `db/Remote/CallBackSelect`, `DropDownButton` | ~1.200 |
| `genro_wdg_menu.js` | `Menu`, `Menuline`, `Tooltip`, `Button`, `_ButtonLogic`, `Calendar`, `ProgressBar`, `Editor`, `ColorPicker`, `ColorPalette`, `fileInput*`, `GoogleMap`, `StaticMap` | ~900 |

### Step 0b.3 — `genro_grid.js` (5.051 righe → 3 file)

| Nuovo file | Classi | Righe circa |
|------------|--------|-------------|
| `genro_grid_base.js` | `DojoGrid` (logica base, celle, eventi) | ~2.200 |
| `genro_grid_virtual.js` | `VirtualGrid`, `VirtualStaticGrid` | ~1.200 |
| `genro_grid_included.js` | `IncludedView`, `NewIncludedView` | ~1.600 |

### Step 0b.4 — `genro_frm.js` (3.328 righe → 3 file)

| Nuovo file | Classi | Righe circa |
|------------|--------|-------------|
| `genro_frm_handler.js` | `GnrFrmHandler` | ~2.100 |
| `genro_frm_validator.js` | `GnrValidator` | ~330 |
| `genro_frm_stores.js` | `formstores.Base`, `.SubForm`, `.Item`, `.Collection`, `.Hierarchical` | ~900 |

### Step 0b.5 — `gnrbag.js` (2.576 righe → 3 file)

| Nuovo file | Classi | Righe circa |
|------------|--------|-------------|
| `gnrbag_node.js` | `GnrBagNode` | ~530 |
| `gnrbag_bag.js` | `GnrBag` | ~1.750 |
| `gnrbag_resolver.js` | `GnrBagResolver`, `GnrBagFormula`, `GnrBagGetter`, `GnrBagCbResolver` | ~300 |

### Step 0b.6 — `genro_wdg.js` (2.324 righe → 4 file)

| Nuovo file | Classi | Righe circa |
|------------|--------|-------------|
| `genro_wdg_handler.js` | `GnrWdgHandler` | ~550 |
| `genro_wdg_row_editor.js` | `RowEditor` | ~160 |
| `genro_wdg_grid_editor.js` | `GridEditor` | ~1.100 |
| `genro_wdg_grid_mgr.js` | `GridFilterManager`, `GridChangeManager` | ~400 |

### Step 0b.7 — `gnrlang.js` (2.232 righe → per categorie)

Non ha classi `dojo.declare`, sono funzioni globali. Split per categoria:

| Nuovo file | Contenuto |
|------------|-----------|
| `gnrlang_string.js` | Manipolazione stringhe |
| `gnrlang_object.js` | objectUpdate, objectExtract, objectPop, etc. |
| `gnrlang_format.js` | Formattazione, conversione tipi |
| `gnrlang_misc.js` | Utility varie |

### Step 0b.8 — `gnrdomsource.js`, `genro_dom.js`, `genro.js`

| File | Split |
|------|-------|
| `gnrdomsource.js` (2.100) | `gnrdomsource_node.js` + `gnrdomsource_bag.js` |
| `genro_dom.js` (2.080) | Per sezione logica del `GnrDomHandler` |
| `genro.js` (2.493) | `GenroClient` per aree (init, data, navigation, misc) |

### Step 0b.9 — `genro_dev.js` (1.564 righe → 2 file)

| Nuovo file | Contenuto | Righe circa |
|------------|-----------|-------------|
| `genro_dev_inspector.js` | Inspector DOM, tree viewer, debug panels | ~800 |
| `genro_dev_tools.js` | Utility sviluppo, logging, diagnostica | ~750 |

### Step 0b.10 — `genro_dlg.js` (1.444 righe → 2 file)

| Nuovo file | Contenuto | Righe circa |
|------------|-----------|-------------|
| `genro_dlg_base.js` | `GnrDlgHandler`, dialog standard, confirm, alert | ~750 |
| `genro_dlg_advanced.js` | Dialog specializzati (file picker, color, form dialog) | ~700 |

### Step 0b.11 — `genro_patch.js` (1.423 righe → 2 file)

| Nuovo file | Contenuto | Righe circa |
|------------|-----------|-------------|
| `genro_patch_widgets.js` | Patch su widget dijit/dojox | ~750 |
| `genro_patch_core.js` | Patch su comportamenti core | ~670 |

### Step 0b.12 — `genro_rpc.js` (1.046 righe → 2 file)

| Nuovo file | Contenuto | Righe circa |
|------------|-----------|-------------|
| `genro_rpc_resolver.js` | `GnrRemoteResolver`, resolver relazionali | ~500 |
| `genro_rpc_call.js` | `_serverCall`, `_serverCall_execute`, utilities RPC | ~550 |

### Meccanismo di aggregazione

Il file originale resta come aggregatore. Esempio per `gnrbag.js`:

```javascript
// gnrbag.js — Aggregator (original file preserved for compatibility)
// Actual code split into:
//   gnrbag_node.js     — GnrBagNode class
//   gnrbag_bag.js      — GnrBag class
//   gnrbag_resolver.js — GnrBagResolver and subclasses

// The script tags for sub-modules are added in the GenroPy bootstrap.
// This file is kept empty for backward compatibility with any direct references.
```

In alternativa, se il loading order e' gestito dal bootstrap HTML di GenroPy,
i nuovi file vengono aggiunti direttamente li' e il file originale viene
svuotato progressivamente.

### Commenti JSDoc

Ogni classe e metodo pubblico riceve un commento JSDoc:

```javascript
/**
 * GnrBagNode — Nodo singolo nella gerarchia Bag.
 *
 * Contiene label, value, attributi e opzionalmente un resolver
 * per il lazy loading. Il valore puo' essere scalare o un'altra
 * GnrBag per creare strutture gerarchiche.
 *
 * @class gnr.GnrBagNode
 * @param {GnrBag} parentbag - Bag contenitore
 * @param {string} label - Nome/etichetta del nodo
 * @param {*} value - Valore (scalare o GnrBag)
 * @param {Object} attr - Attributi del nodo
 * @param {GnrBagResolver} resolver - Resolver per lazy loading
 */
dojo.declare("gnr.GnrBagNode", null, {

    /**
     * Ritorna il valore del nodo, risolvendo il resolver se necessario.
     *
     * Se il nodo ha un resolver e il cache e' scaduto, chiama
     * resolver.resolve() che puo' fare una chiamata al server.
     *
     * @param {string} mode - 'static' per valore cached, 'reload' per forzare
     * @param {Object} optkwargs - Parametri extra per il resolver
     * @returns {*} Il valore del nodo
     */
    getValue: function(mode, optkwargs) {
```

### Ordine di esecuzione

```
Step 0b.1:  genro_components.js  → 8 file    (8.075 righe, 75 classi)
Step 0b.2:  genro_widgets.js     → 5 file    (6.056 righe, 57 classi)
Step 0b.3:  genro_grid.js        → 3 file    (5.051 righe, 5 classi)
Step 0b.4:  genro_frm.js         → 3 file    (3.328 righe, 8 classi)
Step 0b.5:  gnrbag.js            → 3 file    (2.576 righe, 7 classi)
Step 0b.6:  genro_wdg.js         → 4 file    (2.324 righe, 5 classi)
Step 0b.7:  gnrlang.js           → 4 file    (2.232 righe, utility)
Step 0b.8:  gnrdomsource/dom/genro → split   (6.673 righe, 3 file)
Step 0b.9:  genro_dev.js         → 2 file    (1.564 righe)
Step 0b.10: genro_dlg.js         → 2 file    (1.444 righe)
Step 0b.11: genro_patch.js       → 2 file    (1.423 righe)
Step 0b.12: genro_rpc.js         → 2 file    (1.046 righe)
```

**Totale**: 15 file >1.000 righe → ~50 sotto-moduli, tutti <1.000 righe.

Ogni step e' un commit separato. Il file originale resta come aggregatore.
Nessuna modifica funzionale. Solo split e commenti.

---

## Fase 1 — API DOM e utility a rischio zero

Implementare in giojo.js gli equivalenti nativi delle API Dojo piu'
semplici, poi migrare il codice GenroPy da `dojo.*` a `giojo.*`.

### 1.1 Utility base (109 occorrenze)

| Da (Dojo) | A (giojo) | Implementazione |
|-----------|-----------|-----------------|
| `dojo.byId(id)` | `giojo.byId(id)` | `document.getElementById(id)` |
| `dojo.body()` | `giojo.body()` | `document.body` |
| `dojo.doc` | `giojo.doc` | `document` |
| `dojo.stopEvent(e)` | `giojo.stopEvent(e)` | `e.preventDefault(); e.stopPropagation()` |
| `dojo.toJson(obj)` | `giojo.toJson(obj)` | `JSON.stringify(obj)` |
| `dojo.fromJson(str)` | `giojo.fromJson(str)` | `JSON.parse(str)` |
| `dojo.trim(str)` | `giojo.trim(str)` | `str.trim()` |

**Bonus sicurezza**: `dojo.fromJson` usa `eval()`. `JSON.parse` no.

### 1.2 Classi CSS (45 occorrenze)

| Da (Dojo) | A (giojo) | Implementazione |
|-----------|-----------|-----------------|
| `dojo.addClass(n, c)` | `giojo.addClass(n, c)` | `n.classList.add(c)` |
| `dojo.removeClass(n, c)` | `giojo.removeClass(n, c)` | `n.classList.remove(c)` |
| `dojo.hasClass(n, c)` | `giojo.hasClass(n, c)` | `n.classList.contains(c)` |
| `dojo.toggleClass(n, c)` | `giojo.toggleClass(n, c)` | `n.classList.toggle(c)` |

Gestire il caso classi multiple (spazi): `dojo.addClass(n, 'a b')`
→ split e `classList.add('a', 'b')`.

### 1.3 Array methods (121 occorrenze)

| Da (Dojo) | A (giojo) | Implementazione |
|-----------|-----------|-----------------|
| `dojo.forEach(arr, fn)` | `giojo.forEach(arr, fn)` | `Array.prototype.forEach.call(arr, fn)` |
| `dojo.map(arr, fn)` | `giojo.map(arr, fn)` | `Array.prototype.map.call(arr, fn)` |
| `dojo.filter(arr, fn)` | `giojo.filter(arr, fn)` | `Array.prototype.filter.call(arr, fn)` |
| `dojo.indexOf(arr, v)` | `giojo.indexOf(arr, v)` | `Array.prototype.indexOf.call(arr, v)` |
| `dojo.some(arr, fn)` | `giojo.some(arr, fn)` | `Array.prototype.some.call(arr, fn)` |

Nota: si usa `Array.prototype.X.call(arr, fn)` e non `arr.X(fn)` per
gestire array-like (NodeList, arguments) come fa Dojo.

### 1.4 Binding (96 occorrenze)

| Da (Dojo) | A (giojo) | Implementazione |
|-----------|-----------|-----------------|
| `dojo.hitch(scope, fn)` | `giojo.hitch(scope, fn)` | `fn.bind(scope)` |
| `dojo.hitch(scope, 'name')` | `giojo.hitch(scope, 'name')` | `scope[name].bind(scope)` |

`dojo.hitch` accetta anche una stringa come secondo argomento.

### 1.5 Query DOM (41 occorrenze)

| Da (Dojo) | A (giojo) | Implementazione |
|-----------|-----------|-----------------|
| `dojo.query(sel)` | `giojo.query(sel)` | `Array.from(document.querySelectorAll(sel))` |
| `dojo.query(sel, root)` | `giojo.query(sel, root)` | `Array.from(root.querySelectorAll(sel))` |

Ritorna un Array (non NodeList dojo). Se serve `.forEach` funziona
perche' Array ha tutti i metodi.

### Totale Fase 1: ~412 occorrenze migrabili

---

## Fase 2 — Networking

Sostituire `dojo.xhr*` con `fetch()`. Tutto async.

### 2.1 `giojo.rpc.call()` — il layer fetch

```javascript
giojo.rpc = {
    async call(url, kwargs, options) {
        var response = await fetch(url, {
            method: options.httpMethod || 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: giojo.rpc.serializeParams(kwargs),
            signal: options.signal  // per AbortController
        });
        return giojo.rpc.parseResponse(response, options.handleAs);
    },

    serializeParams(params) {
        return new URLSearchParams(params).toString();
    },

    async parseResponse(response, handleAs) {
        if (handleAs === 'xml') {
            var text = await response.text();
            return new DOMParser().parseFromString(text, 'text/xml');
        }
        if (handleAs === 'json') return response.json();
        return response.text();
    }
};
```

### 2.2 Migrazione `_serverCall_execute`

Unico punto di contatto con `dojo.xhr*` in `genro_rpc.js:329-358`.

```javascript
// PRIMA (6 branch dojo.xhr*)
_serverCall_execute: function(httpMethod, kw, callKwargs) {
    if (httpMethod == 'GET') xhrResult = dojo.xhrGet(kw);
    else if (httpMethod == 'POST') ...
}

// DOPO (1 riga)
_serverCall_execute: async function(httpMethod, kw, callKwargs) {
    return giojo.rpc.call(kw.url, kw.content, {
        httpMethod: httpMethod,
        handleAs: kw.handleAs
    });
}
```

### 2.3 Rimozione `dojo.io.argsFromMap`

1 occorrenza in `genro_rpc.js:655` → `URLSearchParams`.

### 2.4 Rimozione `dojo.io.iframe.send`

2 occorrenze in `genro_widgets.js` (upload legacy) → `FormData` + `fetch`.

### Moduli Dojo eliminabili dopo Fase 2

| Modulo | Righe |
|--------|-------|
| `_base/xhr.js` | 730 |
| `_base/json.js` | 137 |
| `io/iframe.js` | ~200 |
| `io/script.js` | ~100 |

---

## Fase 3 — Async: Deferred → Promise/await

### 3.1 WebSocket (2 punti)

`gnrwebsocket.js`: `new dojo.Deferred()` → `new Promise()`.

### 3.2 Pattern instanceof (31 punti in 9 file)

Ogni `instanceof dojo.Deferred` + `addCallback` → `await`.
Trasformazione meccanica, stesso pattern ovunque.

File per impatto:
1. `genro_frm.js` — 13 punti
2. `gnrbag.js` — 10 punti
3. `gnrstores.js` — 7 punti
4. `genro_grid.js` — 2 punti
5. `genro_components.js` — 2 punti
6. altri — 1 punto ciascuno

### 3.3 Resolver async

`GnrRemoteResolver.load()` diventa `async`, usa `giojo.rpc.call()`
invece di `genro.rpc._serverCall`. Rimuovere `sync:true` da:
- `remoteResolver()` (riga 635)
- `remote_relOneResolver()` (riga 803)
- `remote_relManyResolver()` (riga 892)

### Moduli Dojo eliminabili dopo Fase 3

| Modulo | Righe |
|--------|-------|
| `_base/Deferred.js` | 408 |
| `DeferredList.js` | ~80 |

---

## Fase 4 — DOM manipulation e stili

Sostituzioni che richiedono attenzione (non meccaniche).

### 4.1 `dojo.style` (37 occorrenze)

```javascript
// giojo.style — getter e setter
giojo.style = function(node, prop, value) {
    if (value !== undefined) {
        node.style[prop] = value;
    } else if (typeof prop === 'object') {
        Object.assign(node.style, prop);
    } else {
        return getComputedStyle(node)[prop];
    }
};
```

### 4.2 `dojo.coords` / `dojo.marginBox` (35 occorrenze)

```javascript
giojo.coords = function(node) {
    var r = node.getBoundingClientRect();
    return {x: r.left, y: r.top, w: r.width, h: r.height,
            l: r.left, t: r.top};
};
```

Mappare le proprieta' al formato atteso dal codice GenroPy.

### 4.3 `dojo.place` (parte delle occorrenze DOM)

```javascript
giojo.place = function(content, refNode, position) {
    // position: 'before', 'after', 'first', 'last', 'only', 'replace'
    // ...
};
```

---

## Fase 5 — Eventi: connect/disconnect

**196 occorrenze** in 15 file. La piu' complessa perche' `dojo.connect`
funziona sia su DOM che su oggetti JS.

### 5.1 Connect su DOM → addEventListener

```javascript
// PRIMA
dojo.connect(node, 'onclick', this, 'handler');

// DOPO
node.addEventListener('click', this.handler.bind(this));
```

### 5.2 Connect su oggetti non-DOM → pattern custom

Per il connect su oggetti (observer pattern), serve un mini-sistema:

```javascript
giojo.connect = function(obj, event, scope, method) {
    if (obj.addEventListener) {
        // DOM
        var eventName = event.replace(/^on/, '');
        var handler = typeof method === 'string'
            ? scope[method].bind(scope)
            : method.bind(scope);
        obj.addEventListener(eventName, handler);
        return {remove: () => obj.removeEventListener(eventName, handler)};
    } else {
        // Non-DOM: wrapper
        // ...
    }
};
```

### 5.3 Subscribe/Publish → EventTarget o custom

```javascript
// Pub/Sub con EventTarget
giojo.bus = new EventTarget();

giojo.subscribe = function(topic, callback) {
    giojo.bus.addEventListener(topic, e => callback(e.detail));
};

giojo.publish = function(topic, data) {
    giojo.bus.dispatchEvent(new CustomEvent(topic, {detail: data}));
};
```

---

## Fase 6 — Lungo termine

### 6.1 `dojo.declare` → ES6 class

**~190 occorrenze**. Impatto strutturale massimo.

`dojo.declare` supporta:
- Ereditarieta' multipla (mixins)
- `this.inherited(arguments)` per chiamare il metodo padre
- Method resolution order (MRO)

Non sostituibile con un semplice `class extends`. Opzioni:
- Riscrittura progressiva classe per classe
- Shim `giojo.declare` che usa `class` internamente
- Mantenere `dojo.declare` come ultima dipendenza

### 6.2 Widget dijit → alternative moderne

Ultima fase, la piu' impattante. Richiede decisioni architetturali
sul framework UI target (Web Components, React, etc.).
Fuori scope per ora.

---

## Metriche di Progresso

### Conteggio corrente dipendenze Dojo nel codice GenroPy JS

| API | Occorrenze | Eliminabile in |
|-----|-----------|----------------|
| `dojo.declare` | ~190 | Fase 6 |
| `dojo.connect` | ~160 | Fase 5 |
| `dojo.forEach/map/filter/indexOf/some` | 121 | Fase 1 |
| `dojo.hitch` | 96 | Fase 1 |
| `dojo.style/attr/coords/marginBox/place` | 78 | Fase 4 |
| `dojo.subscribe/publish` | ~23 | Fase 5 |
| `dojo.byId/body/doc/stopEvent/toJson/fromJson/trim` | 109 | Fase 1 |
| `dojo.query` | 41 | Fase 1 |
| `dojo.addClass/removeClass/hasClass` | 45 | Fase 1 |
| `dojo.xhr*` | ~10 | Fase 2 |
| `dojo.Deferred` (instanceof + API) | ~70 | Fase 3 |
| `dijit.*` | ~100+ | Fase 6 |
| **Totale `dojo.*`** | **~1.043** | |

### Target per fase

| Dopo fase | `dojo.*` rimanenti | Riduzione |
|-----------|-------------------|-----------|
| Fase 0 | ~1.043 | — |
| Fase 1 | ~631 | -412 (-40%) |
| Fase 2 | ~621 | -10 |
| Fase 3 | ~551 | -70 |
| Fase 4 | ~473 | -78 |
| Fase 5 | ~290 | -183 |
| Fase 6 | 0 | -290 |

---

## Flusso Operativo per Ogni Migrazione

```
1. Implementa giojo.X() in giojo.js
2. Testa isolatamente (browser console, unit test)
3. Nel codice GenroPy: dojo.X() → giojo.X()
4. Testa in applicazione reale
5. Commit e deploy
6. Il modulo dojo corrispondente e' un po' piu' inutile
```

Ogni step e' un commit deployabile. Se qualcosa non va, revert del
singolo commit.

---

## File di Riferimento

| Documento | Contenuto |
|-----------|-----------|
| [source_map.md](initial/source_map.md) | Mappa completa sorgenti Dojo |
| [dojo_core_analysis.md](initial/dojo_core_analysis.md) | Analisi moduli _base/ |
| [genropy_dojo_usage.md](initial/genropy_dojo_usage.md) | Mapping API Dojo usate da GenroPy |
| [async_migration_plan.md](async_migration_plan.md) | Piano Deferred → async/await |
| [zero_risk_changes.md](zero_risk_changes.md) | Catalogo modifiche a rischio zero |
| [grid_features.md](initial/grid_features.md) | Catalogo feature dojox.grid |
| [tree_features.md](initial/tree_features.md) | Catalogo feature dijit.Tree |
