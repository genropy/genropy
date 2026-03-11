# Giojo Tree — Catalogo Completo delle Feature

## Panoramica

Il Tree di Giojo (derivato da dijit.Tree di Dojo 1.1) e' un widget ad albero completo
con caricamento lazy, persistenza stato, navigazione tastiera, drag & drop e
integrazione con dojo.data stores.

**5 file JS**:
- `dijit/Tree.js` — widget principale (`dijit.Tree` e `dijit._TreeNode`)
- `dijit/_tree/model.js` — interfaccia model (contratto)
- `dijit/_tree/dndContainer.js` — container DnD base
- `dijit/_tree/dndSelector.js` — selezione nodi per DnD
- `dijit/_tree/dndSource.js` — sorgente/target drag & drop

---

## Architettura

```
dijit.Tree (extends dijit._Widget + dijit._Templated)
 |
 +-- rootNode (dijit._TreeNode)
 |    +-- figli _TreeNode (lazy-loaded)
 |    |    +-- figli _TreeNode (ricorsivo)
 |    ...
 |
 +-- model (dijit.tree.model — interfaccia)
 |    implementazioni: ForestStoreModel, TreeStoreModel
 |
 +-- dndController (opzionale)
      dijit._tree.dndSource
       +-- dijit._tree.dndSelector
            +-- dijit._tree.dndContainer
```

---

## 1. Struttura ad Albero

### TreeNode (`dijit._TreeNode`)

Ogni nodo dell'albero e' un widget indipendente.

**Eredita da**: `dijit._Widget`, `dijit._Templated`, `dijit._Container`, `dijit._Contained`

**Struttura DOM**:
```html
<div class="dijitTreeNode">
    <div class="rowNode">
        <span class="dijitTreeExpando"/>      <!-- icona +/- -->
        <span class="dijitExpandoText"/>       <!-- testo +/-/* per accessibilita' -->
        <div class="dijitTreeContent">
            <div class="dijitTreeIcon"/>       <!-- icona nodo -->
            <span class="dijitTreeLabel"/>     <!-- testo label -->
        </div>
    </div>
    <div class="containerNode"/>               <!-- figli (creato dinamicamente) -->
</div>
```

### Proprieta' TreeNode
| Proprieta' | Default | Descrizione |
|------------|---------|-------------|
| `item` | `null` | Entry dojo.data associata al nodo |
| `label` | `""` | Testo visualizzato |
| `isExpandable` | `null` | Se mostrare icona +/- |
| `isExpanded` | `false` | Stato espanso/collassato |
| `state` | `"UNCHECKED"` | Stato caricamento: UNCHECKED → LOADING → LOADED |

---

## 2. Espansione e Collasso

### Caratteristiche
- **Caricamento lazy**: i figli vengono caricati dal model solo al primo expand
- **Animazione**: wipeIn/wipeOut con durata 150ms
- **Stati di caricamento**: UNCHECKED (non caricato), LOADING (in caricamento), LOADED
- **Icone espansione**: 4 stati visivi
  - `dijitTreeExpandoLeaf` — nodo foglia (nessun figlio)
  - `dijitTreeExpandoClosed` — nodo chiuso con figli
  - `dijitTreeExpandoOpened` — nodo aperto con figli
  - `dijitTreeExpandoLoading` — caricamento in corso

### Flusso di caricamento
1. Utente clicca su expando (o freccia destra)
2. Se `state == "UNCHECKED"` → icona "Loading", chiama `model.getChildren()`
3. Model risponde con array di items
4. `setChildItems()` crea `_TreeNode` per ogni item
5. `state = "LOADED"`, animazione wipeIn
6. Espansioni successive sono istantanee (figli gia' in memoria)

### API
```
node.expand()                  // Espande con animazione
node.collapse()                // Collassa con animazione
node.makeExpandable()          // Forza nodo come espandibile
node.setChildItems(items)      // Imposta figli da array items
node.setLabelNode(label)       // Imposta testo label
```

---

## 3. Persistenza Stato

### Caratteristiche
- **Cookie-based**: salva gli ID dei nodi aperti in un cookie
- **Abilitabile** (`persist: true`, default)
- **Auto-restore**: al caricamento ri-espande i nodi salvati
- **Nome cookie**: `tree.cookieName` (default basato su widget ID)

### Flusso
1. Ad ogni expand/collapse → aggiorna `_openedItemIds`
2. Chiama `_saveState()` → serializza IDs come CSV in cookie
3. Al `postCreate()` → legge cookie, popola `_openedItemIds`
4. Durante `setChildItems()` → se un item ID e' in `_openedItemIds`, lo espande

---

## 4. Model Interface

Il Tree e' disaccoppiato dai dati tramite un'interfaccia model (`dijit.tree.model`).

### Contratto Model
| Metodo | Descrizione |
|--------|-------------|
| `getRoot(onItem)` | Chiama callback con l'elemento radice |
| `getChildren(parentItem, onComplete)` | Chiama callback con array figli |
| `getIdentity(item)` | Ritorna ID univoco dell'item |
| `getLabel(item)` | Ritorna label dell'item |
| `mayHaveChildren(item)` | Indica se l'item puo' avere figli |
| `newItem(args, parent)` | Crea nuovo item |
| `pasteItem(child, oldParent, newParent, bCopy)` | Sposta/copia item |

### Callback Model → Tree
| Callback | Descrizione |
|----------|-------------|
| `onChange(item)` | Item modificato → aggiorna label/icona |
| `onChildrenChange(parent, newChildren)` | Figli cambiati → rebuild sotto-albero |

### Integrazione dojo.data
- Supporto legacy: `store` + `query` → converte automaticamente a `ForestStoreModel`
- Compatibile con `ItemFileReadStore` e `ItemFileWriteStore`

---

## 5. Personalizzazione Aspetto

### Metodi override
| Metodo | Parametri | Descrizione |
|--------|-----------|-------------|
| `getIconClass(item, opened)` | item, boolean | CSS class per icona nodo |
| `getLabelClass(item, opened)` | item, boolean | CSS class per label nodo |
| `getLabel(item)` | item | Testo label (override per custom formatting) |

### Classi CSS default
| Classe | Significato |
|--------|-------------|
| `dijitFolderOpened` | Icona cartella aperta |
| `dijitFolderClosed` | Icona cartella chiusa |
| `dijitLeaf` | Icona foglia |
| `dijitTreeNodeSelected` | Nodo selezionato |
| `dijitTreeNodeFocused` | Nodo con focus |
| `dijitTreeIsRoot` | Nodo root |
| `dijitTreeIsLast` | Ultimo sibling |

### Root nascosto
- `showRoot: false` → nasconde il nodo root, mostra solo i figli come top-level

---

## 6. Navigazione Tastiera

### Tasti gestiti
| Tasto | Azione |
|-------|--------|
| Freccia Giu' | Prossimo nodo visibile |
| Freccia Su | Nodo precedente visibile |
| Freccia Destra | Se chiuso: espande. Se aperto: va al primo figlio |
| Freccia Sinistra | Se aperto: collassa. Se chiuso: va al parent |
| Home | Primo nodo visibile (root o primo figlio) |
| End | Ultimo nodo visibile (foglia piu' profonda espansa) |
| Enter | Esegue onClick() sull'item |
| Lettera | Naviga al prossimo nodo con label che inizia con il carattere |

### Focus management
- Focus virtuale: il Tree mantiene `lastFocused`
- `tabIndex` gestito automaticamente (0 sul primo nodo focusabile)
- Re-entry: Tab torna al `lastFocused`
- WAI-ARIA: `waiRole="treeitem"`, `waiState="selected"`, `waiState="expanded"`

### API
```
tree.focusNode(node)           // Focus su nodo specifico
tree.blurNode()                // Rimuove focus
```

---

## 7. Click e Interazione Mouse

### Comportamento click
- **Click su expando (+/-)**: espande/collassa il nodo
- **Click su label**:
  - Se `openOnClick: false` (default) → esegue `onClick(item, node)`
  - Se `openOnClick: true` → espande/collassa (come click su expando)

### Evento onClick
```javascript
tree.onClick = function(item, node) {
    // item: dojo.data.Item cliccato
    // node: _TreeNode widget
};
```

### Pub/Sub
Gli eventi vengono pubblicati via `dojo.publish(tree.id, message)`:
- Topic `"execute"` → click su nodo o Enter
- Messaggio: `{ tree, event: "execute", item, node }`

---

## 8. Drag & Drop

Il Tree supporta DnD completo tramite un sistema a 3 livelli.

### Gerarchia DnD
```
dndContainer (base: tracking mouse, CSS states)
 +-- dndSelector (selezione singola/multipla)
      +-- dndSource (drag completo + drop)
           +-- dndTarget (solo target, non sorgente)
```

### 8.1 Container (`dijit._tree.dndContainer`)

Livello base: traccia il mouse e gestisce stati CSS.

| Proprieta' | Default | Descrizione |
|------------|---------|-------------|
| `current` | `null` | TreeNode sotto il mouse |
| `containerState` | `""` | Stato contenitore ("Over", "") |

| Metodo | Descrizione |
|--------|-------------|
| `onMouseOver(e)` | Traccia nodo sotto mouse, applica CSS |
| `onMouseOut(e)` | Rimuove CSS hover |
| `onOverEvent()` | Callback: mouse entra nel tree |
| `onOutEvent()` | Callback: mouse esce dal tree |

### 8.2 Selector (`dijit._tree.dndSelector`)

Aggiunge selezione nodi per il drag.

| Proprieta' | Default | Descrizione |
|------------|---------|-------------|
| `singular` | `false` | Solo selezione singola |
| `selection` | `{}` | Mappa nodi selezionati {id → node} |
| `anchor` | `null` | Nodo anchor per selezione range |

| Metodo | Descrizione |
|--------|-------------|
| `getSelectedItems()` | Array di dojo.data.Item selezionati |
| `getSelectedNodes()` | Dict nodi selezionati |
| `selectNone()` | Deseleziona tutto |
| `onMouseDown(e)` | Logica selezione: click, Ctrl+click |

### Modalita' selezione
- **Click singolo**: seleziona un nodo
- **Ctrl+Click**: aggiunge/toglie dalla selezione
- **Modalita' singola** (`singular: true`): un solo nodo alla volta

### 8.3 Source (`dijit._tree.dndSource`)

Drag & drop completo con integrazione model.

| Proprieta' | Default | Descrizione |
|------------|---------|-------------|
| `isSource` | `true` | Puo' essere sorgente drag |
| `copyOnly` | `false` | Se true, sempre copia (mai sposta) |
| `skipForm` | `false` | Non avvia drag su elementi form |
| `accept` | `["text"]` | Tipi accettati per drop |
| `isDragging` | `false` | In corso un drag |
| `targetAnchor` | `null` | Nodo target per il drop |
| `before` | `true` | Drop prima (true) o dopo (false) il target |

### Flusso DnD
1. **MouseDown** → seleziona nodo, imposta `mouseDown = true`
2. **MouseMove** → se mouse premuto e sorgente, avvia drag via `dojo.dnd.Manager`
3. **Durante drag**:
   - Manager pubblica `/dnd/start`
   - Ad ogni movimento: calcola posizione before/after
   - `checkAcceptance(source, nodes)` — verifica se il tree accetta il drop
   - `checkItemAcceptance(node, source)` — verifica per singolo nodo target
4. **Drop** → Manager pubblica `/dnd/drop`:
   - Se stessa sorgente: `model.pasteItem(child, oldParent, newParent, copy)`
   - Se sorgente esterna: `model.newItem(args)` + `itemCreator(nodes)`
   - Espande il nodo target dopo il drop
5. **Cancel** → Manager pubblica `/dnd/cancel`, ripristina stati

### CSS DnD
| Classe | Significato |
|--------|-------------|
| `dojoDndContainer` | Il tree e' un container DnD |
| `dojoDndSource` | Il tree e' una sorgente |
| `dojoDndTarget` | Il tree e' un target |
| `dojoDndItemOver` | Nodo sotto il mouse |
| `dojoDndItemSelected` | Nodo selezionato |
| `dojoDndItemAnchor` | Nodo anchor |
| `dojoDndItemBefore` | Drop prima del nodo |
| `dojoDndItemAfter` | Drop dopo il nodo |
| `dojoDndSourceCopied` | Sorgente in modalita' copia |
| `dojoDndSourceMoved` | Sorgente in modalita' spostamento |
| `dojoDndTargetDisabled` | Target non accetta drop |

### API DnD
```javascript
// Configurazione su Tree
new dijit.Tree({
    dndController: "dijit._tree.dndSource",
    checkAcceptance: function(source, nodes) { return true; },
    checkItemAcceptance: function(node, source) { return true; },
    itemCreator: function(nodes) { return {...}; },
    onDndDrop: function(source, nodes, copy) { ... }
});
```

### 8.4 Target (`dijit._tree.dndTarget`)

Versione solo-ricezione: eredita tutto da dndSource ma con `isSource: false`.
Non permette di trascinare nodi fuori dal tree, ma accetta drop.

---

## 9. Configurazione Tree

### Proprieta' principali
| Proprieta' | Default | Descrizione |
|------------|---------|-------------|
| `store` | `null` | (Deprecato) dojo.data store |
| `model` | `null` | Model interface per i dati |
| `query` | `null` | (Deprecato) Query per lo store |
| `label` | `""` | Label root |
| `showRoot` | `true` | Mostra nodo root |
| `childrenAttr` | `["children"]` | Attributi che contengono i figli |
| `openOnClick` | `false` | Click su label espande/collassa |
| `persist` | `true` | Salva stato espansione in cookie |
| `dndController` | `null` | Classe DnD controller |

### Metodi principali Tree
| Metodo | Descrizione |
|--------|-------------|
| `onClick(item, node)` | Callback click su nodo (override) |
| `getLabel(item)` | Ritorna label (override) |
| `getIconClass(item, opened)` | Ritorna CSS class icona (override) |
| `getLabelClass(item, opened)` | Ritorna CSS class label (override) |
| `mayHaveChildren(item)` | Override per controllare espandibilita' |
| `destroy()` | Distrugge albero e tutti i nodi |

---

## 10. WAI-ARIA Accessibilita'

### Ruoli e stati
- Container: `waiRole="tree"`
- Nodi: `waiRole="treeitem"`
- Stato selezione: `waiState="selected-true/false"`
- Stato espansione: `waiState="expanded-true/false"` (solo nodi espandibili)
- `tabIndex` gestito: 0 sul primo nodo, -1 sugli altri

---

## 11. Gestione Modifiche Model

Il Tree reagisce automaticamente ai cambiamenti del model.

| Evento Model | Azione Tree |
|-------------|-------------|
| `onChange(item)` | Aggiorna label e classi CSS del nodo |
| `onChildrenChange(parent, newChildren)` | Ricostruisce sotto-albero del parent |

### Aggiornamento nodo
Quando un item cambia:
1. Trova il `_TreeNode` nella mappa `_itemNodeMap`
2. Aggiorna `label` via `setLabelNode()`
3. Aggiorna `iconNode` e `labelNode` CSS classes

### Aggiornamento figli
Quando i figli di un nodo cambiano:
1. Trova il parent `_TreeNode`
2. Chiama `setChildItems(newChildren)`
3. Rimuove vecchi figli (orphan)
4. Crea nuovi `_TreeNode` per i nuovi items
5. Applica layout e persistenza

---

## Riepilogo Feature

| Categoria | Feature |
|-----------|---------|
| **Struttura** | Albero ricorsivo di _TreeNode, lazy loading, root nascondibile |
| **Espansione** | Expand/collapse con animazione wipeIn/wipeOut 150ms |
| **Caricamento** | Lazy: UNCHECKED → LOADING → LOADED, caricamento dal model |
| **Persistenza** | Stato espansione salvato in cookie, auto-restore |
| **Model** | Interfaccia disaccoppiata, integrazione dojo.data stores |
| **Personalizzazione** | Override icone, label, classi CSS per nodo |
| **Tastiera** | Frecce, Home/End, Enter, navigazione per lettera |
| **Focus** | Focus virtuale con WAI-ARIA, tabIndex gestito |
| **Accessibilita'** | WAI-ARIA roles e states completi |
| **Click** | Click su expando/label configurabile (`openOnClick`) |
| **DnD** | Drag & drop completo: selezione, sorgente, target |
| **DnD Selezione** | Singola, multipla (Ctrl+click) |
| **DnD Operazioni** | Sposta, copia (Ctrl), da/verso tree esterni |
| **DnD Model** | Integrato: pasteItem (move/copy), newItem (external drop) |
| **DnD Feedback** | CSS classes per hover, selezione, before/after, copy/move |
| **Reattivita'** | Auto-update su onChange/onChildrenChange del model |
| **Pub/Sub** | Eventi pubblicati via dojo.publish per integrazione esterna |
