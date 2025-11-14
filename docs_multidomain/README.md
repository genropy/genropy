# Genropy Multidomain Workspace - Documentazione

Documentazione tecnica completa del sistema **Multidomain Workspace** per Genropy.

## Branch

- **Corrente**: `feature/multidomain-workspace`
- **Base**: `feature/refactor-dbstores-storetable`
- **Upstream**: `develop`

## Quick Start

### Avviare il sito di documentazione localmente

#### Opzione 1: Python SimpleHTTPServer (consigliato)

```bash
cd docs_multidomain
python3 -m http.server 8000
```

Poi apri il browser su: **http://localhost:8000**

#### Opzione 2: npx serve

```bash
cd docs_multidomain
npx serve
```

Poi apri il browser sull'URL indicato (solitamente http://localhost:3000)

#### Opzione 3: PHP Built-in Server

```bash
cd docs_multidomain
php -S localhost:8000
```

Poi apri il browser su: **http://localhost:8000**

## Struttura della Documentazione

- **index.html** - Overview e introduzione al Multidomain Workspace
- **architecture.html** - Schema architetturale dettagliato dei componenti
- **request-flow.html** - Flusso completo da HTTP Request a Database Query
- **isolation.html** - 6 meccanismi di isolamento (cookie, session, DB, preferences, services, thread-safety)
- **onboarding.html** - Processo di onboarding workspace e storetable
- **configuration.html** - Configurazione instanceconfig.xml e setup
- **neon-integration.html** - Integrazione con Neon DB e autoscaling
- **best-practices.html** - Pattern consigliati e anti-pattern da evitare
- **issues-future.html** - Problemi noti e roadmap future integrazioni

## Features del Sito

✅ **Responsive Design** - Funziona su mobile, tablet e desktop
✅ **Syntax Highlighting** - Code blocks con evidenziazione sintassi
✅ **Copy Code** - Bottone per copiare codice con un click
✅ **Smooth Navigation** - Menu laterale con navigazione fluida
✅ **Dark Theme** - Design dark ottimizzato per lettura
✅ **Mobile Menu** - Menu hamburger responsive per mobile

## Tecnologie

- HTML5 + CSS3 (vanilla, no framework)
- JavaScript vanilla per interattività
- [Highlight.js](https://highlightjs.org/) per syntax highlighting

## Pubblicazione

### GitHub Pages

Per pubblicare su GitHub Pages:

```bash
# Copia la cartella docs_multidomain nella root del repo
cp -r docs_multidomain ../docs

# Commit e push
git add docs/
git commit -m "Add multidomain workspace documentation"
git push
```

Poi configura GitHub Pages per servire dalla cartella `/docs` nella repository settings.

### Netlify / Vercel

Carica semplicemente la cartella `docs_multidomain` su Netlify o Vercel per deploy automatico.

## Contribuire

Per aggiungere o modificare la documentazione:

1. Modifica i file HTML nella directory principale
2. Aggiungi stili in `assets/style.css`
3. Aggiungi interattività in `assets/script.js`
4. Testa localmente con uno dei metodi sopra
5. Commit e push delle modifiche

## Struttura Files

```
docs_multidomain/
├── index.html                    # Homepage
├── architecture.html             # Architettura
├── request-flow.html            # Flusso richieste
├── isolation.html               # Isolamento
├── onboarding.html              # Onboarding
├── configuration.html           # Configurazione
├── neon-integration.html        # Neon DB
├── best-practices.html          # Best practices
├── issues-future.html           # Issues & roadmap
├── assets/
│   ├── style.css               # Stylesheet principale
│   └── script.js               # JavaScript interattività
└── README.md                    # Questo file
```

## Contatti

Per domande o suggerimenti sulla documentazione, aprire un issue nel repository Genropy.

---

**Branch**: `feature/multidomain-workspace`
**Ultima modifica**: 2025-11-14
