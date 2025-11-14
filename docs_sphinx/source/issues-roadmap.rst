==============================
Problemi Noti e Roadmap
==============================

Questa pagina documenta i problemi noti del sistema Multidomain Workspace e le soluzioni proposte.

.. contents:: In questa pagina
   :local:
   :depth: 2

Problemi Noti
=============

Errori 400 su ``_main_`` in Produzione
---------------------------------------

**Severità**: 🔴 ALTA - Rende ``_main_`` inaccessibile dopo giorni di operatività

Descrizione
~~~~~~~~~~~

Dopo alcuni giorni di funzionamento in produzione, il dominio ``_main_`` diventa progressivamente inaccessibile restituendo errori **HTTP 400 Bad Request**, mentre i workspace clienti continuano a funzionare normalmente.

**Sintomi:**

- Errori 400 sul dominio ``/_main_/``
- Workspace clienti funzionano correttamente  
- Problema graduale (non immediato)
- Solo riavvio Gunicorn risolve temporaneamente

**Ambiente:** Gunicorn multiprocesso + multithread, Nginx, Neon DB

**Non riproducibile in locale** - Suggerisce problema di concorrenza o memory leak

Causa Identificata: _main_ come Catchall
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**PROBLEMA CRITICO TROVATO**: ``_main_`` funziona da **catchall** per richieste invalide!

Analisi del Codice
^^^^^^^^^^^^^^^^^^

File: ``gnrpy/gnr/web/gnrwsgisite.py``

**Step 1: Dispatcher inizializza sempre a _main_** (linea 951):

.. code-block:: python

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)
        self.currentDomain = self.rootDomain  # SEMPRE '_main_' all'inizio!
        # ...

**Step 2: handle_path_list() non resetta domain per richieste invalide** (linee 858-870):

.. code-block:: python

    def handle_path_list(self, path_info, request_kwargs=None):
        # ... parsing ...

        if self.multidomain:
            if first_segment in self.domains:
                # Domain valido: setta currentDomain
                self.currentDomain = first_segment
                if first_segment != self.rootDomain:
                    request_kwargs['base_dbstore'] = first_segment
                path_list.pop(0)
            elif first_segment not in self.storageTypes:
                # Richiesta invalida: marca suspicious MA...
                logger.debug('Multidomain with first segment without domain %s',
                           first_segment)
                request_kwargs['_souspicious_request_'] = True
                # ⚠️ currentDomain RIMANE '_main_'!

        # Domain propagato
        self.db.currentEnv['domainName'] = self.currentDomain  # '_main_'
        return path_list, redirect_to

Flusso Problematico
^^^^^^^^^^^^^^^^^^^

.. code-block:: text

    ┌──────────────────────────────────────────────────────────────┐
    │  Richiesta VALIDA: /workspace1/page                          │
    ├──────────────────────────────────────────────────────────────┤
    │  1. dispatcher(): currentDomain = '_main_'                   │
    │  2. handle_path_list('/workspace1/page')                     │
    │  3. 'workspace1' IN self.domains ✅                          │
    │  4. → currentDomain = 'workspace1'                           │
    │  5. → Register: domains['workspace1'].register               │
    │  6. → Cookie: teamset_workspace1                             │
    │  7. → Connection su workspace1 ✅ OK                         │
    └──────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────────────┐
    │  Richiesta INVALIDA: /randompath/page                        │
    ├──────────────────────────────────────────────────────────────┤
    │  1. dispatcher(): currentDomain = '_main_'                   │
    │  2. handle_path_list('/randompath/page')                     │
    │  3. 'randompath' NOT in self.domains ❌                      │
    │  4. 'randompath' NOT in self.storageTypes ❌                 │
    │  5. → Mark '_souspicious_request_' = True                    │
    │  6. → currentDomain RIMANE '_main_' ⚠️                       │
    │  7. → Register: domains['_main_'].register ❌                │
    │  8. → Cookie: teamset__main_ ❌                              │
    │  9. → Connection tracked su _main_ ❌ PROBLEMA!              │
    └──────────────────────────────────────────────────────────────┘

Impatto in Produzione
^^^^^^^^^^^^^^^^^^^^^

In produzione con traffico reale:

**Richieste invalide comuni:**

- Bot scanning: ``/wp-admin/``, ``/admin/``, ``/phpmyadmin/``
- 404 crawling: ``/old-path/``, ``/deleted-page/``
- Typos: ``/workspacee1/`` invece di ``/workspace1/``
- Security scans: ``/.env``, ``/config.php``
- Health checks mal configurati

**Ogni richiesta invalida**:

1. Crea connessione su register di ``_main_``
2. Scrive cookie per ``_main_``
3. Alloca memoria nel register ``_main_``
4. Non viene mai pulita (perché marcata "suspicious")

**Dopo giorni/settimane**:

.. code-block:: python

    # Register _main_ accumula migliaia di entries
    len(site.domains['_main_'].register.pages)        # → 50000+
    len(site.domains['_main_'].register.connections)  # → 30000+

    # Memory leak progressivo
    # Cookie corruption per collisioni
    # Connection pool saturo su rootstore
    # → 400 Bad Request quando soglia superata

Workspace normali non sono affetti perché:

- Richieste a ``/workspace1/*`` → domain esplicito
- Nessuna richiesta invalida finisce sui workspace clienti
- Register workspace puliti

Diagramma Comparativo
^^^^^^^^^^^^^^^^^^^^^

**Flusso _main_ (PROBLEMATICO):**

.. code-block:: text

    HTTP Request: /invalidpath/page
         ↓
    dispatcher()
    ├─ currentDomain = '_main_'  [INIZIALE]
    └─ call handle_path_list()
         ↓
    handle_path_list()
    ├─ first_segment = 'invalidpath'
    ├─ 'invalidpath' NOT in domains
    ├─ 'invalidpath' NOT in storageTypes
    ├─ Mark: _souspicious_request_ = True
    └─ currentDomain RIMANE '_main_'  [⚠️ NON CAMBIATO]
         ↓
    Create Page
    └─ Register su domains['_main_'].register  [❌ ACCUMULA]
         ↓
    Cookie Management
    └─ Cookie name: 'teamset__main_'  [❌ SHARED/CORRUPT]
         ↓
    Connection Tracking
    └─ Connection su register _main_  [❌ MEMORY LEAK]
         ↓
    Response: 404 Not Found
    └─ MA registro inquinato ⚠️

**Flusso Workspace (OK):**

.. code-block:: text

    HTTP Request: /workspace1/page
         ↓
    dispatcher()
    ├─ currentDomain = '_main_'  [INIZIALE]
    └─ call handle_path_list()
         ↓
    handle_path_list()
    ├─ first_segment = 'workspace1'
    ├─ 'workspace1' IN domains ✅
    ├─ SET: currentDomain = 'workspace1'  [✅ CAMBIATO]
    └─ base_dbstore = 'workspace1'
         ↓
    Create Page
    └─ Register su domains['workspace1'].register  [✅ ISOLATO]
         ↓
    Cookie Management
    └─ Cookie name: 'teamset_workspace1'  [✅ SPECIFICO]
         ↓
    Connection Tracking
    └─ Connection su register workspace1  [✅ PULITO]
         ↓
    Response: 200 OK
    └─ Registro pulito ✅

Soluzioni Possibili
~~~~~~~~~~~~~~~~~~~

Soluzione 1: Early check in isInMaintenance (QUICK FIX) 🧪 IN TESTING
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Status**: 🧪 **IN TESTING** nel branch ``feature/multidomain-workspace``

.. warning::
   Questo fix è attualmente in fase di testing. Non è ancora stato validato in produzione.

File modificato: ``gnrpy/gnr/web/gnrwsgisite.py`` (linea 934)

**Problema Identificato**:
``isInMaintenance`` property (chiamata da ``dispatcher()`` alla line 955) accedeva a register e cookies **prima** del check ``_souspicious_request_`` che avviene alla line 1132 in ``_dispatcher()``.

Questo causava accumulo su ``_main_`` register anche se la richiesta veniva poi rigettata.

**Soluzione**:
Aggiungere check early exit in ``isInMaintenance`` **prima** di accedere a register/cookies:

.. code-block:: python

    @property
    def isInMaintenance(self):
        request = self.currentRequest
        request_kwargs = self.parse_kwargs(self.parse_request_params(request))
        path_list,redirect_to = self.handle_path_list(request.path,request_kwargs=request_kwargs)

        # ✅ IMPLEMENTATO: Early exit BEFORE accessing register/cookies
        if redirect_to or request_kwargs.get('_souspicious_request_'):
            return False  # Exit BEFORE line 944-948 (cookie/register access)

        # ... resto del codice che accede a self.register (line 948)

**Flusso Corretto Ora**:

1. ``dispatcher()`` (line 955) chiama ``isInMaintenance``
2. ``isInMaintenance`` (line 931) chiama ``handle_path_list()``
3. ``handle_path_list()`` (line 869) marca ``_souspicious_request_ = True``
4. ``isInMaintenance`` (line 934) check e return False **PRIMA** di accedere register
5. ``dispatcher()`` prosegue a ``_dispatcher()``
6. ``_dispatcher()`` (line 1132) verifica di nuovo e chiama ``not_found_exception()``

**Risultato**: Strada unica coerente usando ``_souspicious_request_`` flag e ``not_found_exception()``, senza accessi a register/cookies di ``_main_``

**Vantaggi:**

- ✅ Fix immediato
- ✅ Nessun accumulo su ``_main_``
- ✅ Codice minimo (~4 righe)
- ✅ Logging migliorato (warning invece di debug)

**Svantaggi:**

- ❌ ``_main_`` rimane primus inter pares
- ❌ Non risolve altri problemi architetturali

**Test del Fix:**

.. code-block:: bash

    # Richiesta valida a _main_ → OK
    curl -I http://localhost:8081/_main_/
    # Expected: 200 OK

    # Richiesta a workspace valido → OK
    curl -I http://localhost:8081/workspace1/
    # Expected: 200 OK (se workspace1 esiste)

    # Richiesta invalida → 404 IMMEDIATO (no accumulo)
    curl -I http://localhost:8081/invalid_domain/
    # Expected: 404 Not Found (NO accumulo su _main_!)

**Verifica in Produzione:**

Prima del fix::

    >>> len(site.domains['_main_'].register.pages)
    50000+  # PROBLEMA - accumulo progressivo

Dopo il fix::

    >>> len(site.domains['_main_'].register.pages)
    ~100    # Solo richieste legittime a /_main_/

**Monitoring Consigliato:**

.. code-block:: python

    # Script monitoring per verificare fix
    def check_main_register_health():
        main_pages = len(site.domains['_main_'].register.pages)
        main_conns = len(site.domains['_main_'].register.connections)

        if main_pages > 1000:
            logger.error(f'_main_ register unhealthy: {main_pages} pages')
        else:
            logger.info(f'_main_ register healthy: {main_pages} pages')

Soluzione 2: Domain speciale 'invalid' (MEDIUM)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Creare domain dedicato per richieste invalide:

.. code-block:: python

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)
        # ✅ FIX: Default a 'invalid' invece di '_main_'
        self.currentDomain = '_invalid_'
        # ...

    def handle_path_list(self, path_info, request_kwargs=None):
        # ...
        if self.multidomain:
            if first_segment in self.domains:
                self.currentDomain = first_segment
                # ...
            elif first_segment not in self.storageTypes:
                # Keep currentDomain = '_invalid_'
                request_kwargs['_souspicious_request_'] = True

        # Se domain rimane '_invalid_', return 404
        if self.currentDomain == '_invalid_':
            raise HTTPNotFound()

**Vantaggi:**

- ✅ ``_main_`` protetto
- ✅ Logging/monitoring separato per invalide
- ✅ Backwards compatible

Soluzione 3: Architettura a due istanze (LONG-TERM)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Vedere sezione dedicata sotto.

Soluzione Proposta: Eliminare _main_
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Architettura a Due Istanze
