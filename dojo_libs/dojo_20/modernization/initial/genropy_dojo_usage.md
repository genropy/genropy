# GenroPy — Mappa Uso API Dojo e Strategie di Modernizzazione

## Panoramica

Analisi completa dei 24 file JS di GenroPy (`gnrjs/gnr_d11/js/`) per mappare
tutte le dipendenze da Dojo e identificare strategie di modernizzazione.

**Totale**: ~1.100 chiamate a API dojo/dijit/dojox, ~60 API dojo.* distinte.

---

## 1. API Dojo Piu' Usate (Top 20)

| # | API | Occorrenze | Categoria | Sostituzione nativa |
|---|-----|-----------|-----------|---------------------|
| 1 | `dojo.declare` | ~190 | Classi/OOP | `class ... extends` |
| 2 | `dojo.connect` | ~160 | Eventi | `addEventListener` |
| 3 | `dojo.hitch` | ~86 | Binding | Arrow functions / `.bind()` |
| 4 | `dojo.forEach` | ~79 | Array | `Array.prototype.forEach` |
| 5 | `dojo.query` | ~41 | DOM selezione | `querySelectorAll` |
| 6 | `dojo.body` | ~38 | DOM | `document.body` |
| 7 | `dojo.style` | ~37 | DOM styling | `el.style.*` |
| 8 | `dojo.stopEvent` | ~36 | Eventi | `e.preventDefault(); e.stopPropagation()` |
| 9 | `dojo.Deferred` | ~33 | Async | `Promise` / `async/await` |
| 10 | `dojo.indexOf` | ~27 | Array | `Array.prototype.indexOf` |
| 11 | `dojo.addClass` | ~26 | DOM classi | `el.classList.add()` |
| 12 | `dojo.byId` | ~20 | DOM selezione | `document.getElementById` |
| 13 | `dojo.coords` | ~19 | DOM geometry | `getBoundingClientRect()` |
| 14 | `dojo.date` | ~22 | Date/time | `Intl.DateTimeFormat` |
| 15 | `dojo.require` | ~17 | Module loading | ES modules |
| 16 | `dojo.marginBox` | ~16 | DOM geometry | `getBoundingClientRect()` |
| 17 | `dojo.subscribe` | ~13 | Pub/Sub | `EventTarget` custom |
| 18 | `dojo.removeClass` | ~11 | DOM classi | `el.classList.remove()` |
| 19 | `dojo.publish` | ~10 | Pub/Sub | `EventTarget` custom |
| 20 | `dojo.disconnect` | ~5 | Eventi | `removeEventListener` |

---

## 2. API dijit Piu' Usate

| API dijit | Occorrenze | Uso |
|-----------|-----------|-----|
| `dijit.getEnclosingWidget` | 25 | Risale dal DOM al widget — pattern core GenroPy |
| `dijit.Menu` | 10 | Menu contestuali |
| `dijit.byId` | 8 | Registry widget per ID |
| `dijit.byNode` | 6 | Registry widget per nodo DOM |
| `dijit.layout.BorderContainer` | 4 | Layout principale |
| `dijit.form.Button` | 4 | Bottoni |
| `dijit.Tree` | 3 | Albero |
| `dijit.form.*` (vari) | ~20 | Widget form (TextBox, ComboBox, DateTextBox, etc.) |
| `dijit.layout.*` (vari) | ~15 | Layout (TabContainer, StackContainer, etc.) |

Le API dijit **non sono sostituibili** senza riscrivere i widget.

---

## 3. API dojox Usate

| API dojox | Occorrenze | Uso |
|-----------|-----------|-----|
| `dojox.widget.FileInputAuto` | 4 | Upload file |
| `dojox.widget.Toaster` | 3 | Notifiche toast |
| `dojox.grid.*` | ~9 | Patching grid (genro_grid.js) |
| `dojox.layout.FloatingPane` | 2 | Finestre flottanti |
| Vari widget dojox | ~15 | ColorPicker, Gallery, Presentation, etc. |

---

## 4. File GenroPy per Intensita' di Uso Dojo

| File | Chiamate dojo | Ruolo |
|------|--------------|-------|
| `genro_widgets.js` | ~370 | Catalogo widget — il piu' dipendente |
| `genro_patch.js` | ~130 | Patch/override su dijit — intimo con Dojo |
| `genro_components.js` | ~106 | Componenti dichiarativi |
| `genro_grid.js` | ~91 | Wrapper grid dojox |
| `genro.js` | ~87 | Core applicativo |
| `genro_dom.js` | ~61 | Manipolazione DOM |
| `gnrstores.js` | ~40 | Data stores |
| `gnrdomsource.js` | ~39 | DOM source |
| `genro_rpc.js` | ~35 | **Networking — punto chiave** |
| `gnrlang.js` | ~35 | Utility linguaggio |
| `gnrbag.js` | ~32 | Bag — struttura dati core |
| `genro_tree.js` | ~30 | Wrapper tree |
| `genro_frm.js` | ~28 | Form handling |
| `genro_wdg.js` | ~28 | Widget factory |
| `genro_dev.js` | ~25 | Developer tools |
| `genro_extra.js` | ~22 | Widget extra |
| `genro_dlg.js` | ~12 | Dialoghi |
| `genro_mobile.js` | ~41 | Mobile |
| `gnrwebsocket.js` | ~4 | WebSocket |
| `genro_uo.js` | 0 | Nessun uso dojo |

---

## 5. Strategia: Separazione Networking (Priorita' 1)

### Perché il networking è il primo candidato

Il networking e' il confine piu' netto: tutto passa da **un unico metodo**
`_serverCall_execute` in `genro_rpc.js:329-358`.

```javascript
// L'unico punto dove GenroPy tocca dojo.xhr*
_serverCall_execute: function(httpMethod, kw, callKwargs) {
    if (httpMethod == 'GET')    xhrResult = dojo.xhrGet(kw);
    else if (httpMethod == 'POST') {
        if ('postData' in callKwargs) xhrResult = dojo.rawXhrPost(kw);
        else                          xhrResult = dojo.xhrPost(kw);
    }
    else if (httpMethod == 'DELETE') xhrResult = dojo.xhrDelete(kw);
    else if (httpMethod == 'PUT') {
        if ('putData' in callKwargs)  xhrResult = dojo.rawXhrPut(kw);
        else                          xhrResult = dojo.xhrPut(kw);
    }
    return xhrResult;
}
```

### Punti di contatto totali

| Punto | File | Righe | Note |
|-------|------|-------|------|
| `dojo.xhrGet/Post/Put/Delete` | genro_rpc.js | 329-358 | **Unico punto** — `_serverCall_execute` |
| `dojo.rawXhrPost/Put` | genro_rpc.js | 340, 350 | Dentro lo stesso metodo |
| `dojo.io.iframe.send` | genro_widgets.js | 5943, 5998 | Upload legacy (iframe) |
| `dojo.io.argsFromMap` | genro_rpc.js | 655 | Query string builder |
| `instanceof dojo.Deferred` | 7 file | ~30 punti | Check tipo risultato async |
| `.addCallback()` / `.addErrback()` | 7 file | ~20 punti | Chain async |

### Proposta: giojo.rpc layer

Creare in `giojo.js` un layer di networking nativo che:

1. **`giojo.Deferred`** — oggetto con interfaccia compatibile `dojo.Deferred`
   ma basato su `Promise` internamente. Metodi: `addCallback`, `addErrback`,
   `addBoth`, `callback`, `errback`.

2. **`giojo.xhr(method, kw)`** — rimpiazzo di `_serverCall_execute`:
   - Per chiamate **async**: usa `fetch()` API
   - Per chiamate **sync**: usa `XMLHttpRequest` sincrono (stesso meccanismo
     che `dojo.xhrPost({sync:true})` usa internamente)
   - Ritorna `giojo.Deferred`

3. **Alias**: `dojo.Deferred = giojo.Deferred` nello shim, cosi' i ~30
   `instanceof dojo.Deferred` continuano a funzionare senza modifiche.

### Il problema sync

GenroPy usa `sync: true` nei resolver della Bag per ottenere valori immediati.
`fetch()` non supporta sync. Le opzioni:

- **XMLHttpRequest sincrono** come ponte (deprecato ma funzionante — e' esattamente
  quello che Dojo fa gia' sotto il cofano)
- **Refactor verso async/await** — la Bag Python ha gia' un porting che supporta
  async, potrebbe servire da riferimento per il pattern JS

### Impatto minimo

| Modifica | File | Righe da cambiare |
|----------|------|--------------------|
| Nuovo giojo.Deferred + giojo.xhr | giojo.js | ~80 nuove |
| Sostituzione in _serverCall_execute | genro_rpc.js | 6 righe → 1 |
| Rimozione dojo.io.iframe (opzionale) | genro_widgets.js | 2 blocchi |
| dojo.io.argsFromMap → URLSearchParams | genro_rpc.js | 1 riga |

**Zero modifiche** a gnrbag.js, gnrstores.js, genro_frm.js, genro_grid.js
e tutti gli altri file che usano Deferred.

---

## 6. Strategia: Shim Layer Progressivo (Priorita' 2)

Creare in `giojo.js` wrapper nativi per le API dojo piu' usate che hanno
sostituzione 1:1. I chiamanti GenroPy continuano a usare `dojo.*`,
ma internamente il codice Dojo non viene piu' eseguito.

### Sostituzioni a rischio zero

| API Dojo | Implementazione giojo | Note |
|----------|----------------------|------|
| `dojo.byId(id)` | `document.getElementById(id)` | Identico |
| `dojo.body()` | `document.body` | Identico |
| `dojo.doc` | `document` | Identico |
| `dojo.stopEvent(e)` | `e.preventDefault(); e.stopPropagation()` | Identico |
| `dojo.addClass(n, c)` | `n.classList.add(c)` | Identico |
| `dojo.removeClass(n, c)` | `n.classList.remove(c)` | Identico |
| `dojo.hasClass(n, c)` | `n.classList.contains(c)` | Identico |
| `dojo.query(sel)` | `Array.from(document.querySelectorAll(sel))` | Quasi identico |
| `dojo.hitch(scope, fn)` | `fn.bind(scope)` | Identico |
| `dojo.toJson(obj)` | `JSON.stringify(obj)` | Identico |
| `dojo.fromJson(str)` | `JSON.parse(str)` | Piu' sicuro (no eval) |
| `dojo.forEach(arr, fn)` | `Array.prototype.forEach.call(arr, fn)` | Identico |
| `dojo.indexOf(arr, v)` | `Array.prototype.indexOf.call(arr, v)` | Nota: === vs == |
| `dojo.map(arr, fn)` | `Array.prototype.map.call(arr, fn)` | Identico |
| `dojo.filter(arr, fn)` | `Array.prototype.filter.call(arr, fn)` | Identico |
| `dojo.some(arr, fn)` | `Array.prototype.some.call(arr, fn)` | Identico |
| `dojo.trim(str)` | `str.trim()` | Identico |

### Sostituzioni che richiedono attenzione

| API Dojo | Sostituzione | Differenza |
|----------|-------------|------------|
| `dojo.connect` | `addEventListener` | connect funziona anche su oggetti non-DOM |
| `dojo.coords` | `getBoundingClientRect()` | Interfaccia diversa (x,y,w,h vs l,t,w,h) |
| `dojo.marginBox` | `getBoundingClientRect()` | Include margin nel calcolo |
| `dojo.style(n, prop)` | `getComputedStyle(n)[prop]` | Getter diverso |
| `dojo.place` | `insertAdjacentHTML` | Parametri diversi |

### Non sostituibili (richiedono il framework)

| API | Motivo |
|-----|--------|
| `dojo.declare` (~190) | Sistema classi con mixins, `inherited()`, method chaining |
| `dojo.connect` su non-DOM (~60) | Observer pattern su oggetti JS — non e' addEventListener |
| `dojo.Deferred` (~33) | Semantica diversa da Promise (cancel, sync, ioArgs) |
| `dojo.require` (~17) | Module loader — serve finché non si passa a ES modules |
| `dijit.*` (tutto) | Widget framework completo |

---

## 7. Strategia: Eliminazione Codice Morto in Dojo (Priorita' 3)

Interventi a rischio zero sui sorgenti Dojo stessi.

### Eliminabili subito

| Componente | File | Motivo |
|------------|------|--------|
| Google Gears | `_base/window.js` | Progetto chiuso 2010 |
| Adobe AIR | `dojo.js` | Abbandonato |
| Konqueror/KHTML | `dojo.js` | Browser morto |
| `_firebug/` require | `hostenv_browser.js` | File non esistono nel repo |
| `jaxer.js` | root | Server-side JS morto 2010 |
| `OpenAjax.js` | root | Spec defunta |
| `dojo.compressed.js` | root | Artefatto di build |

### Sostituzioni sicure nei sorgenti Dojo

| Cosa | File | Da → A |
|------|------|--------|
| JSON eval | `_base/json.js` | `eval("("+json+")")` → `JSON.parse(json)` |
| `dojo.trim` | `_base/lang.js` | Regex → `str.trim()` |
| Safari 2 branch | `_base/lang.js` | Rimuovere branch `dojo.isSafari` per isFunction |
| `with()` | `bootstrap.js` | `with(d.version)` → destructuring |
| `arguments.callee` | `json.js` | → named function |

---

## 8. Roadmap Suggerita

### Fase 1 — Rischio zero (ora)
- Eliminare codice morto da Dojo (Gears, AIR, KHTML, jaxer, OpenAjax)
- Sostituire `eval()` in json.js con `JSON.parse`
- Arricchire `giojo.js` con shim nativi (byId, body, classList, query, etc.)

### Fase 2 — Separazione networking
- Implementare `giojo.Deferred` (compatibile con dojo.Deferred)
- Implementare `giojo.xhr` (fetch + XHR sync come ponte)
- Sostituire `_serverCall_execute` in genro_rpc.js
- Rimuovere `dojo.io.iframe` da genro_widgets.js

### Fase 3 — Migrazione progressiva GenroPy
- File per file, sostituire `dojo.forEach` → nativo, `dojo.hitch` → bind, etc.
- Investigare porting async della Bag Python come riferimento per eliminare sync
- Valutare migrazione `dojo.connect` su oggetti non-DOM → pattern EventTarget

### Fase 4 — Lungo termine
- Valutare migrazione `dojo.declare` → ES6 class (impatto strutturale)
- Valutare sostituzione widget dijit → Web Components o framework moderno
- Valutare rimozione module loader dojo.require → ES modules

---

## Note

- `genro_uo.js` e' l'unico file senza alcuna dipendenza Dojo
- `genro_widgets.js` e' il file piu' dipendente (~370 chiamate, 54% del totale)
- `genro_patch.js` contiene override diretti su prototipi dijit — ultimo da migrare
- Il pattern `instanceof dojo.Deferred` e' usato in 7 file (~30 punti) — risolvibile
  con alias `dojo.Deferred = giojo.Deferred`
