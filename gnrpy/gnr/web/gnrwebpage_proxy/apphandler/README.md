# apphandler — Sub-package

Refactoring del monolite `apphandler.py` (2204 righe, ~80 metodi) in un
sub-package con mixin.

## Struttura

```
apphandler/
├── __init__.py          # GnrWebAppHandler (classe assemblata + metodi core/condivisi)
├── get_selection.py     # GetSelectionMixin: getSelection, getRecordCount + privati
├── get_record.py        # GetRecordMixin: getRecord + privati
├── related.py           # RelatedMixin: getRelatedRecord, getRelatedSelection
├── db_select.py         # DbSelectMixin: dbSelect + privati + ESCAPE_SPECIAL
├── batch.py             # BatchMixin: rpc_batchDo, thermo + BatchExecutor
├── export.py            # ExportMixin: print/pdf/export
├── structure.py         # StructureMixin: schema introspection
├── misc.py              # MiscMixin: CRUD, grid, frozen selections, filesystem, form
└── README.md            # Questo file
```

## Retrocompatibilita

L'import esterno **non cambia**:

```python
from gnr.web.gnrwebpage_proxy.apphandler import GnrWebAppHandler
from gnr.web.gnrwebpage_proxy.apphandler import BatchExecutor
```

Unico punto di import: `gnrwebpage.py:52`.

## MRO della classe assemblata

```
GnrWebAppHandler
├── GetSelectionMixin
├── GetRecordMixin
├── RelatedMixin
├── DbSelectMixin
├── BatchMixin
├── ExportMixin
├── StructureMixin
├── MiscMixin
└── GnrBaseProxy
```

## Dipendenze cross-mixin

I metodi condivisi usati da piu mixin vivono in `__init__.py`:

| Metodo | Usato da |
|--------|----------|
| `_getSqlContextConditions` | `get_selection`, `related` |
| `_joinConditionsFromContext` | `get_selection`, `get_record`, `related` |
| `_getApplyMethodPars` | `get_selection`, `get_record`, `related` |
| `_decodeWhereBag` | `get_selection`, `misc` |

Le dipendenze cross-mixin si risolvono a runtime via `self` nel MRO:

- `related.py` chiama `self.getRecord` (da `get_record.py`)
- `get_record.py` chiama `self.getRelatedRecord` (da `related.py`)
- `get_selection.py` chiama `self.gridSelectionData/gridSelectionStruct` (da `misc.py`)
- `misc.py` chiama `self._decodeWhereBag` (da `__init__.py`)

## Flussi principali

### getSelection (get_selection.py)
Il flusso piu complesso (~216 righe per il metodo principale). Gestisce:
- Parsing colonne e struttura griglia
- Query principale con filtri, ordinamento, paginazione
- Selezioni linkate (master-slave)
- Query su store esterni
- Output formattato per la griglia client-side

### getRecord (get_record.py)
Caricamento singolo record per primary key. Gestisce:
- Locking e protezione scrittura/cancellazione
- `onLoading` handlers (pagina e tabella)
- Espansione eager delle relazioni one-to-one
- Counter columns e sequences
- Default values per new record

### dbSelect (db_select.py)
Ricerca per autocomplete (FilteringSelect). Gestisce:
- Query con escape caratteri speciali
- Ordinamento per rilevanza
- Raggruppamento risultati
- Multi-fetch per batch resolving

### Batch (batch.py)
Esecuzione batch operations con progress tracking (thermo).

### Export (export.py)
Esportazione selezioni in Excel, HTML print, PDF.

---

## Inventario problemi

### BUG (errori logici che producono comportamento errato)

| # | File | Descrizione |
|---|------|-------------|
| B1 | `__init__.py` | `_getAppId`: `.split['/']` usa subscript sul metodo invece di chiamarlo — dovrebbe essere `.split('/')[2]` |
| B2 | `batch.py` | `rpc_batchDo`: `from processing import Process` — il modulo `processing` non esiste, dovrebbe essere `from multiprocessing import Process` |
| B3 | `batch.py` | `setThermo`: `command == 'end'` e un confronto (scartato) invece dell'assegnamento `command = 'end'` — il thermo non termina mai automaticamente |
| B4 | `export.py` | `rpc_printStaticGrid`: `not filename.lower().endswith('.html') or filename.lower().endswith('.htm')` — mancano le parentesi attorno all'`or`, quindi il `not` si applica solo al primo operando |
| B5 | `export.py` | `rpc_printStaticGridDownload`: `result.decode('utf-8')` — in Python 3 `str` non ha `.decode()`, solleva `AttributeError` |
| B6 | `export.py` | `_getStoreBag`: usa `self.unfreezeSelection` e `self.app.db` — dovrebbe essere `self.db` |
| B7 | `get_selection.py` | `getSelection`: `formats[7:]` e uno slice assignment su un dict — dovrebbe essere `formats[k[7:]] = kwargs.pop(k)` |
| B8 | `misc.py` | `duplicateDbRows`: format string `'...table % for user %s'` — manca la `s` dopo il primo `%` |
| B9 | `misc.py` | `deleteDbRows`: stessa format string rotta |
| B10 | `misc.py` | `gridSelectionStruct`: `if size < 6` dovrebbe essere `elif` — quando `size < 3` entrambe le branch eseguono |
| B11 | `related.py` | `getRelatedSelection`: `joinBag = None` sovrascrive il valore calcolato — la branch `applymethod` e dead code |

### SMELL (code smell — funziona ma e fragile o confuso)

| # | File | Descrizione |
|---|------|-------------|
| S1 | `__init__.py` | `_finalize`: accetta `page` ma non lo usa — usa sempre `self.db` |
| S2 | `__init__.py` | `getDb`: `dbId` accettato ma ignorato |
| S3 | `__init__.py` | `_getAppId`: usa `hasattr` per caching — puo mascherare `AttributeError` |
| S4 | `__init__.py` | `_getAppId`: `not x in y` invece di `x not in y` |
| S5 | `structure.py` | `_dbStructureInner`: confronto `!= None` invece di `is not None` |
| S6 | `structure.py` | `_dbStructureInner`: JS resolver string inline |
| S7 | `batch.py` | `setThermo`: fallback `progress_1 or thermoBag['t1.maximum']` legge maximum invece di progress |
| S8 | `batch.py` | `BatchExecutor`: `weakref.ref` commentato — in un processo forked i weak ref non funzionano |
| S9 | `export.py` | `rpc_onSelectionDo`: `!= None` invece di `is not None` |
| S10 | `export.py` | `export_standard`: fallback a `self.maintable` mescola le responsabilita proxy/page |
| S11 | `export.py` | `print_standard` / `pdf_standard`: dead code `columns = None; if not columns:` |
| S12 | `export.py` | `_exportFileNameClean`: restituisce `bytes` in Python 3 |
| S13 | `export.py` | `_getStoreBag`: commento "da finire" — implementazione incompleta |
| S14 | `export.py` | `rpc_printStaticGrid`: scrive bytes in file text-mode |
| S15 | `db_select.py` | `dbSelect`: parametro duale `_querystring` / `querystring` |
| S16 | `db_select.py` | `dbSelect_default`: `group_by` usato sia come colonna che come flag booleano |
| S17 | `get_selection.py` | `getSelection`: ~40 parametri — serve un context object |
| S18 | `get_selection.py` | `_getSelection_columns`: chiama `self.app._decodeWhereBag` con indirezione inutile |
| S19 | `get_record.py` | `_getRecord_locked`: lock disabilitato — il metodo e un no-op |
| S20 | `get_record.py` | `getRecord`: ~30 parametri con bookkeeping interno esposto |
| S21 | `get_record.py` | `getRecord`: `_resolver_kwargs` accettato ma mai usato |
| S22 | `get_record.py` | `_handleEagerRelations`: mutazione in-place con side effect pesanti |
| S23 | `related.py` | `getRelatedRecord`: `not x in y` invece di `x not in y` |
| S24 | `related.py` | `getRelatedSelection`: `query_columns` loggato come errore ma usato come fallback |
| S25 | `related.py` | `getRelatedSelection`: `getattr(self, 'self.newprocess', 'no')` — attr name con punto, sempre `'no'` |
| S26 | `misc.py` | `rpc_getRecordForm`: chiama `self.getRecordForm` che non e definito |

### REVIEW (decisioni di design da rivalutare)

| # | File | Descrizione |
|---|------|-------------|
| R1 | `get_record.py` | `_handleEagerRelations`: `_eager_one == 'weak'` guard solo a livello 0 — potrebbe impedire eager loading nested legittimo |
| R2 | `misc.py` | `saveEditedRows`: rilevamento conflitti concorrenti basato su confronto `_loadedValue` |
| R3 | `related.py` | `getRelatedRecord`: FK mancante produce silenziosamente un `*newrecord*` — potrebbe mascherare problemi di integrita dati |
| R4 | `get_selection.py` | `_default_getSelection`: chiamato senza argomenti — possibile dead code |

### TODO (dal codice originale)

| # | File | Descrizione |
|---|------|-------------|
| T1 | `get_record.py` | `getRecord` L243: fallback a `onLoadingRelatedMethod` se `onLoading` manca |
