# Modifiche a Rischio Zero — Codice GenroPy JS

## Principio

Queste sono modifiche al codice JS di GenroPy (`gnrjs/gnr_d11/js/`) che:
- Funzionano identicamente in tutti i browser moderni
- Non toccano Dojo/dijit/dojox
- Non cambiano semantica
- Possono andare in produzione subito

---

## Tier 1 — Sostituzione meccanica, zero rischio

### 1.1 `var` → `let` / `const`

| Dato | Valore |
|------|--------|
| Occorrenze `var` | **~5.800** (23 file) |
| Gia' usati `let`/`const` | **~940** (20 file — il codice li usa gia') |

Il codice GenroPy **usa gia'** `let` e `const` in molti punti, quindi
la codebase e' gia' compatibile con ES6. La migrazione e' meccanica:

```javascript
// PRIMA
var result = this.getValue();
var items = [];

// DOPO
const result = this.getValue();
let items = [];
```

**Regola**: `const` se non viene riassegnato, `let` se viene riassegnato.

**Strategia**: file per file, quando si tocca per altri motivi.
Non fare un commit unico da 5.800 righe.

### 1.2 `dojo.forEach` → `Array.forEach` nativo

**121 occorrenze** in 14 file.

```javascript
// PRIMA
dojo.forEach(items, function(item) { ... });

// DOPO
items.forEach(function(item) { ... });
// oppure
items.forEach(item => { ... });
```

Identico al 100%. `Array.prototype.forEach` e' nativo da ES5 (2009).

### 1.3 `dojo.indexOf` → `Array.indexOf` / `includes`

Parte delle 121 occorrenze sopra (dojo.indexOf e' nel conteggio).

```javascript
// PRIMA
dojo.indexOf(arr, value)

// DOPO
arr.indexOf(value)
```

### 1.4 `dojo.map` / `dojo.filter` / `dojo.some` → nativi

Parte delle 121 occorrenze sopra.

```javascript
// PRIMA                          // DOPO
dojo.map(arr, fn)                 arr.map(fn)
dojo.filter(arr, fn)              arr.filter(fn)
dojo.some(arr, fn)                arr.some(fn)
```

### 1.5 `dojo.hitch(this, fn)` → arrow function o `.bind()`

**96 occorrenze** in 15 file.

```javascript
// PRIMA
dojo.hitch(this, function(result) { this.handle(result); })
dojo.hitch(this, 'methodName')

// DOPO — arrow function (preferito)
(result) => { this.handle(result); }

// DOPO — bind (quando si passa un nome metodo)
this.methodName.bind(this)
```

**Nota**: `dojo.hitch(this, 'methodName')` accetta una stringa.
Arrow function e' preferibile ma `.bind()` e' il mapping diretto.

### 1.6 `.indexOf() != -1` → `.includes()`

**110 occorrenze** in 14 file.

```javascript
// PRIMA
if (str.indexOf('something') != -1) { ... }
if (str.indexOf('something') >= 0) { ... }

// DOPO
if (str.includes('something')) { ... }
```

Funziona su String e Array. Nativo da ES2016.

### 1.7 String concatenation → template literals

**~500+ occorrenze** (stima parziale, 45 trovate con pattern semplice).

```javascript
// PRIMA
var msg = 'Error in ' + method + ': ' + error;

// DOPO
const msg = `Error in ${method}: ${error}`;
```

**Strategia**: convertire quando si tocca il file, non in blocco.

### 1.8 `typeof x === 'undefined'` → confronto diretto

**7 occorrenze** in 4 file.

```javascript
// PRIMA
if (typeof x === 'undefined') { ... }
if (typeof x !== 'undefined') { ... }

// DOPO
if (x === undefined) { ... }
if (x !== undefined) { ... }
```

---

## Tier 2 — Sostituzione Dojo con API native identiche

### 2.1 `dojo.byId(id)` → `document.getElementById(id)`

Parte delle **109 occorrenze** di API DOM dojo (byId, body, doc, stopEvent, toJson, fromJson, trim).

```javascript
// PRIMA                              // DOPO
dojo.byId('myid')                     document.getElementById('myid')
```

Identico al 100%.

### 2.2 `dojo.body()` → `document.body`

```javascript
// PRIMA                              // DOPO
dojo.body()                            document.body
```

### 2.3 `dojo.doc` → `document`

```javascript
// PRIMA                              // DOPO
dojo.doc                               document
```

### 2.4 `dojo.stopEvent(e)` → due righe

```javascript
// PRIMA
dojo.stopEvent(e);

// DOPO
e.preventDefault();
e.stopPropagation();
```

### 2.5 `dojo.toJson(obj)` → `JSON.stringify(obj)`

```javascript
// PRIMA                              // DOPO
dojo.toJson(obj)                       JSON.stringify(obj)
```

### 2.6 `dojo.fromJson(str)` → `JSON.parse(str)`

```javascript
// PRIMA                              // DOPO
dojo.fromJson(str)                     JSON.parse(str)
```

**Bonus sicurezza**: `dojo.fromJson` usa `eval()` internamente.
`JSON.parse` e' sicuro per definizione.

### 2.7 `dojo.trim(str)` → `str.trim()`

```javascript
// PRIMA                              // DOPO
dojo.trim(str)                         str.trim()
```

### 2.8 `dojo.addClass/removeClass/hasClass/toggleClass`

**45 occorrenze** in 8 file.

```javascript
// PRIMA                              // DOPO
dojo.addClass(node, 'cls')            node.classList.add('cls')
dojo.removeClass(node, 'cls')         node.classList.remove('cls')
dojo.hasClass(node, 'cls')            node.classList.contains('cls')
dojo.toggleClass(node, 'cls')         node.classList.toggle('cls')
```

**Attenzione**: `dojo.addClass` accetta spazi nel nome classe
(`dojo.addClass(n, 'a b')`) mentre `classList.add` vuole argomenti separati
(`n.classList.add('a', 'b')`). Verificare caso per caso.

### 2.9 `dojo.query(selector)` → `document.querySelectorAll`

**41 occorrenze** in 9 file.

```javascript
// PRIMA
dojo.query('.myclass', containerNode)

// DOPO
containerNode.querySelectorAll('.myclass')
// oppure per array:
[...containerNode.querySelectorAll('.myclass')]
```

**Nota**: `dojo.query` ritorna un `NodeList` dojo con metodi extra
(`.forEach`, `.addClass`, etc.). Se il codice usa solo iterazione,
la sostituzione e' diretta. Se usa metodi NodeList dojo, serve adattamento.

---

## Tier 3 — Modernizzazione JS pura (senza toccare Dojo)

### 3.1 `for (var i=0; ...)` → `for...of` / `.forEach`

**~322 occorrenze** di for classici in 22 file.

```javascript
// PRIMA
for (var i = 0; i < items.length; i++) {
    doSomething(items[i]);
}

// DOPO
for (const item of items) {
    doSomething(item);
}
```

**Solo quando** il loop non usa `i` per altro (posizione, break con indice, etc.).

### 3.2 `arguments` → rest parameters

**24 occorrenze** in 8 file.

```javascript
// PRIMA
function myFunc() {
    var args = Array.prototype.slice.call(arguments);
    return otherFunc.apply(this, args);
}

// DOPO
function myFunc(...args) {
    return otherFunc(...args);
}
```

### 3.3 Callback anonime → arrow functions

Le callback passate a `forEach`, `map`, `filter`, event handler possono
diventare arrow functions. Questo e' gia' fatto in parte (il codice usa `let`
e `const` in molti punti, quindi lo stile misto e' gia' presente).

```javascript
// PRIMA
items.forEach(function(item) {
    this.process(item);
}.bind(this));

// DOPO
items.forEach(item => {
    this.process(item);
});
```

---

## NON toccare (rischio > 0)

| Pattern | Motivo |
|---------|--------|
| `dojo.connect` | Funziona anche su oggetti non-DOM, non e' solo addEventListener |
| `dojo.style(node, prop)` | Il getter ha semantica diversa da getComputedStyle |
| `dojo.coords` / `dojo.marginBox` | Interfaccia diversa da getBoundingClientRect |
| `dojo.place` | Parametri diversi da insertAdjacentHTML |
| `dojo.declare` | Sistema classi con inherited(), non sostituibile 1:1 |
| `dojo.connect` su non-DOM | Observer pattern su oggetti JS |
| `dojo.subscribe` / `dojo.publish` | Pub/sub interno, da valutare separatamente |

---

## Riepilogo Quantitativo

| Tier | Modifica | Occorrenze | Rischio |
|------|----------|-----------|---------|
| 1.1 | `var` → `let`/`const` | ~5.800 | Zero |
| 1.2 | `dojo.forEach/map/filter` → nativi | 121 | Zero |
| 1.3 | `dojo.hitch` → arrow/bind | 96 | Zero |
| 1.4 | `.indexOf()!=-1` → `.includes()` | 110 | Zero |
| 1.5 | String concat → template literals | ~500 | Zero |
| 1.6 | `typeof === 'undefined'` | 7 | Zero |
| 2.1-2.7 | `dojo.byId/body/doc/stop/json/trim` | 109 | Zero |
| 2.8 | `dojo.addClass/removeClass` | 45 | Zero (*) |
| 2.9 | `dojo.query` → `querySelectorAll` | 41 | Zero (*) |
| 3.1 | `for` classico → `for...of` | ~322 | Zero |
| 3.2 | `arguments` → rest params | 24 | Zero |
| **Totale** | | **~7.175** | |

(*) Richiede verifica caso per caso per parametri multipli.

---

## Strategia di Esecuzione

### Approccio consigliato: file per file, per priorita'

Non fare un mega-commit. Quando si tocca un file per qualsiasi motivo,
modernizzare i pattern presenti.

### Se si vuole fare un intervento mirato:

**Batch 1 — Massimo impatto, minimo rischio** (Tier 2.1-2.7):
- `dojo.byId` → `document.getElementById`
- `dojo.body()` → `document.body`
- `dojo.stopEvent` → `preventDefault + stopPropagation`
- `dojo.toJson` / `dojo.fromJson` → `JSON.stringify` / `JSON.parse`
- `dojo.trim` → `.trim()`

Sono le 109 occorrenze piu' facili da verificare: sostituzione 1:1 senza
casi particolari.

**Batch 2 — Array methods** (Tier 1.2):
- `dojo.forEach/map/filter/indexOf/some` → nativi

121 occorrenze, tutte meccaniche.

**Batch 3 — classList** (Tier 2.8):
- `dojo.addClass/removeClass/hasClass` → `classList`

45 occorrenze. Verificare che non si passino classi con spazi.

**Batch 4 — hitch** (Tier 1.3):
- `dojo.hitch(this, fn)` → arrow function

96 occorrenze. La piu' impattante per leggibilita'.
