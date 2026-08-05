# Giojo Lab — Ambiente di Test GenroPy + Giojo

## Panoramica

Ambiente dedicato per testare l'integrazione tra GenroPy e i sorgenti JavaScript di Giojo.
Directory: `/Users/gporcari/Sviluppo/giojo/giojo_lab/`
Venv: `.giojo_venv` (prompt: `giojo-lab`)

## Struttura

```
giojo/giojo_lab/
├── .giojo_venv/                    # Virtual environment Python (prompt: giojo-lab)
│   ├── bin/activate                # Attivazione venv
│   └── etc/gnr/
│       └── environment.xml         # Config GenroPy (auto-rilevata dal venv)
├── environment.xml                 # Copia di riferimento
├── dojo_libs/
│   └── giojo/
│       ├── dojo     -> giojo/src   # Symlink ai sorgenti Giojo
│       └── dojo_src -> giojo/src   # Symlink ai sorgenti Giojo
├── gnrjs/
│   └── gnr_d11 -> .../genropy/gnrjs/gnr_d11   # Symlink al JS GenroPy originale
├── projects/
├── packages/
├── resources/
├── webtools/
├── data/
└── sites/
```

## Come Funziona

### Meccanismo di rilevamento automatico

GenroPy (`gnr.core.gnrconfig.gnrConfigPath()`) cerca `environment.xml` in quest'ordine:

1. `$GENRO_GNRFOLDER` (variabile d'ambiente)
2. `$VIRTUAL_ENV/etc/gnr/` (se in un virtualenv)
3. `~/.gnr/`
4. `/etc/gnr/`

Attivando il venv, GenroPy trova automaticamente il nostro `environment.xml`
senza toccare la configurazione globale `~/.gnr/`.

### Mapping dei path JS

L'`environment.xml` definisce:

- `static.js.dojo_11` -> `giojo_lab/dojo_libs/giojo/`
  - Contiene `dojo_src/` e `dojo/`, entrambi symlink a `giojo/src/`
  - Struttura interna: `{dojo, dijit, dojox}/` — compatibile con Dojo 1.1
- `static.js.gnr_11` -> `giojo_lab/gnrjs/gnr_d11/`
  - Symlink al codice JavaScript GenroPy originale (non modificato)

### Path delle risorse GenroPy

Tutti i path non-JS puntano al repository GenroPy originale:

- `gnrhome` -> `/Users/gporcari/Sviluppo/Genropy/genropy`
- `projects` -> `.../genropy/projects`
- `resources` -> `.../genropy/resources`
- `webtools` -> `.../genropy/webtools`

## Utilizzo

### Attivazione

```bash
source /Users/gporcari/Sviluppo/giojo/giojo_lab/.giojo_venv/bin/activate
```

Il prompt diventa `(giojo-lab)` per distinguerlo dall'ambiente GenroPy principale.

### Verifica configurazione

```bash
python3 -c "
from gnr.core.gnrconfig import gnrConfigPath, getGnrConfig
config = getGnrConfig()
print(f'Config: {gnrConfigPath()}')
print(f'Dojo:   {config[\"gnr.environment_xml.static.js.dojo_11?path\"]}')
print(f'GnrJS:  {config[\"gnr.environment_xml.static.js.gnr_11?path\"]}')
"
```

### Flusso dei file JS

Quando GenroPy serve una pagina:

1. `gnrwsgisite.find_gnrjs_and_dojo()` legge `environment.xml`
2. `dojo_path['11']` = `.../dojo_libs/giojo/`
3. Se `dojo_source=True` -> carica da `dojo_src/dojo/dojo.js` (= `giojo/src/dojo/dojo.js`)
4. Se `dojo_source=False` -> carica da `dojo/dojo/dojo.js` (= stessa cosa, per ora)
5. `dojo.js` bootstrap carica `dojo._base` che include `dojo.giojo` (le nostre estensioni)

## Dipendenze

- **GenroPy**: installato in editable mode da `/Users/gporcari/Sviluppo/Genropy/genropy/gnrpy/`
- **Python**: 3.12.9 nel venv
- **Giojo JS**: sorgenti in `/Users/gporcari/Sviluppo/giojo/src/`

## Note

- Le modifiche ai file in `giojo/src/` sono immediatamente visibili (symlink diretti)
- Il daemon GenroPy usa porta 41414 (diversa dalla 40404 dell'ambiente principale)
- Non e' necessario un database per testare il caricamento JS nel browser
- Per un test completo serve creare un sito/progetto GenroPy nella directory `sites/`
