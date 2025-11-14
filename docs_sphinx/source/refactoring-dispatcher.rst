=======================================
Refactoring Dispatcher - Suggerimenti
=======================================

Analisi dei problemi architetturali nel dispatcher di ``gnrwsgisite.py`` e proposte di miglioramento.

.. contents:: Indice
   :local:
   :depth: 3

Problemi Identificati
=====================

1. Flusso di Controllo Confuso
-------------------------------

**Problema**: Il flusso attraversa multiple funzioni con logiche intrecciate e side-effects nascosti.

Flusso Attuale
~~~~~~~~~~~~~~

.. code-block:: text

    dispatcher() [line 951]
      ├─ Inizializza currentDomain = rootDomain ('_main_')
      ├─ Chiama isInMaintenance [property]
      │   ├─ Richiama handle_path_list() [side effect: modifica currentDomain]
      │   ├─ Accede a self.register (dipende da currentDomain)
      │   ├─ Accede a cookie (dipende da currentDomain)
      │   └─ Return True/False
      │
      ├─ Se maintenance → maintenanceDispatcher()
      │   └─ Richiama handle_path_list() [DOPPIA CHIAMATA!]
      │
      └─ Altrimenti → _dispatcher()
          └─ Richiama handle_path_list() [TERZA CHIAMATA!]

**Problemi**:

- ``handle_path_list()`` viene chiamato **fino a 3 volte** per la stessa richiesta
- ``isInMaintenance`` ha side-effects (modifica ``currentDomain``)
- Dipendenze circolari tra domain, register, cookies
- Ogni chiamata ripete parsing e validazione

**Impatto Performance**:

.. code-block:: python

    # Per ogni richiesta HTTP:
    parse_request_params()  # 3x - wasteful!
    handle_path_list()      # 3x - wasteful!
    URL parsing             # 3x - wasteful!

2. isInMaintenance - Property con Side-Effects
-----------------------------------------------

**Problema**: ``isInMaintenance`` è una property che modifica lo stato (anti-pattern).

Codice Attuale (line 928-948)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @property
    def isInMaintenance(self):
        request = self.currentRequest
        request_kwargs = self.parse_kwargs(self.parse_request_params(request))  # Side effect!
        path_list,redirect_to = self.handle_path_list(request.path,request_kwargs=request_kwargs)  # Side effect!

        if redirect_to or request_kwargs.get('_souspicious_request_'):
            return False

        # Accesso a register/cookie usando currentDomain modificato da handle_path_list
        r = GnrWebRequest(request)
        c = r.get_cookie(self.currentDomainIdentifier,'marshal', secret=self.config['secret'])
        user = c.get('user') if c else None
        return self.register.isInMaintenance(user)  # Accede a register domain-specific

**Problemi**:

❌ Property dovrebbe essere **read-only e senza side-effects**

❌ Modifica ``currentDomain`` (chiamando ``handle_path_list``)

❌ Accede a register **prima** di validare la richiesta

❌ Parsing ripetuto in ogni punto del flusso

**Proposta**: Convertire in metodo esplicito o eliminare completamente

3. Maintenance Check su Register
---------------------------------

**Problema**: Il check di maintenance accede al register domain-specific, causando accumulo su ``_main_`` per richieste invalide.

**Da Cassare**: Secondo le indicazioni, il meccanismo di maintenance che accede al register è da eliminare.

Motivi per Rimuoverlo
~~~~~~~~~~~~~~~~~~~~~

1. **Complessità inutile**: Maintenance dovrebbe essere system-wide, non per-domain
2. **Performance**: Accesso a register per ogni richiesta HTTP è costoso
3. **Memory leak**: Causa accumulo su ``_main_`` (problema attuale)
4. **Race conditions**: Check concurrent su register in multithread/multiprocess
5. **Semantica confusa**: Maintenance per domain vs maintenance generale

Proposta
~~~~~~~~

.. code-block:: python

    # Opzione 1: Maintenance a livello site (file flag)
    @property
    def isInMaintenance(self):
        return os.path.exists(self.maintenance_flag_file)

    # Opzione 2: Maintenance in config/env
    @property
    def isInMaintenance(self):
        return self.config.get('maintenance_mode', False)

    # Opzione 3: Maintenance in memoria (settabile da admin)
    @property
    def isInMaintenance(self):
        return self._maintenance_mode  # Simple boolean flag

**Vantaggi**:

✅ Zero accessi a database/register per check maintenance

✅ Performance migliori (check su file/memoria vs DB query)

✅ Semantica chiara (maintenance = site-wide)

✅ No memory leak

✅ Thread-safe

4. Chiamate Multiple a handle_path_list()
------------------------------------------

**Problema**: Parsing URL ripetuto multiple volte nello stesso request lifecycle.

Occorrenze
~~~~~~~~~~

1. **Line 933**: ``isInMaintenance`` → parse URL
2. **Line 980**: ``maintenanceDispatcher`` → parse URL
3. **Line 1046**: ``_dispatcher`` → parse URL

**Spreco**:

- CPU: 3x parsing dello stesso URL
- Memoria: 3x allocazione ``path_list``, ``request_kwargs``
- Cache miss: Nessun caching tra chiamate

Proposta
~~~~~~~~

.. code-block:: python

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)

        # Parse UNA SOLA VOLTA all'inizio
        request_kwargs = self.parse_kwargs(self.parse_request_params(self.currentRequest))
        path_list, redirect_to = self.handle_path_list(
            self.currentRequest.path,
            request_kwargs=request_kwargs
        )

        # Valida PRIMA di qualsiasi accesso a risorse
        if request_kwargs.get('_souspicious_request_'):
            return self.not_found_exception(environ, start_response)

        if redirect_to:
            return self.redirect(environ, start_response, location=redirect_to)

        # Ora currentDomain è settato correttamente
        # Check maintenance DOPO validazione
        if self.isInMaintenance:
            return self.maintenanceDispatcher(environ, start_response,
                                              path_list, request_kwargs)

        # Dispatch normale
        return self._dispatcher(environ, start_response,
                               path_list, request_kwargs)

5. currentDomain Inizializzato a _main_
----------------------------------------

**Problema**: ``currentDomain`` inizializza sempre a ``rootDomain`` (``_main_``), causando il catchall.

Codice Attuale (line 953)
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)
        self.currentDomain = self.rootDomain  # SEMPRE '_main_' inizialmente

**Problemi**:

- Ogni operazione prima di ``handle_path_list`` usa ``_main_`` come domain
- ``isInMaintenance`` accede a register di ``_main_``
- Richieste invalide restano su ``_main_``

Proposta: Domain Sentinel
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)

        # Non inizializzare domain - forza validazione esplicita
        self.currentDomain = None  # o '_unvalidated_'

        # Parsing URL SUBITO
        request_kwargs = self.parse_kwargs(self.parse_request_params(self.currentRequest))
        path_list, redirect_to = self.handle_path_list(
            self.currentRequest.path,
            request_kwargs=request_kwargs
        )

        # Dopo handle_path_list, currentDomain è settato correttamente O è None
        if self.currentDomain is None:
            # Richiesta invalida - reject subito
            return self.not_found_exception(environ, start_response)

**Vantaggi**:

✅ Esplicito: ``currentDomain=None`` → richiesta non ancora validata

✅ Fail-safe: Qualsiasi accesso a ``self.register`` prima della validazione → errore esplicito

✅ No catchall: Impossibile accumulare su ``_main_``

Proposte di Refactoring
========================

Soluzione 1: Dispatcher Lineare (CONSIGLIATO)
----------------------------------------------

Refactoring completo per flusso lineare senza side-effects.

Struttura Proposta
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def dispatcher(self, environ, start_response):
        """
        Linear dispatcher with explicit validation stages.
        No side-effects in validation phase.
        """
        # 1. PARSE REQUEST (no state modification)
        request = Request(environ)
        request_kwargs = self.parse_kwargs(self.parse_request_params(request))

        # 2. VALIDATE AND EXTRACT DOMAIN (no resource access)
        domain, path_list, redirect_to = self._validate_request(
            request.path, request_kwargs
        )

        # 3. EARLY EXITS (before any resource access)
        if redirect_to:
            return self.redirect(environ, start_response, location=redirect_to)

        if domain is None:  # Invalid request
            return self.not_found_exception(environ, start_response)

        # 4. SET VALIDATED STATE
        self.currentRequest = request
        self.currentDomain = domain
        self.db.currentEnv['domainName'] = domain

        # 5. CHECK MAINTENANCE (simple, no DB access)
        if self.isInMaintenance:
            return self.maintenanceDispatcher(environ, start_response,
                                              path_list, request_kwargs)

        # 6. DISPATCH TO HANDLER
        return self._dispatcher(environ, start_response,
                               path_list, request_kwargs)

    def _validate_request(self, path_info, request_kwargs):
        """
        Pure validation function: no side effects, no state modification.

        Returns:
            (domain, path_list, redirect_to)
            domain=None if invalid request
        """
        path_list = [x for x in path_info.split('/') if x]
        redirect_to = None

        if not path_list:
            return self.rootDomain, ['index'], None

        first_segment = path_list[0]

        # Multidomain handling
        if self.multidomain:
            if first_segment in self.domains:
                # Valid domain
                domain = first_segment
                if domain != self.rootDomain:
                    request_kwargs['base_dbstore'] = domain
                path_list.pop(0)
            elif first_segment not in self.storageTypes:
                # Invalid domain - NO FALLBACK TO _main_
                logger.warning('Invalid domain in multidomain mode: %s', first_segment)
                request_kwargs['_souspicious_request_'] = True
                return None, path_list, None  # domain=None → reject
            else:
                domain = self.rootDomain
        else:
            domain = self.rootDomain

        return domain, path_list, redirect_to

**Vantaggi**:

✅ **Flusso lineare**: Validazione → Early exits → State setting → Dispatch

✅ **Zero side-effects**: ``_validate_request`` è pura (no state modification)

✅ **Performance**: Parsing URL una sola volta

✅ **Explicit is better than implicit**: Domain validation esplicita

✅ **Fail-safe**: ``domain=None`` per richieste invalide

Soluzione 2: Maintenance Simplificato
--------------------------------------

Eliminare completamente il check maintenance dal register.

Opzione A: File Flag
~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @property
    def isInMaintenance(self):
        """Check maintenance mode via file flag (fastest)."""
        maintenance_file = os.path.join(self.instance_path, '.maintenance')
        return os.path.exists(maintenance_file)

    def enable_maintenance(self):
        """Enable maintenance mode."""
        maintenance_file = os.path.join(self.instance_path, '.maintenance')
        Path(maintenance_file).touch()

    def disable_maintenance(self):
        """Disable maintenance mode."""
        maintenance_file = os.path.join(self.instance_path, '.maintenance')
        try:
            os.remove(maintenance_file)
        except FileNotFoundError:
            pass

**Vantaggi**:

✅ Zero DB access

✅ Thread-safe (OS-level file check)

✅ Deployable (Ansible/script can create file)

✅ No memory leak

Opzione B: Environment Variable
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    @property
    def isInMaintenance(self):
        """Check maintenance mode via environment variable."""
        return os.getenv('GENROPY_MAINTENANCE_MODE', '0') == '1'

**Vantaggi**:

✅ Zero filesystem access

✅ Configurabile da systemd/docker

✅ Immediate (no file I/O)

Opzione C: In-Memory Flag con RPC
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._maintenance_mode = False
        self._maintenance_lock = threading.Lock()

    @property
    def isInMaintenance(self):
        """Check maintenance mode (in-memory)."""
        with self._maintenance_lock:
            return self._maintenance_mode

    def setMaintenance(self, enabled):
        """Set maintenance mode (callable via RPC)."""
        with self._maintenance_lock:
            self._maintenance_mode = enabled
            logger.info(f'Maintenance mode {"enabled" if enabled else "disabled"}')

**Vantaggi**:

✅ Immediate (no I/O)

✅ Controllabile via RPC da admin interface

✅ Thread-safe (lock)

**Svantaggi**:

❌ Per-process (in multiprocess deployment, ogni worker ha suo flag)

Soluzione 3: Separation of Concerns
------------------------------------

Separare dispatcher in componenti specializzati.

Struttura Proposta
~~~~~~~~~~~~~~~~~~

.. code-block:: python

    class RequestValidator:
        """Pure validation logic - no state, no side effects."""

        def validate(self, path_info, multidomain, domains, storage_types):
            """Returns (domain, path_list, is_valid, redirect_to)."""
            pass

    class MaintenanceManager:
        """Centralized maintenance management."""

        def is_in_maintenance(self):
            """Simple check without DB access."""
            pass

        def enable_maintenance(self, message=None):
            pass

        def disable_maintenance(self):
            pass

    class RequestDispatcher:
        """Orchestrates request flow."""

        def __init__(self):
            self.validator = RequestValidator()
            self.maintenance = MaintenanceManager()

        def dispatch(self, environ, start_response):
            # 1. Validate
            domain, path_list, is_valid, redirect = self.validator.validate(...)

            # 2. Early exits
            if not is_valid:
                return self.not_found(environ, start_response)

            if redirect:
                return self.redirect(environ, start_response, redirect)

            # 3. Check maintenance
            if self.maintenance.is_in_maintenance():
                return self.serve_maintenance(environ, start_response)

            # 4. Dispatch to handler
            return self.handle_request(environ, start_response, domain, path_list)

**Vantaggi**:

✅ **Testable**: Ogni componente testabile isolatamente

✅ **Clean**: Separation of concerns

✅ **Maintainable**: Logica chiara e modulare

✅ **Reusable**: Validator riusabile in altri contesti

Roadmap di Implementazione
===========================

Fase 1: Quick Wins (Immediate)
-------------------------------

1. ✅ **Fix isInMaintenance**: Aggiungere early exit per ``_souspicious_request_`` (FATTO)
2. 🔄 **Test in produzione**: Validare fix attuale
3. 📝 **Documentare limitazioni**: Marcare codice problematico con TODO

Fase 2: Maintenance Refactor (Short-term)
------------------------------------------

1. Implementare ``isInMaintenance`` con file flag
2. Rimuovere accesso a register da maintenance check
3. Aggiungere RPC per controllo maintenance da admin
4. Test in staging

**Effort**: 2-3 giorni
**Risk**: Basso
**Impact**: Alto (elimina memory leak)

Fase 3: Dispatcher Lineare (Medium-term)
-----------------------------------------

1. Implementare ``_validate_request()`` pura
2. Refactor ``dispatcher()`` per flusso lineare
3. Eliminare chiamate multiple a ``handle_path_list``
4. Test completi

**Effort**: 1 settimana
**Risk**: Medio (richiede testing estensivo)
**Impact**: Alto (performance + maintainability)

Fase 4: Separation of Concerns (Long-term)
-------------------------------------------

1. Estrarre ``RequestValidator`` class
2. Estrarre ``MaintenanceManager`` class
3. Refactor ``dispatcher`` per usare componenti
4. Unit tests per ogni componente

**Effort**: 2-3 settimane
**Risk**: Medio-Alto (refactoring estensivo)
**Impact**: Molto Alto (clean architecture)

Metriche di Successo
====================

Performance
-----------

- **Prima**: 3x parsing URL per richiesta
- **Dopo**: 1x parsing URL per richiesta
- **Target**: -60% CPU time in dispatcher

Memory
------

- **Prima**: ``len(site.domains['_main_'].register.pages) > 50000``
- **Dopo**: ``len(site.domains['_main_'].register.pages) < 100``
- **Target**: Zero accumulo su ``_main_``

Code Quality
------------

- **Prima**: Property con side-effects, flusso confuso
- **Dopo**: Funzioni pure, flusso lineare
- **Target**: 100% test coverage su dispatcher

Maintenance
-----------

- **Prima**: Accesso DB per ogni richiesta HTTP
- **Dopo**: Check in-memory o file flag
- **Target**: < 1ms per maintenance check

Riferimenti
===========

- **Issue tracker**: GitHub issue #XXX
- **PR attuale**: ``feature/multidomain-workspace``
- **Documentazione fix**: :doc:`issues-roadmap`
- **Codice attuale**: ``gnrpy/gnr/web/gnrwsgisite.py`` lines 951-1138

---

**Data**: 2025-11-14
**Autore**: Analisi automatica + suggerimenti architetturali
**Status**: 📋 Proposta - Da discutere con team
