.. Genropy Multidomain Workspace documentation master file

====================================
Genropy Multidomain Workspace
====================================

Un'unica istanza applicativa per servire N clienti completamente isolati
========================================================================

.. image:: https://img.shields.io/badge/branch-feature%2Fmultidomain--workspace-blue
   :alt: Branch

.. image:: https://img.shields.io/badge/base-feature%2Frefactor--dbstores--storetable-lightgrey
   :alt: Base Branch

.. image:: https://img.shields.io/badge/status-in%20development-yellow
   :alt: Status

Benvenuto nella documentazione del sistema **Multidomain Workspace** di Genropy.

Questa feature trasforma la tua applicazione Genropy in una piattaforma SaaS multi-tenant, permettendo di servire centinaia di clienti indipendenti da un'unica istanza con isolamento completo di utenti, sessioni, dati e preferenze.

.. contents:: Indice
   :depth: 2
   :local:

Introduzione
============

Concetto Chiave
---------------

Il sistema Multidomain Workspace permette di:

✅ **Ridurre i costi dell'87%**: Da $1200/cliente/anno a $150/cliente/anno

✅ **Onboarding rapido**: Nuovo cliente operativo in 2-5 minuti

✅ **Isolamento completo**: Utenti, sessioni, database, preferenze, servizi separati

✅ **Scalabilità infinita**: Nessun limite al numero di workspace con autoscaling

Caso d'Uso
----------

**Scenario tipico**: Applicativo che vuoi rivendere a N clienti con:

- Configurazioni di base comuni
- Accessi e gestione utenti indipendente
- Separazione netta dei dati
- Preferenze personalizzate per cliente
- Un dominio ``_main_`` per configurazioni template

**Esempio Reale: teamset.io**

Prima (istanze separate)::

    cinema_emotion.teamset.io  → Instance A → DB A → Server A
    sky_movies.teamset.io      → Instance B → DB B → Server B
    wolves_prod.teamset.io     → Instance C → DB C → Server C

    Costi: 3 server × $1200/anno = $3600/anno
    Manutenzione: 3 aggiornamenti, 3 deploy, 3 backup

Dopo (multidomain)::

    app.teamset.io/_main_/          → Admin interface
    app.teamset.io/cinema_emotion/  → Cliente A
    app.teamset.io/sky_movies/      → Cliente B
    app.teamset.io/wolves_prod/     → Cliente C

    Costi: 1 server + Neon DB = ~$700/anno
    Manutenzione: 1 aggiornamento, 1 deploy, backup automatico

Quick Start
===========

1. Abilita Multidomain
----------------------

Nel tuo ``instanceconfig.xml``:

.. code-block:: xml

    <gnrcore_multidb pkgcode="gnrcore:multidb"
                     storetable='ts_hosting.workspace'
                     multidomain='t'
                     prefix=''/>

2. Crea Storetable Custom
--------------------------

Estendi la classe ``StoreTable``:

.. code-block:: python

    from gnrpkg.multidb.storetable import StoreTable

    class Table(StoreTable):
        def config_db(self, pkg):
            tbl = pkg.table('workspace', pkey='id',
                           name_long='Workspace',
                           caption_field='denominazione')
            self.sysFields(tbl)
            tbl.column('dbstore', size=':30', unique=True)
            tbl.column('denominazione', size=':40')

        def multidb_setStartupData_whitelist(self):
            return ['adm.user', 'adm.group', ...]

3. Crea Workspace
-----------------

Dall'interfaccia admin ``/_main_/``:

1. Inserisci nuovo record workspace
2. Click "Crea" → Attiva dbstore
3. Click "Inizializza dati" → Copia template
4. Cliente pronto! Accedi a ``/workspace_name/``

Documentazione Completa
=======================

.. toctree::
   :maxdepth: 2
   :caption: Architettura

   architecture/overview
   architecture/components
   architecture/request-flow
   architecture/database

.. toctree::
   :maxdepth: 2
   :caption: Isolamento

   isolation/overview
   isolation/cookies
   isolation/database
   isolation/preferences

.. toctree::
   :maxdepth: 2
   :caption: Setup

   setup/configuration
   setup/onboarding
   setup/neon-integration

.. toctree::
   :maxdepth: 2
   :caption: Guide

   development/best-practices
   development/patterns

.. toctree::
   :maxdepth: 1
   :caption: Problemi e Miglioramenti

   issues-roadmap
   refactoring-dispatcher

.. toctree::
   :maxdepth: 1
   :caption: Altro

   faq

Indici
======

* :ref:`genindex`
* :ref:`search`

