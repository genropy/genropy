# Giojo.js — Report Analisi src/dojo/

## Contesto

Giojo.js e' un fork di Dojo Toolkit 1.1.2 (2008). Questa analisi mappa in dettaglio tutti i contenuti di `src/dojo/` come primo passo verso la modernizzazione.

---

## Panoramica Generale

- **172 file** totali in `src/dojo/`
- **~17 MB** di codice sorgente (inclusi dati CLDR/NLS e build compilati)
- Nessuna customizzazione GenroPy rilevata nei sorgenti dojo — codice Dojo standard

---

## 1. Core (_base/) — 15 moduli, ~6.550 righe

Il nucleo del framework. Ogni modulo espone API su `dojo.*`.

### Grafo dipendenze

```
lang.js (base puro, nessuna dipendenza)
 +-- array.js
 +-- declare.js
 +-- connect.js
 |    +-- event.js
 +-- Deferred.js
 +-- json.js
 +-- Color.js (+ array)
 +-- html.js
 +-- window.js (base puro)
 +-- NodeList.js (+ array)
 |    +-- query.js
 +-- xhr.js (+ Deferred, json, query)
 +-- fx.js (+ Color, connect, declare, html)

browser.js (aggregatore che richiede tutti i moduli browser)
```

### Dettaglio moduli

| Modulo | Righe | Scopo | API principali | Equivalente moderno |
|--------|-------|-------|----------------|---------------------|
| **lang.js** | 257 | Type checking, binding, cloning | `isString/Array/Function`, `hitch`, `delegate`, `clone`, `trim` | `typeof`, `.bind()`, `Object.create()`, `structuredClone()`, `.trim()` |
| **array.js** | 182 | Polyfill metodi array ES5 | `indexOf`, `forEach`, `map`, `filter`, `reduce` | `Array.prototype.*` nativi |
| **declare.js** | 178 | Sistema classi OOP con mixins | `dojo.declare()` | ES6 `class` + composition |
| **Deferred.js** | 408 | Promise-like (ispirato a Twisted) | `callback`, `errback`, `addCallback`, `cancel` | `Promise`, `async/await` |
| **connect.js** | 285 | Observer pattern per eventi | `connect`, `disconnect` | `addEventListener/removeEventListener` |
| **event.js** | 529 | Normalizzazione eventi DOM cross-browser | `fixEvent`, `stopEvent`, `preventDefault` | Eventi DOM standardizzati |
| **html.js** | 1.227 | Manipolazione DOM e CSS (il piu' grande) | `byId`, `addClass/removeClass/toggleClass`, `setStyle/getStyle`, positioning | `classList`, `getComputedStyle()`, `element.style` |
| **query.js** | 1.178 | CSS3 selector engine | `dojo.query()` | `querySelectorAll()` |
| **NodeList.js** | 532 | Array-like wrapper per nodi DOM | chaining: `filter`, `map`, `addClass`, `style` | `[...querySelectorAll()]` |
| **xhr.js** | 730 | AJAX HTTP requests | `xhrGet/Post/Put/Delete`, `formToObject` | `fetch()`, `FormData`, `URLSearchParams` |
| **json.js** | 137 | JSON parse/serialize (usa eval!) | `fromJson`, `toJson` | `JSON.parse/stringify` |
| **Color.js** | 156 | Manipolazione colori RGB/RGBA | `Color()`, `toRgb`, `toHex` | CSS Color Module, librerie dedicate |
| **fx.js** | 584 | Framework animazioni | `_Animation`, `play/pause/stop`, easing curves | CSS Transitions/Animations, `requestAnimationFrame` |
| **window.js** | 145 | Alias globali + Google Gears detection | `dojo.doc`, `dojo.body()`, `dojo.global` | `document`, `document.body`, `window` |
| **browser.js** | 21 | Aggregatore loader browser | (nessuna API diretta) | ES6 imports |

---

## 2. File Root — 20 file JS

| File | Righe | Scopo | Rilevanza |
|------|-------|-------|-----------|
| **dojo.js** | ~11.000 | Bootstrap principale + module loader (`require/provide`) | Core ma obsoleto |
| **_base.js** | 13 | Aggregatore dei moduli _base | Meta-file |
| **string.js** | 84 | Pad, substitute (template `${key}`), trim | Media — template literals ES6 |
| **number.js** | 552 | Formattazione numeri con CLDR locale | Media — `Intl.NumberFormat` |
| **currency.js** | ~80 | Formattazione valute localizzate | Media — `Intl.NumberFormat` con currency |
| **date.js** | 343 | Manipolazione date (add, diff, compare) | Media — `Intl.DateTimeFormat`, date-fns |
| **cookie.js** | 95 | Get/set cookie | Media — Cookie API |
| **colors.js** | 225 | Colori CSS3 + conversioni HSL/RGB | Bassa |
| **fx.js** | ~100 | Effects: combine, chain, Toggler | Bassa — CSS animations |
| **NodeList-fx.js** | ~80 | Animazioni su NodeList (fadeIn, wipeIn, slideTo) | Bassa |
| **parser.js** | ~100+ | Parser DOM per widget dichiarative (`dojoType`) | Bassa — Web Components |
| **i18n.js** | ~100+ | Caricamento bundle risorse localizzate | Media — i18next, Intl API |
| **back.js** | ~80 | Browser history management (hash-based) | Bassa — History API |
| **behavior.js** | ~80 | Bind eventi a DOM via CSS selectors | Bassa |
| **regexp.js** | 69 | Utility costruzione RegExp dinamiche | Media |
| **DeferredList.js** | ~80 | Aggregatore Deferred multipli | Bassa — `Promise.all/race/allSettled` |
| **AdapterRegistry.js** | 99 | Registry pattern per dispatch contestuale | Bassa |
| **OpenAjax.js** | ~80 | Pub/Sub hub (spec OpenAjax Alliance, defunta) | Bassa |
| **jaxer.js** | 15 | Integration Jaxer (server-side JS, morto 2010) | Nulla — eliminabile |
| **dojo.compressed.js** | — | Build minificato | Artefatto di build |

---

## 3. Sottodirectory

### data/ (2 file, ~1.570 righe) — Data Store API

| File | Righe | Contenuto |
|------|-------|-----------|
| **ItemFileReadStore.js** | 766 | Store read-only: `getValue`, `getValues`, `fetch`, `getIdentity`. Supporta JSON con `_reference` e `typeMap`. |
| **ItemFileWriteStore.js** | 805 | Estende ReadStore: `newItem`, `deleteItem`, `setValue`, `save`, `revert`, `isDirty`. Tracking pending changes. |

Pattern fondamentale per data binding in Dojo/dijit. Obsoleto ma architetturalmente interessante.

### dnd/ (11 file, ~150 KB) — Drag and Drop

| File | Scopo |
|------|-------|
| **Manager.js** | Singleton globale gestione stato DnD |
| **Source.js** | Sorgente draggable |
| **Container.js** | Container base, hover tracking |
| **Selector.js** | Selezione elementi |
| **Moveable.js** | Spostamento singolo elemento |
| **TimedMoveable.js** | Spostamento con delay |
| **Mover.js** | Handler drag basso livello |
| **Avatar.js** | Feedback visuale durante drag |
| **move.js** | Animazione spostamento |
| **autoscroll.js** | Auto-scroll durante drag |
| **common.js** | Utility (`getCopyKeyState`, `getUniqueId`) |

Implementazione completa ma senza touch support. Architettura: Container -> Source -> Manager.

### cldr/ (56 file, ~400 KB) — Dati Localizzazione CLDR

Dati per 20+ lingue: separatori numerici, formati data, simboli valuta.
Struttura: `cldr/nls/{locale}/number.js`, `gregorian.js`, etc.
Lingue: en, de, it, fr, es, pt-br, ja, zh-cn, zh-tw, ko-kr, e altre.

Sostituibile con `Intl` API nativa del browser.

### nls/ (24 file, ~200 KB) — Stringhe Localizzate

Stringhe UI traducibili. File root: `colors.js` (nomi colori CSS). Pattern NLS di Dojo con fallback locale.

### date/ (2 file, ~40 KB)

| File | Scopo |
|------|-------|
| **stamp.js** | Conversione ISO 8601 <-> Date (`fromISOString`, `toISOString`) |
| **locale.js** | Formattazione date locale-aware |

`stamp.js` ancora rilevante (ISO 8601 e' standard web).

### io/ (2 file, ~60 KB) — Transport Legacy

| File | Scopo |
|------|-------|
| **iframe.js** | Form submission via iframe nascosto (file upload pre-FormData) |
| **script.js** | JSONP script injection (cross-domain pre-CORS) |

Obsoleti: rimpiazzati da `FormData`, CORS, `fetch()`.

### rpc/ (3 file, ~80 KB) — Remote Procedure Call

| File | Scopo |
|------|-------|
| **RpcService.js** | Base class, parsing SMD (Service Mapping Description) |
| **JsonService.js** | JSON-RPC |
| **JsonpService.js** | JSON-RPC via JSONP cross-domain |

Obsoleto: rimpiazzato da REST API + fetch/axios.

### _firebug/ (7 file, ~30 KB) — Console Debug Embedded

Console visuale per browser senza developer tools. Completamente obsoleto.

### resources/ (13 file, ~15 KB) — Asset Statici

CSS core (`dojo.css`), CSS DnD (`dnd.css`), `blank.html` per iframe, `blank.gif` spacer.

---

## 4. Classificazione per Rilevanza

### Eliminabili subito (codice morto)

| Componente | Motivo |
|------------|--------|
| `_firebug/` | Browser moderni hanno DevTools |
| `jaxer.js` | Jaxer morto dal 2010 |
| `OpenAjax.js` | Spec defunta |
| `dojo.compressed.js` | Artefatto di build |
| `back.js` | History API nativa |
| `io/iframe.js` | FormData API |
| `io/script.js` | CORS + fetch |
| `rpc/` (3 file) | REST API standard |
| Google Gears detection in `window.js` | Gears chiuso 2010 |

### Sostituibili con API native (medio termine)

| Componente | Sostituzione nativa |
|------------|---------------------|
| `json.js` (usa `eval()`!) | `JSON.parse/stringify` |
| `array.js` | `Array.prototype.*` |
| `Deferred.js` + `DeferredList.js` | `Promise`, `async/await` |
| `connect.js` + `event.js` | `addEventListener` |
| `query.js` + `NodeList.js` | `querySelectorAll` |
| `xhr.js` | `fetch()` API |
| `cldr/` + `number.js` + `currency.js` | `Intl.NumberFormat` |
| `fx.js` + `NodeList-fx.js` | CSS Transitions/Animations |

### Da preservare/adattare (valore architetturale)

| Componente | Motivo |
|------------|--------|
| `declare.js` | Usato massivamente in dijit/dojox per ereditarieta' |
| `lang.js` | Utility core (`hitch`, `clone`, `delegate`) usate ovunque |
| `html.js` | DOM manipulation usata in tutti i widget |
| `data/` (stores) | Pattern data binding per dijit |
| `dnd/` | DnD framework completo, usato da GenroPy |
| `parser.js` | Parsing dichiarativo dei widget |
| `date/stamp.js` | ISO 8601, standard |
| `i18n.js` | Framework localizzazione per dijit |

---

## 5. Note di Sicurezza

- **`json.js` usa `eval()` per parsing JSON** — rischio XSS. Da sostituire con `JSON.parse()` come priorita'.
- Cookie handling senza flag `Secure`/`HttpOnly`/`SameSite` di default.

---

## 6. Prossimi Passi Suggeriti

1. **Cross-reference con GenroPy** — identificare quali moduli dojo sono effettivamente importati/usati dal codice Python/JS di GenroPy
2. **Analisi dijit/** — i widget UI sono il cuore dell'uso GenroPy
3. **Analisi dojox/** — identificare i moduli estesi usati (grid, charting, gfx)
4. **Mappa delle dipendenze GenroPy -> dojo** — per capire il perimetro reale da modernizzare
