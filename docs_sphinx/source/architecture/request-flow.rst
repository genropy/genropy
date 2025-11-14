====================
Flusso di Richiesta
====================

Questo documento descrive in dettaglio il flusso completo di una richiesta HTTP attraverso il sistema Multidomain Workspace, dalla ricezione della richiesta fino all'esecuzione della query sul database.

.. contents:: In questa pagina
   :local:
   :depth: 2

Panoramica
==========

Una richiesta HTTP attraversa 6 livelli principali:

1. **Client** - Browser con cookie isolation
2. **Reverse Proxy** - Nginx → Gunicorn
3. **WSGI Site** - Estrazione dominio e setup contesto
4. **Page** - Creazione pagina con DB environment
5. **Database Layer** - Connection pool e query execution
6. **Neon DB** - Database PostgreSQL per workspace

Flusso Completo
===============

Step 1: HTTP Request
--------------------

Il client invia una richiesta HTTP:

.. code-block:: http

    GET /workspace1/sys/user HTTP/1.1
    Host: app.teamset.io
    Cookie: teamset_workspace1=<encrypted_data>

**Componenti richiesta:**

- **URL**: ``/workspace1/sys/user``
- **Domain**: ``workspace1`` (primo segmento URL)
- **Page**: ``sys/user`` (path dopo dominio)
- **Cookie**: ``teamset_workspace1`` (cookie domain-scoped)

Step 2: WSGI Dispatcher
-----------------------

File: :file:`gnrpy/gnr/web/gnrwsgisite.py`

La richiesta entra nel dispatcher WSGI:

.. code-block:: python

    def __call__(self, environ, start_response):
        return self.wsgiapp(environ, start_response)

    def dispatcher(self, environ, start_response):
        self.currentRequest = Request(environ)
        self.currentDomain = self.rootDomain  # Iniziale: '_main_'
        # ... gestione richiesta

**Azioni:**

1. Crea oggetto ``Request`` da environ WSGI
2. Inizializza ``currentDomain`` a ``'_main_'`` (default)
3. Chiama ``_dispatcher()`` per elaborazione

Step 3: Domain Extraction
--------------------------

File: :file:`gnrpy/gnr/web/gnrwsgisite.py:845-871`

Il metodo ``handle_path_list()`` estrae il dominio dall'URL:

.. code-block:: python

    def handle_path_list(self, path_info, request_kwargs=None):
        # Parse URL
        path_list = path_info.strip('/').split('/')
        # URL: "/workspace1/sys/user"
        # path_list: ['workspace1', 'sys', 'user']

        first_segment = path_list[0]  # 'workspace1'
        redirect_to = None

        # Check static routes first
        if first_segment in self.static_routes:
            return self.static_routes[first_segment].split('/'), redirect_to

        # MULTIDOMAIN LOGIC
        if self.multidomain:
            if first_segment in self.domains:
                # Domain found!
                if path_list[-1] == first_segment and not path_info.endswith('/'):
                    # Force trailing slash for consistency
                    redirect_to = f'{path_info}/'
                else:
                    # SET DOMAIN CONTEXT (thread-local)
                    self.currentDomain = first_segment

                    # MAP DOMAIN TO DBSTORE
                    if first_segment != self.rootDomain:
                        request_kwargs['base_dbstore'] = first_segment

                    # Remove domain from path
                    path_list.pop(0)
                    # Now: path_list = ['sys', 'user']

            elif first_segment not in self.storageTypes:
                # Invalid domain - mark as suspicious
                logger.debug('Suspicious request without valid domain')
                request_kwargs['_souspicious_request_'] = True

        # PROPAGATE DOMAIN TO DB ENVIRONMENT
        self.db.currentEnv['domainName'] = self.currentDomain

        return path_list, redirect_to

**Risultato:**

- ``currentDomain`` = ``'workspace1'`` (thread-local)
- ``request_kwargs['base_dbstore']`` = ``'workspace1'``
- ``db.currentEnv['domainName']`` = ``'workspace1'``
- ``path_list`` = ``['sys', 'user']`` (dominio rimosso)

Thread-Local Domain Context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il dominio è memorizzato **per-thread** per supportare concorrenza:

.. code-block:: python

    # File: gnrwsgisite.py:832-840

    def _get_currentDomain(self):
        """Returns the domain currently used in this thread"""
        return self._currentDomains.get(_thread.get_ident())

    def _set_currentDomain(self, domain):
        """Set currentDomain for this thread"""
        self._currentDomains[_thread.get_ident()] = domain

    currentDomain = property(_get_currentDomain, _set_currentDomain)

**Vantaggi:**

- Ogni thread ha il proprio ``currentDomain``
- Nessuna contaminazione tra richieste concorrenti
- Supporto nativo Gunicorn multiprocesso/multithread

Step 4: Page Creation
---------------------

File: :file:`gnrpy/gnr/web/gnrwebpage.py`

Il ResourceLoader crea un'istanza di ``GnrWebPage``:

.. code-block:: python

    # File: gnrresourceloader.py:72-89

    def __call__(self, path_list, request, response, environ=None,
                 request_kwargs=None):
        request_kwargs = request_kwargs or dict()

        # Get URL info (basepath, relpath, package)
        info = self.site.getUrlInfo(path_list, request_kwargs,
                                     default_path=self.default_path)

        # Create page class with mixins
        page_class = self.get_page_class(...)

        # INSTANTIATE PAGE - passa request_kwargs con base_dbstore
        page = page_class(
            site=self.site,
            request=request,
            response=response,
            request_kwargs=request_kwargs,  # Contiene base_dbstore='workspace1'
            ...
        )
        return page

Page Initialization
~~~~~~~~~~~~~~~~~~~

Il costruttore della pagina estrae il ``base_dbstore``:

.. code-block:: python

    # File: gnrwebpage.py:134-248

    def __init__(self, site=None, request=None, response=None,
                 request_kwargs=None, ...):

        # EXTRACT DBSTORE from request_kwargs
        self.base_dbstore = request_kwargs.pop('base_dbstore', None)
        # base_dbstore = 'workspace1'

        self.temp_dbstore = request_kwargs.pop('temp_dbstore', None)

        # Normalize dbstore
        if self.temp_dbstore is False:
            self.temp_dbstore = self.application.db.rootstore

        dbstore = self.temp_dbstore or self.base_dbstore
        self.dbstore = dbstore if dbstore != self.application.db.rootstore else None
        # self.dbstore = 'workspace1'

        # Create domain-scoped connection
        self.connection = GnrWebConnection(self, ...)

**Risultato:**

- ``page.dbstore`` = ``'workspace1'``
- ``page.currentDomain`` = ``'workspace1'`` (via site property)
- ``page.connection`` = Connessione con cookie domain-scoped

Step 5: Database Access
-----------------------

File: :file:`gnrpy/gnr/web/gnrwebpage.py:435-466`

Quando la pagina accede al database per la prima volta (lazy):

.. code-block:: python

    @property
    def db(self):
        if not getattr(self, '_db', None):
            self._db = self.application.db  # Shared instance
            self._db.clearCurrentEnv()  # Clear previous env

            # SET DATABASE ENVIRONMENT with domain context
            self._db.updateEnv(
                storename=self.dbstore,         # 'workspace1'
                currentDomain=self.currentDomain,  # 'workspace1'
                dbbranch=self._call_kwargs.get("dbbranch", None),
                workdate=self.workdate,
                locale=self.locale,
                maxdate=datetime.date.max,
                mindate=datetime.date.min,
                user=self.user,
                userTags=self.userTags,
                pagename=self.pagename,
                mainpackage=self.mainpackage,
                external_host=self.external_host
            )

            self._db.setLocale()
        return self._db

**Risultato:**

.. code-block:: python

    db.currentEnv[thread_id] = {
        'storename': 'workspace1',
        'currentDomain': 'workspace1',
        'user': 'john@workspace1',
        'locale': 'it',
        ...
    }

Step 6: Query Execution
-----------------------

File: :file:`gnrpy/gnr/sql/gnrsql.py`

Quando la pagina esegue una query:

.. code-block:: python

    # Codice pagina
    users = page.db.table('sys.user').query().fetch()

Internamente:

.. code-block:: python

    # File: gnrsql.py:562-643

    @sql_audit
    def execute(self, sql, sqlargs=None, cursor=None,
                storename=None, ...):

        # Resolve storename from environment
        if storename is False:
            storename = self.rootstore
        storename = storename or envargs.get('env_storename', self.rootstore)
        # storename = 'workspace1'

        # Execute with store context
        with self.tempEnv(storename=storename):
            cursor.execute(sql, sqlargs)

        return cursor

Connection Pool
~~~~~~~~~~~~~~~

Il metodo ``_get_store_connection()`` gestisce il connection pool:

.. code-block:: python

    # File: gnrsql.py:513-538

    def _get_store_connection(self, storename):
        thread_ident = _thread.get_ident()

        # Thread-local connection pool
        thread_connections = self._connections.setdefault(thread_ident, {})

        # Connection key: (storename, connectionName)
        connectionTuple = (storename or self.currentStorename,
                          self.currentConnectionName)
        connection = thread_connections.get(connectionTuple)

        if not connection:
            # CREATE NEW CONNECTION for this store
            connection = self.adapter.connect(storename)
            connection.storename = storename
            connection.committed = False
            connection.connectionName = connectionTuple[1]

            # CACHE connection in thread-local pool
            thread_connections[connectionTuple] = connection

        return connection

Store Parameters Resolution
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Il metodo ``get_connection_params()`` risolve i parametri di connessione:

.. code-block:: python

    # File: gnrsql.py:543-560

    def get_connection_params(self, storename=None):
        if storename == self.rootstore or not storename:
            # Main database
            return dict(host=self.host, database=self.dbname, ...)

        # GET STORE-SPECIFIC PARAMETERS
        storeattr = self.get_store_parameters(storename)
        # storeattr = dbstores['workspace1']
        # storeattr = {'database': 'workspace1'}

        if not storeattr:
            raise GnrSqlException(f'No config for {storename}')

        return dict(
            host=storeattr.get('host') or self.host,
            database=storeattr.get('database'),  # 'workspace1'
            user=storeattr.get('user') or self.user,
            password=storeattr.get('password') or self.password,
            port=storeattr.get('port') or self.port,
            implementation=storeattr.get('implementation') or self.implementation
        )

**Connessione creata:**

.. code-block:: python

    connection = psycopg2.connect(
        host='ep-xxx.neon.tech',
        database='workspace1',  # ← Database workspace1
        user='neondb_owner',
        password='...',
        port=5432
    )

Step 7: Response
----------------

Dopo l'esecuzione della query, la risposta viene costruita e inviata:

.. code-block:: http

    HTTP/1.1 200 OK
    Set-Cookie: teamset_workspace1=<data>; Path=/workspace1/; Expires=...
    Content-Type: text/html; charset=utf-8

    <!DOCTYPE html>
    <html>
      ... contenuto pagina con lista utenti da workspace1 ...
    </html>

**Cookie domain-scoped:**

- **Nome**: ``teamset_workspace1`` (unico per workspace)
- **Path**: ``/workspace1/`` (browser invia solo per questo path)
- **Expires**: Timestamp futuro

Diagramma di Sequenza
======================

.. code-block:: text

    Client          Nginx      WSGI Site     Page         Database     Neon DB
      │               │            │           │              │            │
      │─HTTP Request ─│            │           │              │            │
      │ /workspace1/  │            │           │              │            │
      │ sys/user      │            │           │              │            │
      │               │            │           │              │            │
      │               │─forward────│           │              │            │
      │               │            │           │              │            │
      │               │            │           │              │            │
      │               │    dispatcher()        │              │            │
      │               │    currentDomain =     │              │            │
      │               │    '_main_' (initial)  │              │            │
      │               │            │           │              │            │
      │               │    handle_path_list()  │              │            │
      │               │    • Parse URL         │              │            │
      │               │    • Extract domain    │              │            │
      │               │    • Set currentDomain │              │            │
      │               │      = 'workspace1'    │              │            │
      │               │    • Set base_dbstore  │              │            │
      │               │      = 'workspace1'    │              │            │
      │               │            │           │              │            │
      │               │            │           │              │            │
      │               │    resource_loader()   │              │            │
      │               │─────────────────────── │              │            │
      │               │                 create page           │            │
      │               │                   request_kwargs      │            │
      │               │                   {base_dbstore:      │            │
      │               │                    'workspace1'}      │            │
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                  __init__()           │            │
      │               │                  self.dbstore =       │            │
      │               │                  'workspace1'         │            │
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                  page.db property     │            │
      │               │                        │──updateEnv ──│            │
      │               │                        │  (storename= │            │
      │               │                        │   'workspace1')           │
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                  query execution      │            │
      │               │                        │──execute()───│            │
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                        │     _get_store_connection()
      │               │                        │     (storename=           │
      │               │                        │      'workspace1')        │
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                        │     get_connection_params()
      │               │                        │     → database:           │
      │               │                        │       'workspace1'        │
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                        │              │──connect───│
      │               │                        │              │  (database=│
      │               │                        │              │   workspace1)
      │               │                        │              │            │
      │               │                        │              │<───conn────│
      │               │                        │              │            │
      │               │                        │              │            │
      │               │                        │              │──SQL───────│
      │               │                        │              │  SELECT *  │
      │               │                        │              │  FROM      │
      │               │                        │              │  sys.user  │
      │               │                        │              │            │
      │               │                        │              │<──results──│
      │               │                        │<─results─────│            │
      │               │<─page rendered─────────│              │            │
      │<─HTTP Response│            │           │              │            │
      │ (Cookie:      │            │           │              │            │
      │  workspace1,  │            │           │              │            │
      │  Path:        │            │           │              │            │
      │  /workspace1/)│            │           │              │            │
      │               │            │           │              │            │

Punti Chiave
============

Domain Mapping
--------------

Il mapping domain → database avviene in step:

1. **URL** → ``/workspace1/sys/user``
2. **Domain extraction** → ``workspace1``
3. **base_dbstore** → ``'workspace1'``
4. **storename** → ``'workspace1'``
5. **database** → ``'workspace1'`` (NO PREFIX in teamset config)

Thread-Safety
-------------

Tre livelli di isolamento thread-local:

1. **Site**: ``_currentDomains[thread_id]`` = ``'workspace1'``
2. **DB Env**: ``_currentEnv[thread_id]`` = ``{storename: 'workspace1', ...}``
3. **DB Conn**: ``_connections[thread_id][('workspace1', 'main')]`` = connection

Cookie Isolation
----------------

Cookie isolation a due livelli:

1. **Nome**: ``teamset_workspace1`` (unico per workspace)
2. **Path**: ``/workspace1/`` (browser scoping automatico)

→ Browser invia cookie **solo** per richieste a ``/workspace1/*``

Lazy Loading
------------

Componenti lazy-loaded per performance:

- **Domain register**: Creato al primo accesso
- **DB instance**: Configurato al primo ``page.db``
- **Connection**: Creata al primo query
- **Domain from dbstores**: Auto-discovered on-demand

Vedi Anche
==========

- :doc:`components` - Componenti chiave del sistema
- :doc:`database` - Database layer in dettaglio
- :doc:`../isolation/overview` - Meccanismi di isolamento
