# Grouplet System Documentation

## Overview

A **grouplet** is a self-contained, reusable UI fragment that encapsulates a set of form fields and their presentation logic. Grouplets solve a common problem in data-intensive applications: records often have large numbers of fields that need to be organized, edited, and displayed in different contexts — inline forms, dialog editors, wizards, summary previews, and navigation panels.

Instead of duplicating field definitions across pages, a grouplet defines its fields **once** as a Python resource file and can then be rendered through multiple presentation modes:

- **Inline** — directly embedded in a form via the `Grouplet` widget
- **Dialog** — opened in a modal editor via `groupletChunk` (template preview + edit button)
- **Panel** — navigated through a tree or multibutton selector via `groupletPanel`
- **Wizard** — presented step-by-step via `groupletWizard`
- **Grid** — multiple grouplets rendered together in a CSS grid layout via **topic-as-resource**

Grouplets can be organized into **topics** (folders of related grouplets) to create hierarchical structures. The system supports permission-based visibility, template-driven previews, and automatic discovery of metadata from resource files.

**Module Location:** `resources/common/gnrcomponents/grouplet.py`
**JS Client:** `resources/common/gnrcomponents/grouplet.js`
**CSS Styles:** `resources/common/gnrcomponents/grouplet.css`
**JS Widgets:** `gnrjs/gnr_d11/js/genro_components.js` (`gnr.widgets.Grouplet`, `gnr.widgets.GroupletForm`)
**Dialog Logic:** `gnrjs/gnr_d11/js/genro_dlg.js` (`memoryDataEditor`, `documentDataEditor`, `recordDataEditor`)

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Resource File System                       │
│                                                                 │
│  resources/tables/{table}/grouplets/                            │
│  ├── anagrafica.py              (single grouplet)               │
│  ├── codici.py                  (single grouplet with template) │
│  └── technical/                 (topic = folder)                │
│      ├── __info__.py            (topic metadata + template)     │
│      ├── system.py              (child grouplet)                │
│      ├── error.py               (child grouplet)                │
│      └── reproduction.py        (child grouplet)                │
│                                                                 │
│  resources/grouplets/           (non-table grouplets)           │
│  └── app/                                                       │
│      ├── __info__.py                                            │
│      └── android_qrcode.py                                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼ (discovered by)
┌─────────────────────────────────────────────────────────────────┐
│              GroupletHandler (Python Component)                  │
│                                                                 │
│  gr_getGroupletMenu()   → Builds Bag menu from file system      │
│  gr_loadGrouplet()      → RPC: loads single grouplet or topic   │
│  gr_getTemplatePars()   → Reads template from __info__.py       │
│  gr_groupletChunk()     → Template preview + edit button        │
│  gr_groupletPanel()     → Tree/multibutton navigation           │
│  gr_groupletWizard()    → Step-by-step form wizard              │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼ (renders via)
┌─────────────────────────────────────────────────────────────────┐
│                    JS Widgets (Client)                           │
│                                                                 │
│  Grouplet         → Remote widget, calls gr_loadGrouplet RPC    │
│  GroupletForm     → BoxForm wrapper with store (memory/record)  │
│  gnr_grouplet.*   → Wizard navigation, cell toggle, panel       │
│  genro.dlg.*      → Dialog editors (memory, document, record)   │
└─────────────────────────────────────────────────────────────────┘
```

### Resource Resolution Order

When a grouplet is requested for a table (e.g., `test.myticket`), the system searches resources in this order:

1. **Package-specific:** `packages/test/resources/tables/myticket/grouplets/`
2. **Cross-package (custom):** `resources/tables/_packages/test/myticket/grouplets/`

For non-table grouplets (no `table` parameter), it searches:

3. **Page-level resources:** `resources/grouplets/`

Resources found later in the chain override earlier ones, allowing customization.

## Resource Structure

### Single Grouplet

A grouplet is a Python file containing an `info` dict and a `Grouplet` class:

```python
# resources/tables/myticket/grouplets/technical/system.py

from gnr.web.gnrbaseclasses import BaseComponent

info = dict(
    caption='System',           # Display name in menus and headers
    code='system',              # Unique identifier (defaults to filename)
    priority=1,                 # Sort order (lower = higher priority)
    tags=None,                  # Permission tags (e.g., 'admin,support')
    permissions=None,           # Table-level permissions (e.g., 'readOnly')
    template=None,              # HTML template for groupletChunk preview
    template_virtual_columns=None  # Comma-separated virtual columns for template
)


class Grouplet(BaseComponent):
    def grouplet_main(self, pane, **kwargs):
        fb = pane.formlet(cols=2, border_spacing='3px')
        fb.textbox(value='^.operating_system', lbl='Operating System',
                   colspan=2, width='100%')
        fb.textbox(value='^.software_version', lbl='Software Version')
        fb.textbox(value='^.browser', lbl='Browser')
```

**Key points:**

- The class **must** be named `Grouplet` (or specify a custom class via `resource_name:ClassName` syntax)
- The entry point method is `grouplet_main` by default (customizable via `handlername`)
- Field values use relative paths (`^.field_name`) — the datapath is set by the calling widget
- When bound to a table, `fb.field(...)` can be used for automatic field configuration

### Topic (Folder of Grouplets)

A **topic** is a directory containing multiple related grouplets and an optional `__info__.py`:

```
grouplets/technical/
├── __info__.py         # Topic-level metadata
├── system.py           # Grouplet: System Info
├── error.py            # Grouplet: Error Details
└── reproduction.py     # Grouplet: Reproduction Steps
```

The `__info__.py` defines topic metadata:

```python
# grouplets/technical/__info__.py

info = dict(
    caption='Technical',    # Topic display name
    priority=1,             # Sort order among topics
    template='<div>${<span>OS: <b>$operating_system</b></span>}'
             '${<span> | Error: $error_code</span>}</div>'
)
```

The `template` in `__info__.py` serves two purposes:
1. It is used by `groupletChunk` for the summary preview when the topic is the resource
2. It is auto-discovered — no need to pass `template=` explicitly to `groupletChunk`

### Nested Topics

Topics can be nested to create deeper hierarchies:

```
grouplets/
├── territorio/                    # Parent topic
│   ├── __info__.py
│   ├── altimetria.py              # Sub-grouplet
│   └── superficie.py             # Sub-grouplet
├── codici.py                      # Standalone grouplet (sibling)
└── anagrafica.py                  # Standalone grouplet (sibling)
```

Nested resources are referenced with slash-separated paths: `territorio/altimetria`.

### Non-Table Grouplets

Grouplets do not require a table binding. App-level grouplets live under `resources/grouplets/`:

```
resources/grouplets/
└── app/
    ├── __info__.py
    ├── android_qrcode.py
    ├── ios_qrcode.py
    └── connection_qrcode.py
```

Use them by omitting the `table` parameter:

```python
pane.grouplet(resource='app/android_qrcode', value='^.settings')
```

## The `info` Dict Reference

Every grouplet resource file exposes a module-level `info` dict:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `caption` | `str` | filename | Display name shown in menus, headers, wizard steps |
| `code` | `str` | filename | Unique identifier within its topic/scope |
| `priority` | `int` | `0` | Sort order (lower values appear first) |
| `tags` | `str` | `None` | Comma-separated permission tags (e.g., `'admin,support'`). If set, the grouplet is hidden from users without matching tags |
| `permissions` | `str` | `None` | Table-level permission check (e.g., `'readOnly'`). Requires `table` to be set |
| `template` | `str` | `None` | HTML template string for `groupletChunk` preview (see Template Syntax below) |
| `template_virtual_columns` | `str` | `None` | Comma-separated virtual column names needed by the template |

### Dynamic Visibility

In addition to `tags` and `permissions`, a resource file can define an `is_enabled` function:

```python
info = dict(caption='Admin Panel', code='admin', priority=99)

def is_enabled(page):
    """Only show this grouplet if the user is an administrator."""
    return 'admin' in page.userTags
```

If `is_enabled` returns `False`, the grouplet is excluded from menus and cannot be loaded.

## Widgets and Presentation Modes

### 1. `Grouplet` Widget — Inline Rendering

The base widget that loads a grouplet via RPC and renders it inline.

**Python (server-side):**

```python
pane.grouplet(
    resource='technical/system',     # Resource path (required unless handler is set)
    table='test.myticket',           # Table binding (optional)
    value='^.record.extra_data',     # Data path for field values
    handler=self.my_method,          # Alternative: use a handler method instead of resource
    showOnFormLoaded=True            # Delay loading until parent form is loaded
)
```

**How it works:**
1. The JS `Grouplet` widget creates a remote contentPane
2. It calls `gr_loadGrouplet` RPC on the server
3. The server mixes in the resource class and calls `grouplet_main`
4. The resulting DOM is returned and rendered client-side

**Handler-based grouplets** do not use resource files — they call a `@public_method` directly:

```python
pane.grouplet(handler=self.grp_address, value='^.address_data')

@public_method
def grp_address(self, pane, **kwargs):
    fb = pane.formlet(cols=2, border_spacing='6px')
    fb.textbox(value='^.street', lbl='Street', colspan=2, width='100%')
    fb.textbox(value='^.city', lbl='City')
    fb.textbox(value='^.zip', lbl='ZIP')
```

### 2. `GroupletForm` Widget — Form with Store

Wraps a grouplet inside a `BoxForm` with data store capabilities (memory, record, or document).

```python
# In-memory form (data lives in a Bag, no DB)
pane.groupletform(
    handler=self.grp_address,
    value='^.address_data',
    formId='address_form',
    loadOnBuilt=True            # Load immediately on widget build
)

# Record-backed form (data from DB table)
pane.groupletform(
    resource='anagrafica',
    table='glbl.comune',
    formId='anagrafica_form',
    store_handler='record',     # Use record store (DB)
    storeType='Item'            # Single-record store
)
```

**Parameters:**

| Parameter | Description |
|-----------|-------------|
| `resource` | Resource path (grouplet file or topic) |
| `handler` | Alternative: handler method reference |
| `table` | Table binding |
| `value` | Data path (used as `store_locationpath` for memory stores) |
| `formId` | Form identifier (for `genro.formById()`) |
| `loadOnBuilt` | Auto-load when widget is built |
| `startKey` | Initial record key to load |
| `store_handler` | Store type: `'memory'` (default), `'record'`, `'document'` |
| `storeType` | Store collection type: `'Item'`, `'SubForm'`, `'Collection'` |
| `form_modalForm` | Enable modal form mode (used by wizard) |
| `grouplet_*` | Any `grouplet_` prefixed parameter is forwarded to the inner `Grouplet` widget |

**Store types explained:**

- **memory + SubForm**: Copies fields from the parent form; save writes them back. Ideal for editing a subset of a larger record
- **memory + Item**: Reads/writes from a Bag at `value` path. Ideal for structured sub-data (e.g., `extra_data` JSON column)
- **record + Item**: Full DB record load/save via `app.getRecord` / `app.saveRecord`
- **document + Item**: Document-based load/save for file-backed data

### 3. `groupletChunk` — Template Preview with Edit Dialog

Displays a read-only template preview of the data with a pencil button that opens a `memoryDataEditor` dialog for editing.

```python
pane.groupletChunk(
    value='^#FORM.record.extra_data',
    name='edit_technical',                 # Unique dialog name
    resource='technical',                  # Resource or topic
    table='test.myticket',                 # Table binding
    title='Technical Details',             # Dialog title

    # Template (optional if __info__.py defines it)
    template='<div>${<span>OS: $operating_system</span>}</div>',
    virtual_columns='zona_altimetrica',    # Virtual columns for template

    # Grid parameters (when resource is a topic)
    grid_columns=2,                        # CSS grid columns in dialog
    grid_collapsible=True,                 # Collapsible cells
    grid_gap='16px',                       # Grid gap

    # Box styling
    box_padding='5px',
    box_background='#f9f9f9',
    box_border_radius='4px'
)
```

**Template auto-discovery:** When `resource` is set but `template` is not, `groupletChunk` automatically reads the template and `template_virtual_columns` from the resource's `__info__.py`. This means:

```python
# These two are equivalent:
pane.groupletChunk(value='^.data', resource='codici', table='glbl.comune',
                   name='edit_codici',
                   template='<div><b>$sigla_provincia</b> - $codice_comune</div>')

pane.groupletChunk(value='^.data', resource='codici', table='glbl.comune',
                   name='edit_codici')  # template auto-discovered from codici.py's info dict
```

### 4. `groupletPanel` — Navigation Panel

A panel with a navigation sidebar (tree or multibutton) and a content area that loads the selected grouplet.

**Tree mode** (when no `topic` is specified — shows the full hierarchy):

```python
pane.groupletPanel(
    table='test.myticket',
    value='^.record.extra_data',
    frameCode='ticket_panel',
    height='400px'
)
```

This renders:
```
┌──────────────────┬───────────────────────────────┐
│ [Search...]      │ Selected Grouplet Caption     │
├──────────────────┤───────────────────────────────│
│ ▸ Technical      │                               │
│   ├ System       │   [Grouplet form content      │
│   ├ Error        │    loaded dynamically]         │
│   └ Reproduction │                               │
│ ▸ Commercial     │                               │
│   ├ Company      │                               │
│   └ Contract     │                               │
│ ▸ Administrative │                               │
└──────────────────┴───────────────────────────────┘
```

**Multibutton mode** (when `topic` is specified — flat list within a topic):

```python
pane.groupletPanel(
    table='test.myticket',
    topic='technical',              # Filter to a single topic
    value='^.record.extra_data',
    frameCode='tech_panel'
)
```

This renders:
```
┌─────────────────────────────────────────┐
│  [ System ]  [ Error ]  [ Reproduction ]│
├─────────────────────────────────────────┤
│                                         │
│  [Selected grouplet form content]       │
│                                         │
└─────────────────────────────────────────┘
```

The multibutton mode is mobile-friendly and ideal for a small number of grouplets within a topic.

### 5. `groupletWizard` — Step-by-Step Wizard

Presents each grouplet in a topic as a sequential step with a visual stepper bar.

```python
pane.groupletWizard(
    table='test.booking',
    topic='booking',                    # Topic whose grouplets become steps
    value='^.record.extra_data',
    frameCode='booking_wizard',
    completeLabel='Confirm Booking',    # Label for the final step button
    saveMainFormOnComplete=True,        # Save the parent form when wizard completes
    height='400px'
)
```

This renders:
```
┌─────────────────────────────────────────────────────┐
│      (1)───────(2)───────(3)───────(4)              │
│     Stay      Guest    Services   Payment           │
├─────────────────────────────────────────────────────┤
│                                                     │
│   [Current step's grouplet form]                    │
│                                                     │
├─────────────────────────────────────────────────────┤
│                                    Guest →          │
└─────────────────────────────────────────────────────┘
```

**Behavior:**
- Each step uses a `GroupletForm` with memory store and `modalForm=True`
- Clicking "Next" validates the current step, saves it, and advances
- Completed steps show a checkmark and are clickable for back-navigation
- The last step shows `completeLabel` instead of the next step name
- On completion, publishes `{frameCode}_complete` event
- If `saveMainFormOnComplete=True`, the parent form is saved on completion

**Published events:**
- `{frameCode}_step_complete` — fired after each step, with `{step_code: ...}`
- `{frameCode}_complete` — fired when the last step is confirmed

## Topic-as-Resource Grid

When a topic folder name is passed as the `resource` to the `Grouplet` widget, all child grouplets are rendered together in a CSS grid layout instead of loading a single grouplet.

### Basic Usage

```python
# Single column (default)
pane.grouplet(
    resource='technical',
    table='test.myticket',
    value='^.record.extra_data'
)

# Two-column grid
pane.grouplet(
    resource='technical',
    table='test.myticket',
    value='^.record.extra_data',
    remote_grid_columns=2
)
```

### Grid Parameters

All grid parameters use the `remote_grid_` prefix (or `grid_` inside `groupletChunk`):

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `grid_columns` | `int` | `1` | Number of CSS grid columns |
| `grid_template_columns` | `str` | auto | Custom `grid-template-columns` CSS value (e.g., `'1fr 2fr'`, `'200px 1fr 1fr'`) |
| `grid_gap` | `str` | `'10px'` | Gap between grid cells |
| `grid_collapsible` | `bool\|str` | `False` | Enable collapsible cells. Set to `'closed'` to start collapsed |
| `grid_direction` | `str` | auto | Grid flow direction: `'rows'` or `'columns'`. Defaults to `'columns'` when `columns > 1`, `'rows'` otherwise |

### Collapsible Cells

When `grid_collapsible` is truthy, each cell gets a clickable header that toggles content visibility:

```python
# Start expanded (click to collapse)
pane.grouplet(resource='technical', table='test.myticket',
              value='^.extra_data',
              remote_grid_collapsible=True)

# Start collapsed (click to expand)
pane.grouplet(resource='technical', table='test.myticket',
              value='^.extra_data',
              remote_grid_collapsible='closed')
```

The collapse/expand animation uses CSS `max-height` transitions for smooth visual feedback.

### Column Direction

With `grid_direction='columns'` (default for multi-column grids), items fill column-by-column:

```
columns=2, 3 items:          columns=2, 3 items (direction='rows'):
┌──────────┬──────────┐      ┌──────────┬──────────┐
│ System   │ Reprod.  │      │ System   │ Error    │
├──────────┤          │      ├──────────┼──────────┤
│ Error    │          │      │ Reprod.  │          │
└──────────┴──────────┘      └──────────┴──────────┘
```

### Using Topic Grid Inside groupletChunk

A `groupletChunk` can open a dialog that renders a topic grid:

```python
pane.groupletChunk(
    value='^#FORM.record.extra_data',
    name='edit_commercial',
    resource='commercial',              # Topic folder
    table='test.myticket',
    title='Commercial Details',
    grid_columns=2,                     # Dialog shows 2-column grid
    grid_collapsible=True
)
```

## Template Syntax

Templates are HTML strings with field interpolation, used by `groupletChunk` for preview display.

### Field Interpolation

Use `$field_name` to insert a field value:

```html
<div><b>$company_name</b> — $industry</div>
```

### Conditional Blocks

Use `${<tag>content</tag>}` to conditionally render content only if the interpolated fields have values:

```html
<div>
    ${<span>OS: <b>$operating_system</b></span>}
    ${<span> | Version: $software_version</span>}
    ${<span> | Browser: $browser</span>}
</div>
```

If `software_version` is empty, the entire `<span> | Version: ...</span>` block is omitted.

### Virtual Columns

When a template references computed or related fields not present in the base record, declare them as `template_virtual_columns`:

```python
info = dict(
    caption='Territorio',
    template='<div>Zona: $zona_altimetrica | Alt. $altitudine m</div>',
    template_virtual_columns='zona_altimetrica,altitudine'
)
```

The `groupletChunk` widget adds a `_virtual_columns` attribute that ensures these columns are loaded with the record.

## Dialog Editors

The `groupletChunk` button opens a `memoryDataEditor` by default, but the dialog system supports three editor types:

### `memoryDataEditor`

Used by `groupletChunk`. Opens a `GroupletForm` with `memory` store that reads fields from the parent form and writes them back on save.

```javascript
genro.dlg.memoryDataEditor('editor_name', {
    resource: 'technical',
    table: 'test.myticket',
    value: '.extra_data',
    title: 'Edit Technical Details'
}, sourceNode);
```

### `documentDataEditor`

Opens a `GroupletForm` with `document` store for editing file-backed data.

```javascript
genro.dlg.documentDataEditor('doc_editor', {
    resource: 'my_resource',
    path: '/path/to/document',
    title: 'Edit Document'
}, sourceNode);
```

### `recordDataEditor`

Opens a `GroupletForm` with `record` store for editing a DB record directly.

```javascript
genro.dlg.recordDataEditor('record_editor', {
    resource: 'anagrafica',
    table: 'glbl.comune',
    pkey: 'some_pkey',
    title: 'Edit Record'
}, sourceNode);
```

All three editors share the same dialog infrastructure (`_groupletForm`), with Confirm/Cancel buttons and auto-sizing.

## Menu System

`gr_getGroupletMenu` builds a `Bag` that represents the grouplet hierarchy discovered from the file system.

### Usage

```python
# Full menu for a table
menu = self.gr_getGroupletMenu(table='test.myticket')

# Filtered by topic
menu = self.gr_getGroupletMenu(table='test.myticket', topic='technical')

# Non-table grouplets
menu = self.gr_getGroupletMenu(topic='app')
```

### Bag Structure

For a table with topics, the returned Bag looks like:

```
technical/              (topic node with children)
  ├── system            (grouplet leaf: resource='technical/system')
  ├── error             (grouplet leaf: resource='technical/error')
  └── reproduction      (grouplet leaf: resource='technical/reproduction')
commercial/
  ├── company
  ├── contract
  └── offer
anagrafica              (standalone grouplet: resource='anagrafica')
codici                  (standalone grouplet: resource='codici')
```

Each node has attributes:
- **Topic nodes:** `caption`, `topic`, `priority`
- **Grouplet leaves:** `caption`, `code`, `priority`, `resource`, `grouplet_caption`, `topic_caption`, `topic`

### Using the Menu Directly

You can use the menu Bag to build custom navigation:

```python
# Server-side: expose menu via RPC
left.dataRpc('.grouplets_menu', self.gr_getGroupletMenu,
             table='glbl.comune', _onStart=True)

# Client-side: render as a tree
left.tree(storepath='.grouplets_menu',
          hideValues=True,
          labelAttribute='caption',
          connect_onClick="""
              if($2.item.attr.resource){
                  SET .selected_resource = $2.item.attr.resource;
              }
          """)

# Content area: load selected grouplet
right.grouplet(resource='^.selected_resource',
               table='glbl.comune',
               value='^.record')
```

### Addrow Menu

`gr_groupletAddrowMenu` transforms the grouplet menu into a format suitable for grid "add row" buttons, where each menu item sets a default field value:

```python
menu = self.gr_groupletAddrowMenu(table='test.myticket', field='ticket_type')
```

## Putting It All Together: Complete Examples

### Example 1: Ticket System with Typed Extra Data

A ticket has a `ticket_type` field and an `extra_data` column (dtype='X') that stores structured data. Different ticket types show different grouplets.

**Table model:**

```python
class Table(object):
    def config_db(self, pkg):
        tbl = pkg.table('myticket', name_long='Ticket')
        self.sysFields(tbl)
        tbl.column('subject', name_long='Subject')
        tbl.column('ticket_type', name_long='Type',
                    values='technical:Technical,commercial:Commercial,administrative:Administrative')
        tbl.column('extra_data', dtype='X', name_long='Extra Data')
```

**Form resource (th_myticket.py):**

```python
class Form(BaseComponent):
    def th_form(self, form):
        bc = form.center.borderContainer()
        top = bc.contentPane(region='top', height='80px', datapath='.record')
        fb = top.formlet(cols=2, table='test.myticket')
        fb.field('subject', colspan=2, width='100%')
        fb.field('ticket_type', tag='filteringSelect')

        bc.contentPane(region='center').groupletPanel(
            table='test.myticket',
            value='^.record.extra_data')
```

**Grouplet resources:**

```
resources/tables/myticket/grouplets/
├── technical/
│   ├── __info__.py     → info = dict(caption='Technical', priority=1)
│   ├── system.py       → System info fields
│   ├── error.py        → Error details fields
│   └── reproduction.py → Reproduction steps fields
├── commercial/
│   ├── __info__.py     → info = dict(caption='Commercial', priority=2)
│   ├── company.py      → Company fields
│   ├── contract.py     → Contract fields
│   └── offer.py        → Offer fields
└── administrative/
    ├── __info__.py     → info = dict(caption='Administrative', priority=3)
    ├── billing.py      → Billing fields
    └── licenses.py     → License fields
```

### Example 2: Booking Wizard

A hotel booking uses a wizard to collect data step by step.

**Form resource:**

```python
class Form(BaseComponent):
    def th_form(self, form):
        bc = form.center.borderContainer()
        bc.contentPane(region='center').groupletWizard(
            table='test.booking',
            topic='booking',
            value='^.record',
            completeLabel='Confirm Booking',
            saveMainFormOnComplete=True)
```

**Grouplet resources (sorted by priority = wizard step order):**

```
resources/tables/booking/grouplets/booking/
├── __info__.py  → info = dict(caption='Booking', priority=1)
├── stay.py      → priority=1: Check-in, Check-out, Room Type, Guests
├── guest.py     → priority=2: Guest Name, Email, Phone, Documents
├── services.py  → priority=3: Breakfast, Parking, Spa, Notes
└── payment.py   → priority=4: Payment Method, Card Holder, Amount
```

### Example 3: Prospect Form with Collapsible Topic Grids

A prospect record has multiple data sections shown as collapsible grids.

**Form resource:**

```python
class FormGrid(BaseComponent):
    def th_form(self, form):
        bc = form.center.borderContainer(datapath='.record')
        top = bc.contentPane(region='top', height='120px')
        fb = top.formlet(cols=3, table='test.myprospect')
        fb.field('company_name', colspan=3, width='100%')
        fb.field('contact_name')
        fb.field('contact_email')
        fb.field('contact_phone')

        tc = bc.tabContainer(region='center')
        for topic_name, topic_label in [('company', 'Company'),
                                         ('needs', 'Needs'),
                                         ('budget', 'Budget')]:
            tc.contentPane(title=topic_label, overflow='auto').grouplet(
                resource=topic_name,
                table='test.myprospect',
                value='^.extra_data',
                remote_grid_collapsible='closed',
                remote_grid_columns=2)
```

### Example 4: groupletChunk in a Form

Show a compact preview of extra data with an edit button:

```python
class Form(BaseComponent):
    def th_form(self, form):
        center = form.center.contentPane(padding='10px', datapath='.record')
        fb = center.formlet(cols=2, table='glbl.comune')
        fb.field('denominazione', colspan=2, width='100%')
        fb.field('sigla_provincia')
        fb.field('codice_comune')

        # Preview + edit button for territorio data
        chunk_pane = fb.div(colspan=2, width='100%', lbl='Territorio',
                            height='60px')
        chunk_pane.groupletChunk(
            value='^#FORM.record',
            name='edit_territorio',
            resource='territorio',
            table='glbl.comune',
            title='Edit Territorio')
        # Template is auto-discovered from territorio/__info__.py
```

## CSS Classes Reference

The grouplet system uses these CSS classes for styling:

### Topic Grid
| Class | Description |
|-------|-------------|
| `grouplet_topic_grid` | Grid container |
| `grouplet_topic_grid_columns` | Added when `direction='columns'` (uses `grid-auto-flow: column`) |
| `grouplet_topic_cell` | Individual cell wrapper |
| `grouplet_topic_cell_caption` | Cell header (clickable when collapsible) |
| `grouplet_topic_cell_content` | Cell content area (animated on collapse) |
| `grouplet_topic_toggle` | Collapse/expand arrow indicator |

### Panel
| Class | Description |
|-------|-------------|
| `grouplet_panel_tree` | Tree sidebar container |
| `grouplet_panel_searchbar` | Search bar above tree |
| `grouplet_panel_title_bar` | Title bar in content area |
| `grouplet_panel_title` | Title text |
| `grouplet_tree` | Tree widget styling |

### Wizard
| Class | Description |
|-------|-------------|
| `wizard_stepper_bar` | Stepper container |
| `wizard_stepper` | Stepper flex layout |
| `wizard_step` | Individual step (has `.active`, `.completed`, `.pending` modifiers) |
| `wizard_circle` | Step number circle |
| `wizard_caption` | Step label text |
| `wizard_connector` | Line between steps (has `.completed` modifier) |
| `wizard_bottom_bar` | Bottom navigation bar |
| `wizard_next_btn` | Next/Complete button |

### Chunk
| Class | Description |
|-------|-------------|
| `grouplet_chunk_box` | Default class for the chunk container |

## Component Requirement

To use grouplets in a webpage, include the `GroupletHandler` component:

```python
class GnrCustomWebPage(object):
    py_requires = """gnrcomponents/grouplet:GroupletHandler"""
```

The component automatically includes `grouplet.css` and `grouplet.js` via `css_requires` and `js_requires`.

For table handler pages that use `dialogTableHandler`, include it in the form resource's `py_requires` or in the page itself.
