# Piano Migrazione: Deferred/callback → async/await

## Obiettivo

Eliminare completamente `dojo.Deferred`, callback manuali e pattern sync a favore
di `Promise`, `async/await` e `fetch()`. Ispirato al resolver async della nuova
Bag Python (`genro-bag`).

---

## 1. Stato Attuale

### Networking

| Tipo chiamata | Meccanismo attuale | sync/async |
|---------------|-------------------|------------|
| RPC con callback | `dojo.xhrPost` + `addCallback` | async |
| RPC senza callback | `dojo.xhrPost({sync:true})` | sync (raro) |
| WebSocket | `genro.wsk.call()` → `dojo.Deferred` | async |
| Resolver relazionali | `GnrRemoteResolver({sync:true})` | sync |
| Resolver generici | `GnrRemoteResolver({sync:false})` | async |

Le chiamate sync sono limitate ai **resolver relazionali** (`relOneResolver`,
`relManyResolver`, `remoteResolver`) e a rare RPC senza callback.
Tutto il resto e' gia' async.

### Pattern Deferred nel codice GenroPy JS

| Pattern | Occorrenze | File coinvolti |
|---------|-----------|----------------|
| `instanceof dojo.Deferred` | 31 | 9 file |
| `.addCallback()` | ~35 | 8 file |
| `.addErrback()` | 4 | 2 file |
| `new dojo.Deferred()` | 2 | genro.js, gnrwebsocket.js |
| `.callback()` / `.errback()` | 6 | 3 file |

### Pattern dominante da eliminare

```javascript
// PRIMA — pattern ripetuto ~30 volte
var result = someOperation();
if (result instanceof dojo.Deferred) {
    result.addCallback(function(r) {
        doSomething(r);
    });
} else {
    doSomething(result);
}

// DOPO — async/await
var result = await someOperation();
doSomething(result);
```

---

## 2. Architettura Target

### Riferimento: Bag Python resolver

La nuova Bag Python (`genro-bag/src/genro_bag/resolver.py`) ha risolto il
problema architetturale con un pattern pulito:

- `load()` per resolver sync
- `async_load()` per resolver async
- `__call__()` come entry point unico con cache basata su fingerprint
- `_dispatch_load()` sceglie il path corretto

In JavaScript non serve la matrice 2x2 del Python (sync/async context ×
sync/async resolver) perche' **tutto puo' essere async** nel browser.

### Stack target

```
Applicativo GenroPy JS
        |
        v
   async/await
        |
        v
   fetch() / WebSocket    ← sostituisce dojo.xhr* e dojo.Deferred
        |
        v
   Server Python
```

### API networking target

```javascript
// giojo.rpc — sostituzione di genro.rpc._serverCall_execute

giojo.rpc = {
    async call(method, kwargs, options = {}) {
        const url = buildUrl(method, kwargs);
        const response = await fetch(url, {
            method: options.httpMethod || 'POST',
            headers: {'Content-Type': 'application/x-www-form-urlencoded'},
            body: serializeParams(kwargs)
        });
        return parseResponse(response, options.handleAs || 'xml');
    }
};
```

### Resolver target

```javascript
// giojo.RemoteResolver — sostituzione di gnr.GnrRemoteResolver

class RemoteResolver extends BagResolver {
    async load(kwargs) {
        return await giojo.rpc.call(this.method, kwargs);
    }
}
```

---

## 3. Fasi di Migrazione

### Fase 1 — Layer fetch() (impatto: 1 file)

Creare `giojo.rpc.call()` in `giojo.js` che wrappa `fetch()`.

**File da modificare**: `genro_rpc.js`

| Punto | Riga | Modifica |
|-------|------|----------|
| `_serverCall_execute` | 329-358 | Sostituire `dojo.xhrGet/Post/Put/Delete` con `fetch()` |
| `_serverCall` | 282-328 | Ritornare `Promise` invece di `dojo.Deferred` |
| `remoteCallAsync` | 388-408 | Semplificare — tutto e' async |

`_serverCall_execute` e' l'**unico punto** dove GenroPy tocca `dojo.xhr*`.
La modifica e' chirurgica.

### Fase 2 — Resolver async (impatto: 1 file)

Convertire `GnrRemoteResolver` ad async.

**File da modificare**: `genro_rpc.js`

| Punto | Riga | Modifica |
|-------|------|----------|
| `GnrRemoteResolver.load` | 51-96 | `async load()` con `await giojo.rpc.call()` |
| `remoteResolver` | 630-639 | Rimuovere `sync:true` |
| `remote_relOneResolver` | 799-814 | Rimuovere `sync:true` |
| `remote_relManyResolver` | 887-899 | Rimuovere `sync:true` |

### Fase 3 — Eliminare instanceof Deferred (impatto: 9 file)

Convertire il pattern `instanceof dojo.Deferred` → `await`.

Dettaglio per file (ordinato per impatto):

| File | Punti | Pattern |
|------|-------|---------|
| `gnrstores.js` | 7 | `instanceof` + `addCallback` su risultati store |
| `genro_frm.js` | 13 | `instanceof` + `addCallback` su save/delete/reload |
| `gnrbag.js` | 10 | `instanceof` in getValue, htraverse, setItem |
| `genro_grid.js` | 2 | `instanceof` su store data |
| `genro_components.js` | 2 | `instanceof` su risultati RPC |
| `genro_wdg.js` | 1 | `instanceof` su masterTotal |
| `genro.js` | 2 | `instanceof` + `new dojo.Deferred` |
| `gnrdomsource.js` | 1 | `addCallback` su deferred |
| `genro_tree.js` | 1 | `addCallback` su deferred |

**Trasformazione meccanica** — stesso pattern ovunque:

```javascript
// PRIMA
load: function() {
    var result = this.getStore();
    if (result instanceof dojo.Deferred) {
        result.addCallback(function(r) { finalize(r); });
    } else {
        finalize(result);
    }
}

// DOPO
load: async function() {
    var result = await this.getStore();
    finalize(result);
}
```

### Fase 4 — WebSocket (impatto: 1 file)

**File**: `gnrwebsocket.js`

| Punto | Riga | Modifica |
|-------|------|----------|
| `call` | 198 | `new dojo.Deferred()` → `new Promise()` |
| callback/errback | 119-122 | `resolve()`/`reject()` |
| `addCallback` | 211, 225 | `.then()` o `await` |

```javascript
// PRIMA
call: function(kwargs) {
    var deferred = new dojo.Deferred();
    // ... invio via websocket ...
    // al ritorno:
    deferred.callback(result);
    return deferred;
}

// DOPO
call: function(kwargs) {
    return new Promise((resolve, reject) => {
        // ... invio via websocket ...
        // al ritorno:
        resolve(result);
    });
}
```

### Fase 5 — Codice applicativo

Il codice applicativo GenroPy (fuori dal core JS) che usa `dojo.Deferred`
va modificato quando si incontra. Pattern identico alle fasi precedenti.

Casi possibili nel codice applicativo:
- `result.addCallback(fn)` → `result.then(fn)` o `await result`
- `new dojo.Deferred()` → `new Promise()`
- `deferred.callback(val)` → `resolve(val)`

---

## 4. Mapping Deferred → Promise

| dojo.Deferred | Promise/async | Note |
|---------------|---------------|------|
| `new dojo.Deferred()` | `new Promise((resolve, reject) => ...)` | |
| `deferred.callback(val)` | `resolve(val)` | Dentro il costruttore Promise |
| `deferred.errback(err)` | `reject(err)` | Dentro il costruttore Promise |
| `deferred.addCallback(fn)` | `.then(fn)` | O meglio: `await` |
| `deferred.addErrback(fn)` | `.catch(fn)` | O meglio: `try/catch` |
| `deferred.addBoth(fn)` | `.finally(fn)` | |
| `instanceof dojo.Deferred` | Non necessario | Con `await` il valore e' sempre risolto |
| `deferred.cancel()` | `AbortController` | Per fetch; Promise non ha cancel |

### Caso cancel()

`dojo.Deferred` supporta `cancel()`. In GenroPy e' usato solo in
`GnrBagResolver.cancelMeToo()` (gnrbag.js). Per `fetch()` si usa
`AbortController`:

```javascript
const controller = new AbortController();
const response = await fetch(url, { signal: controller.signal });
// per cancellare:
controller.cancel();
```

---

## 5. Riferimento Architetturale: Bag Python

### resolver.py — Pattern da portare in JS

**Cache con fingerprint** (resolver.py:460-470):
```python
effective_kw = dict(self._kw)
if self._parent_node:
    for key in self._kw:
        if key not in self.internal_params and key in self._parent_node.attr:
            effective_kw[key] = self._parent_node.attr[key]
effective_kw.update(call_kwargs)

current_fingerprint = self._compute_effective_fingerprint(effective_kw)
if current_fingerprint == self._last_effective_fingerprint and not self.expired:
    return self.cached_value
```

Questo pattern e' superiore al `cacheTime` attuale della Bag JS perche'
invalida la cache anche quando i **parametri** cambiano, non solo per timeout.

**Priorita' parametri** (resolver.py:454-460):
```
1. call_kwargs  (passati alla chiamata)     ← massima priorita'
2. node.attr    (attributi del nodo)
3. resolver._kw (default del resolver)      ← minima priorita'
```

Stesso pattern della Bag JS attuale ma formalizzato e con invalidazione
cache automatica.

**Conversione automatica** (resolver.py:535-567):
Il risultato del resolver viene automaticamente convertito in Bag se
possibile (dict, list, XML string, JSON string). Da portare in JS.

---

## 6. Dipendenze da Rimuovere

Dopo la migrazione completa, queste parti di Dojo non servono piu':

| Modulo Dojo | Righe | Motivo rimozione |
|-------------|-------|------------------|
| `_base/Deferred.js` | 408 | → Promise nativo |
| `_base/xhr.js` | 730 | → fetch() nativo |
| `DeferredList.js` | ~80 | → Promise.all() |
| `io/iframe.js` | ~200 | → FormData + fetch |
| `_base/json.js` | 137 | → JSON.parse/stringify |

Totale: **~1.555 righe** di codice Dojo eliminabili.

---

## 7. Rischi e Mitigazioni

| Rischio | Mitigazione |
|---------|-------------|
| Funzione non-async che chiama async | In JS l'async e' contagioso: la funzione chiamante diventa async. Propagare verso l'alto. |
| Event handler DOM (non possono essere async) | Wrappare: `onclick = () => { handleClick().catch(console.error); }` |
| Performance fetch vs XHR | fetch e' nativo e ottimizzato. Nessun overhead. |
| Codice applicativo sparso | Migrazione incrementale: si converte quando si tocca il file. Il ponte Deferred→Promise non serve se si fa file per file. |
| `cancel()` su Deferred | Raro (solo cancelMeToo in gnrbag.js). Usare AbortController. |

---

## 8. Ordine di Esecuzione

```
Fase 1: fetch() layer in giojo.js          ← nessun impatto sui chiamanti
   |
   v
Fase 2: GnrRemoteResolver → async          ← resolver funzionano con fetch
   |
   v
Fase 3: instanceof Deferred → await         ← file per file, 9 file
   |    gnrstores.js     (7 punti)
   |    genro_frm.js     (13 punti)
   |    gnrbag.js        (10 punti)
   |    genro_grid.js    (2 punti)
   |    genro_components (2 punti)
   |    genro_wdg.js     (1 punto)
   |    genro.js         (2 punti)
   |    gnrdomsource.js  (1 punto)
   |    genro_tree.js    (1 punto)
   |
   v
Fase 4: WebSocket → Promise                 ← gnrwebsocket.js
   |
   v
Fase 5: Codice applicativo                  ← incrementale, quando serve
   |
   v
Rimozione: Deferred.js, xhr.js, DeferredList.js, io/iframe.js, json.js
```

---

## Note

- Il pattern `instanceof dojo.Deferred` + `addCallback` e' ripetuto ~30 volte
  con la stessa struttura — la trasformazione e' meccanica e verificabile.
- La Fase 1 (fetch layer) puo' essere implementata **senza toccare nessun
  chiamante** — si sostituisce solo `_serverCall_execute`.
- Il codice applicativo puo' essere migrato incrementalmente: quando si tocca
  un file per altri motivi, si convertono i Deferred.
- `dojo.Deferred` supporta chaining sincrono (addCallback su Deferred gia'
  risolto esegue la callback immediatamente). Con Promise il chaining e'
  sempre asincrono (microtask). Questo **non** dovrebbe causare problemi
  perche' il codice GenroPy non dipende dall'esecuzione sincrona del chaining.
