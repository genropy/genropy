.. _recordpicker:

recordPicker
============

``recordPicker`` searches records and displays matching template cards or rich
rows. It uses ordinary DOM elements without a grid or a dbSelect widget.
Database searches reuse ``app.dbSelect``. Clicking a candidate immediately
updates the bound checked identifiers. Confirmation belongs to the host page,
wizard or dialog; the component has no confirmation, cancellation or draft state.

Requirement::

    py_requires = 'gnrcomponents/recordpicker/recordpicker:RecordPicker'

Database source
---------------

The component can be placed inside a wizard step or an ordinary pane::

    pane.recordPicker(
        checkedId='^.province', table='glbl.provincia',
        columns='$nome,$sigla', hiddenColumns='$nome,$sigla,$regione',
        template='<strong>$nome</strong><div>$sigla · $regione</div>',
        selectedRecord='^.province_record',
        selectedCaption='^.province_caption')

``checkedId`` must be a reactive data path. Single selection writes a record key
as text, or ``None`` when cleared. ``multiSelect=True`` writes comma-separated
keys, consistently with the framework's checkedId controls; identifiers must
not contain commas. Selection order is preserved across searches.

Optional ``selectedRecord`` receives a record Bag in single mode, or a Bag of
record Bags with ``_pkey`` node attributes in multiple mode.
``selectedCaption`` receives the caption, or comma-separated captions.
These paths update immediately, before ``checkedId``. With database preselection,
record details update when hydration completes. Unknown or excluded identifiers
remain checked and removable, but are absent from ``selectedRecord``.

Bag source
----------

Use ``storepath`` instead of ``table`` for a reactive source Bag::

    provinces = self.db.table('glbl.provincia').query(
        columns='$nome,$sigla,$regione').selection().output('selection', caption=True)
    pane.data('.province_store', provinces)
    pane.recordPicker(checkedId='^.provinces', storepath='.province_store',
                      cols=3, boxHeight='240px',
                      columns='nome,sigla,regione', multiSelect=True,
                      template='<strong>$nome</strong><div>$sigla</div>')

Each source node can contain record attributes or a record Bag. ``identifier``
defaults to ``_pkey``; ``captionField`` defaults to ``caption``. Both can be changed
for arbitrary application Bags. ``columns`` lists searchable fields, defaulting
to the caption field. Store changes refresh the results; filtering does not remove
checked identifiers. Source records are not mutated by checking them: selection
is written to the bound output paths in the client datastore.

Presentation and templates
--------------------------

* ``layout='cards'`` uses responsive columns; ``layout='list'`` uses rich rows.
* ``cols`` fixes the number of card columns on desktop. Omit it for automatic
  columns. Compact screens and list layout use one column. This is independent
  from ``columns``, which specifies searchable record fields.
* ``boxHeight`` reserves a fixed results viewport below the search input. Accepts
  a CSS length such as ``'240px'`` or a number in pixels. Candidates, preview,
  status and optional selected summary share this space and scroll internally,
  so content below the component stays in place as results and checks change.
* ``emptyMessage`` defaults to ``'!!No items'`` (``Nessun elemento`` in Italian).
  The message is centered in the empty results area. It is visible before typing
  when ``boxHeight`` is set, and after a search with no results. Pass another
  localization-marked string to customize it, or ``''`` for no message.
* Single selection highlights the selected candidate, with no radio by default.
  ``showRadio=True`` adds a native radio indicator. ``multiSelect=True`` uses
  native checkboxes. Keyboard activation follows the native controls.
* ``showSelected`` controls the removable selected-record chips and count. It defaults
  to ``False`` for single selection and ``True`` for multiple selection. Chips use
  the theme's tonal colors and pill radius. Set it explicitly to override the default.
* ``preview=True`` reserves a separate pane beside the results, even before selection.
  Candidates and preview scroll independently; scrolling candidates never moves the preview. Clicking selects
  and previews in one action. Multiple selection previews only the latest checked
  record; removing it falls back to the most recently remaining checked record.
* ``preview_template`` customizes the preview; otherwise it uses the candidate template.
* ``template_resource`` and ``preview_resource`` accept ``loadTemplate`` addresses,
  such as ``pkg.table:template_name`` or a package resource path. Compiled XML and
  HTML resource content are supported. Inline and resource forms of the same
  template are mutually exclusive.
* Templates use the framework's ``dataTemplate`` renderer and ``$field`` syntax.
  Candidate templates contain display content, without nested interactive controls.
  Include database template fields in ``hiddenColumns`` or ``auxColumns``.

Search and constraints
----------------------

An empty search displays no candidates and makes no candidate query. A fixed
results box still displays its empty-state message. Typing
shows only matching records. Clearing the search hides the candidates again;
checked identifiers and their record details remain available. An empty selection
has no selected-record summary; the reserved preview pane displays a localized prompt.

Database searches use ``columns``, ``auxColumns``, ``hiddenColumns`` and
``rowcaption`` as in dbSelect. ``limit`` defaults to 30 results; one extra record
is requested to detect truncation. ``delay`` defaults to 250ms. Hydration loads
only previously checked keys and respects the current condition. Late responses
from previous searches or conditions cannot replace current results.

SQL constraints use reactive keyword arguments::

    pane.recordPicker(checkedId='^.province', table='glbl.provincia',
                      columns='$nome,$sigla', condition='$regione=:region',
                      condition_region='^.region')

``maxSelect`` limits new checks in multiple mode. ``disabled`` accepts a Boolean
or reactive binding. Bind it to the host form's disabled state where appropriate.
Selection validation and required-value rules belong to the host. The multiple
selection helper checks displayed candidates only, respecting the maximum.
External ``checkedId`` changes update the controls. Publish ``reload`` to the
picker source node to refresh the current search and checked record details.

Host dialog
-----------

Compose a standard Genro dialog around ``recordPicker``. If confirmation is needed,
bind the picker to a dialog-specific working path, copy the accepted value there
on opening, and copy it back only from the host's Confirm action::

    dialog = pane.dialog(nodeId='province_dialog', title='Choose province',
                         closable=True, width='600px',
                         connect_onShowing='SET .working = GET .accepted;')
    dialog.recordPicker(checkedId='^.working', table='glbl.provincia',
                        columns='$nome,$sigla', layout='list')
    dialog.button('Confirm', action="""
        SET .accepted = GET .working;
        genro.wdgById('province_dialog').hide();
    """)
    pane.button('Choose province', action="genro.wdgById('province_dialog').show();")

``recordPickerButton`` is a separate templated opener. It displays ``placeholder``
when its bound ``record`` is empty and renders the record template after the host
sets that path. Its ``action`` belongs to the host; it neither opens a particular
dialog nor confirms a selection itself::

    pane.recordPickerButton(
        record='^.chosen_record', placeholder='!!Select province',
        template='<strong>$nome</strong><div>$sigla</div>',
        action="genro.wdgById('province_dialog').show();")

Use the dialog picker's ``selectedRecord='^.working_record'`` output, and copy it
to ``.chosen_record`` in the host's Confirm action. Cancel leaves the displayed
record unchanged. The opener also supports ``template_resource`` and ``disabled``.
Its magnifier is a theme-colored outline SVG, replaceable through
``--record-picker-button-icon``.

The demo includes this clickable record box, host-owned Cancel and Confirm buttons and responsive dialog CSS.
The widget itself has no dependency on dialog lifecycle or dimensions.

Theming
-------

The component inherits application typography. Fields use ``--form-field-*``;
the search field uses ``--radius-pill``; chips use ``--btn-tonal-*``;
candidates use ``--card-surface``, ``--border-color`` and ``--radius-sm``;
selection uses ``--grid-row-selected-bg`` and ``--accent-color``. The outer frame
uses ``--roundedgroup-border`` and ``--radius-md``. The optional selected area has
a divider and ``--surface-light`` background. Its bulk action is a small,
underlined button in the accent color. Empty-state text uses ``--text-placeholder``
at a larger size. Joanna, Mimi
and their color variants therefore supply the appearance without a separate palette.

Optional ``--record-picker-*`` overrides can be declared in application CSS or
on a containing element. The main hooks are ``bg``, ``color``, ``label-color``,
``muted-color``, ``border``, ``radius``, ``control-bg``, ``input-bg``, ``input-color``,
``input-border``, ``input-padding``, ``card-bg``, ``hover-bg``, ``selected-bg``,
``selected-border``, ``selected-color``, ``focus-color``, ``preview-bg``,
``preview-width``, ``card-width``, ``gap``, ``padding``, ``item-padding``,
``selection-height``, ``box-height``, ``columns``, ``touch-height``, ``search-radius``, ``chip-radius``,
``chip-bg``, ``chip-color``, ``chip-hover-bg``, ``chip-padding``, ``frame-border``,
``frame-radius``, ``selection-bg``, ``selection-border``, ``selection-padding``,
``action-color``, ``action-font-size``, ``empty-color`` and ``empty-font-size``.
The opener adds ``button-width``, ``button-height``, ``button-padding``, ``button-bg``,
``button-icon``, ``button-icon-size``, ``button-icon-inset`` and ``placeholder-color``. For example::

    .compact_picker {
        --record-picker-card-width: 12em;
        --record-picker-gap: .4em;
        --record-picker-item-padding: .5em;
    }

Examples and verification
-------------------------

``test/components/recordpicker`` uses the ``glbl`` package and its startup data.
Cases cover a source Bag, separate single-selection extended preview, host dialog,
multicheck with resource template and compact preview, live database preselection,
reactive region conditions, empty/disabled state, and optional radios.
Use ``?css_theme=joanna`` or ``?css_theme=mimi`` to compare themes.

Automated checks::

    node --test gnrjs/tests/record_picker.test.js
    python -m pytest gnrpy/tests/web/recordpicker_test.py -q

The Python database tests create isolated SQLite tables and execute real inserts
and queries. JavaScript tests cover immediate checked paths, output Bags, preview
selection, limits, filtering, empty searches, RPC envelopes and stale responses.
