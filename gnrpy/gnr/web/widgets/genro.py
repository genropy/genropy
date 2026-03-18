"""GenroPy gnr namespace widgets — DbSelect, dataController, FramePane, QuickGrid, etc.

Formal documentation of the gnrNS widgets available on GnrDomSrc.
These methods are generated at runtime via __getattr__ -> child(tag, **kwargs).
"""
from __future__ import annotations

from genro_bag.builder import element


class GenroWidgets:
    """Mixin documenting GenroPy-specific widgets (gnrNS namespace)."""

    # =====================================================================
    # Data binding
    # =====================================================================

    @element
    def dataController(self, script=None, **kwargs):
        """Client-side controller that executes JavaScript when observed data changes.

        Args:
            script: JavaScript code to execute.
            **kwargs: Data bindings using ^path (subscribe) or =path (read) syntax.
                Special attrs: _init, _onStart, _timing, _if, _fired.
        """
        ...

    @element
    def dataRpc(self, pathOrMethod=None, method=None, **kwargs):
        """Remote procedure call to a server-side Python method.

        Calls a @public_method on the server and stores the result at path.

        Args:
            pathOrMethod: Datastore path for the result, or the method name directly.
            method: Server method name (if pathOrMethod is the path).
            **kwargs: Parameters passed to the server method.
                Special attrs: _onCalling, _onResult, _onError, _lockScreen, sync,
                _fired, _if, _else.
        """
        ...

    @element
    def dataFormula(self, path=None, formula=None, **kwargs):
        """Reactive formula that computes a value from datastore paths.

        Args:
            path: Datastore path where the computed result is stored.
            formula: JavaScript expression using named variables.
            **kwargs: Variable bindings (varname='^.path' or varname='=.path').
        """
        ...

    @element
    def dataRemote(self, path=None, method=None, _resolved=None, **kwargs):
        """Lazy resolver that calls a server RPC when the path is first accessed.

        Unlike dataRpc (which fires immediately), dataRemote installs a resolver
        that triggers the RPC only when the client reads the path.

        Args:
            path: Datastore path where the result is stored.
            method: Server method name to call.
            _resolved: Internal flag for resolution state.
            **kwargs: Parameters passed to the server method.
                Special attrs: cacheTime (seconds to cache the result).
        """
        ...

    @element
    def dataScript(self, path=None, script=None, **kwargs):
        """Deprecated since 0.7. Use dataController or dataFormula instead.

        Args:
            path: Datastore path for the result.
            script: JavaScript code to execute.
        """
        ...

    # =====================================================================
    # Database selection widgets
    # =====================================================================

    @element
    def DbSelect(self, dbtable=None, value=None, **kwargs):
        """Database-connected autocomplete select widget.

        Progressive search: startswith -> contains -> regex word boundary -> ILIKE.

        Args:
            dbtable: Table address in package.table format (e.g. 'app.customer').
            value: Datastore path for the selected record's pkey (^path syntax).
            **kwargs: Common attrs: lbl, columns, auxColumns, condition, condition_*,
                selected_*, hasDownArrow, alternatePkey, order_by, limit,
                validate_notnull, width.
        """
        ...

    @element
    def CallBackSelect(self, **kwargs):
        """Select widget that uses a custom callback method for options.

        Args:
            **kwargs: Callback configuration and standard select attrs.
        """
        ...

    @element
    def RemoteSelect(self, **kwargs):
        """Select widget that fetches options from a remote method.

        Args:
            **kwargs: Remote method configuration and standard select attrs.
        """
        ...

    @element
    def PackageSelect(self, **kwargs):
        """Select widget for choosing a GenroPy package.

        Args:
            **kwargs: Standard select attrs (value, lbl, width).
        """
        ...

    @element
    def TableSelect(self, **kwargs):
        """Select widget for choosing a database table.

        Args:
            **kwargs: Standard select attrs (value, lbl, width, pkg).
        """
        ...

    @element
    def DbComboBox(self, **kwargs):
        """Database-connected combobox allowing free text or db-matched values.

        Args:
            **kwargs: Same as DbSelect plus free-text input support.
        """
        ...

    # =====================================================================
    # Database views and forms
    # =====================================================================

    @element(sub_tags='*')
    def DbView(self, **kwargs):
        """Database view widget for displaying tabular data from a query.

        Args:
            **kwargs: table, columns, where, order_by, struct, etc.
        """
        ...

    @element(sub_tags='*')
    def DbForm(self, **kwargs):
        """Database form widget for editing a single record.

        Args:
            **kwargs: table, formId, store, datapath, etc.
        """
        ...

    @element
    def DbQuery(self, **kwargs):
        """Database query widget for building and executing queries.

        Args:
            **kwargs: table, query configuration.
        """
        ...

    @element
    def DbField(self, **kwargs):
        """Database field widget — renders the appropriate input for a column dtype.

        Args:
            **kwargs: field, table, value, lbl, tag (override widget type).
        """
        ...

    # =====================================================================
    # Frame containers
    # =====================================================================

    @element(sub_tags='*')
    def FramePane(self, frameCode=None, **kwargs):
        """Frame container with named slot regions (top, bottom, left, right, center).

        The center region is automatically available. Access regions via
        frame.top, frame.bottom, frame.left, frame.right, frame.center.

        Args:
            frameCode: Unique identifier for the frame (use '#' suffix for auto-id).
            **kwargs: Common attrs: datapath, title, height, width, _class.
        """
        ...

    @element(sub_tags='*')
    def FrameForm(self, frameCode=None, formId=None, table=None, store=None, **kwargs):
        """Frame container with integrated form store for record editing.

        Combines FramePane layout with a FormStore for load/save operations.

        Args:
            frameCode: Unique identifier for the frame.
            formId: Unique identifier for the form.
            table: Database table in package.table format.
            store: Store type ('record', 'document', 'memory').
            **kwargs: Common attrs: datapath, pkeyPath, default_kwargs.
        """
        ...

    @element(sub_tags='*')
    def BoxForm(self, **kwargs):
        """Simplified form container without frame regions.

        Args:
            **kwargs: formId, table, store, datapath.
        """
        ...

    # =====================================================================
    # Grid widgets
    # =====================================================================

    @element(sub_tags='*')
    def QuickGrid(self, value=None, **kwargs):
        """Lightweight grid widget for displaying and editing tabular data.

        Supports inline editing, column configuration, and tools (addrow, delrow, export).

        Args:
            value: Datastore path to the Bag containing grid data (^path syntax).
            **kwargs: Common attrs: columns, height, width, border, default_*,
                selfDragRows, canSort, canFilter.
        """
        ...

    @element(sub_tags='*')
    def TreeGrid(self, **kwargs):
        """Hierarchical grid with expandable tree rows.

        Args:
            **kwargs: value, storepath, columns, height, width.
        """
        ...

    @element(sub_tags='*')
    def staticGrid(self, **kwargs):
        """Static grid widget with fixed structure definition.

        Args:
            **kwargs: storepath, struct, height, width.
        """
        ...

    @element(sub_tags='*')
    def dynamicGrid(self, **kwargs):
        """Dynamic grid widget that builds structure from data.

        Args:
            **kwargs: storepath, table, height, width.
        """
        ...

    @element(sub_tags='*')
    def gridView(self, **kwargs):
        """Grid view container for structured data display.

        Args:
            **kwargs: storepath, struct, height, width.
        """
        ...

    @element
    def viewHeader(self, **kwargs):
        """Header definition for a gridView.

        Args:
            **kwargs: Header configuration.
        """
        ...

    @element
    def viewRow(self, **kwargs):
        """Row definition for a gridView.

        Args:
            **kwargs: Row configuration.
        """
        ...

    @element
    def gridEditor(self, **kwargs):
        """Inline editor widget for grid cells.

        Args:
            **kwargs: Editor configuration (field, tag, values).
        """
        ...

    @element(sub_tags='*')
    def GridGallery(self, **kwargs):
        """Grid displayed as a visual gallery of cards/thumbnails.

        Args:
            **kwargs: storepath, columns, cardWidth, cardHeight.
        """
        ...

    # =====================================================================
    # Palette widgets
    # =====================================================================

    @element(sub_tags='*')
    def Palette(self, **kwargs):
        """Floating palette window — draggable, resizable popup panel.

        Args:
            **kwargs: paletteCode, title, dockTo, width, height, _class.
        """
        ...

    @element(sub_tags='*')
    def PaletteTree(self, **kwargs):
        """Palette containing a tree widget.

        Args:
            **kwargs: paletteCode, title, storepath, dockTo, width, height.
        """
        ...

    @element(sub_tags='*')
    def PalettePane(self, **kwargs):
        """Palette containing a generic content pane.

        Args:
            **kwargs: paletteCode, title, dockTo, width, height.
        """
        ...

    @element(sub_tags='*')
    def PaletteGroup(self, **kwargs):
        """Group of palettes that share a dock area.

        Args:
            **kwargs: groupCode, title, dockTo.
        """
        ...

    @element(sub_tags='*')
    def PaletteMap(self, **kwargs):
        """Palette containing a map widget.

        Args:
            **kwargs: paletteCode, title, dockTo, width, height.
        """
        ...

    @element(sub_tags='*')
    def PaletteImporter(self, **kwargs):
        """Palette for importing data from external sources.

        Args:
            **kwargs: paletteCode, title, importMethod.
        """
        ...

    @element(sub_tags='*')
    def PaletteChart(self, **kwargs):
        """Palette containing a chart widget.

        Args:
            **kwargs: paletteCode, title, chartType, storepath.
        """
        ...

    @element(sub_tags='*')
    def PaletteBagNodeEditor(self, **kwargs):
        """Palette for editing a BagNode's attributes and value.

        Args:
            **kwargs: paletteCode, title, storepath.
        """
        ...

    # =====================================================================
    # Tree widgets
    # =====================================================================

    @element(sub_tags='*')
    def TreeFrame(self, **kwargs):
        """Tree widget inside a frame with toolbar slots.

        Args:
            **kwargs: storepath, frameCode, columns, height, width.
        """
        ...

    @element(sub_tags='*')
    def QuickTree(self, **kwargs):
        """Lightweight tree widget for hierarchical data.

        Args:
            **kwargs: storepath, value, height, width, labelAttribute.
        """
        ...

    @element(sub_tags='*')
    def FieldsTree(self, **kwargs):
        """Tree widget that displays database table fields.

        Args:
            **kwargs: table, value, height, width.
        """
        ...

    # =====================================================================
    # Code editors
    # =====================================================================

    @element
    def codemirror(self, **kwargs):
        """CodeMirror text editor widget for code editing.

        Args:
            **kwargs: value (^path), mode (language), theme, readOnly,
                lineNumbers, height, width.
        """
        ...

    @element
    def CodeEditor(self, value=None, **kwargs):
        """GenroPy enhanced code editor (wraps CodeMirror with extra features).

        Args:
            value: Datastore path to the source code text (^path syntax).
            **kwargs: mode, theme, readOnly, lineNumbers, height, width.
        """
        ...

    # =====================================================================
    # Rich text editors
    # =====================================================================

    @element
    def ckEditor(self, **kwargs):
        """CKEditor rich text editor widget.

        Args:
            **kwargs: value, height, width, toolbar, config.
        """
        ...

    @element
    def ExtendedCkeditor(self, **kwargs):
        """Extended CKEditor with additional GenroPy integration.

        Args:
            **kwargs: value, height, width, toolbar, config.
        """
        ...

    @element
    def tinyMCE(self, **kwargs):
        """TinyMCE rich text editor widget.

        Args:
            **kwargs: value, height, width, config.
        """
        ...

    @element
    def ExtendedTinyMCE(self, **kwargs):
        """Extended TinyMCE with additional GenroPy integration.

        Args:
            **kwargs: value, height, width, config.
        """
        ...

    @element
    def mdeditor(self, **kwargs):
        """Markdown editor widget with preview.

        Args:
            **kwargs: value, height, width, readOnly.
        """
        ...

    # =====================================================================
    # Chart and visualization widgets
    # =====================================================================

    @element
    def protovis(self, **kwargs):
        """Protovis data visualization widget.

        Args:
            **kwargs: Visualization configuration.
        """
        ...

    @element
    def dygraph(self, **kwargs):
        """Dygraph time-series chart widget.

        Args:
            **kwargs: storepath, value, height, width, options.
        """
        ...

    @element
    def chartjs(self, **kwargs):
        """Chart.js chart widget for various chart types.

        Args:
            **kwargs: chartType, storepath, value, height, width, options.
        """
        ...

    @element(sub_tags='*')
    def ChartPane(self, **kwargs):
        """Container pane for embedding chart widgets.

        Args:
            **kwargs: chartType, storepath, height, width.
        """
        ...

    @element
    def fullcalendar(self, **kwargs):
        """FullCalendar event calendar widget.

        Args:
            **kwargs: storepath, value, defaultView, height, width.
        """
        ...

    # =====================================================================
    # Script and function elements
    # =====================================================================

    @element
    def script(self, **kwargs):
        """Client-side JavaScript script element.

        Args:
            **kwargs: Script content and configuration.
        """
        ...

    @element
    def func(self, **kwargs):
        """Client-side JavaScript function definition element.

        Args:
            **kwargs: Function name, parameters, body.
        """
        ...

    # =====================================================================
    # File upload widgets
    # =====================================================================

    @element
    def fileUploader(self, **kwargs):
        """File upload widget with progress indication.

        Args:
            **kwargs: uploadPath, onUpload, multiple, accept.
        """
        ...

    @element
    def DropUploader(self, **kwargs):
        """Drag-and-drop file upload area.

        Args:
            **kwargs: uploadPath, onUpload, _class, label.
        """
        ...

    @element
    def ModalUploader(self, **kwargs):
        """File upload widget in a modal dialog.

        Args:
            **kwargs: uploadPath, onUpload, title, accept.
        """
        ...

    @element(sub_tags='*')
    def DropUploaderGrid(self, **kwargs):
        """Drag-and-drop upload area with a grid showing uploaded files.

        Args:
            **kwargs: uploadPath, onUpload, storepath.
        """
        ...

    @element
    def ImgUploader(self, **kwargs):
        """Image upload widget with preview.

        Args:
            **kwargs: uploadPath, value, width, height, crop.
        """
        ...

    # =====================================================================
    # Button widgets
    # =====================================================================

    @element
    def SlotButton(self, label=None, **kwargs):
        """Compact button designed for toolbars and slot areas.

        The label acts as tooltip when iconClass is set.

        Args:
            label: Button tooltip (or visible label if no iconClass).
            **kwargs: action (JavaScript), iconClass, publish, topic.
        """
        ...

    @element
    def LightButton(self, **kwargs):
        """Lightweight styled button with minimal chrome.

        Args:
            **kwargs: label, action, iconClass, _class.
        """
        ...

    @element
    def DownloadButton(self, **kwargs):
        """Button that triggers a file download.

        Args:
            **kwargs: url, method, filename, label, iconClass.
        """
        ...

    @element
    def MultiButton(self, **kwargs):
        """Segmented button group with multiple selectable items.

        Args:
            **kwargs: value, storepath, code, items.
        """
        ...

    @element
    def StackButtons(self, **kwargs):
        """Button group linked to a stackContainer for panel switching.

        Args:
            **kwargs: stackNodeId, _class.
        """
        ...

    # =====================================================================
    # Form widgets
    # =====================================================================

    @element
    def FormStore(self, **kwargs):
        """Client-side form data store for load/save record operations.

        Args:
            **kwargs: handler, table, formId, pkeyField, autoSave.
        """
        ...

    @element
    def PasswordTextBox(self, **kwargs):
        """Password input widget with masked text.

        Args:
            **kwargs: value, lbl, width, validate_notnull.
        """
        ...

    @element
    def CheckBoxText(self, **kwargs):
        """Checkbox with an associated text label.

        Args:
            **kwargs: value, label, lbl.
        """
        ...

    @element
    def RadioButtonText(self, **kwargs):
        """Radio button with an associated text label.

        Args:
            **kwargs: value, label, lbl, group.
        """
        ...

    @element
    def ColorTextBox(self, **kwargs):
        """Text input with a color picker.

        Args:
            **kwargs: value, lbl, width.
        """
        ...

    @element
    def ColorFiltering(self, **kwargs):
        """Color-based filtering widget.

        Args:
            **kwargs: value, storepath, colors.
        """
        ...

    @element
    def SearchBox(self, **kwargs):
        """Search input box with configurable search behavior.

        Args:
            **kwargs: value, searchOn, nodeId, width.
        """
        ...

    @element
    def MultiValueEditor(self, **kwargs):
        """Editor for multiple values (tags, tokens).

        Args:
            **kwargs: value, lbl, separator, width.
        """
        ...

    @element
    def MultiLanguageTextBox(self, **kwargs):
        """Text input with multi-language support.

        Args:
            **kwargs: value, lbl, languages, width.
        """
        ...

    @element
    def TextboxMenu(self, **kwargs):
        """Textbox with an attached dropdown menu for predefined options.

        Args:
            **kwargs: value, lbl, values, width.
        """
        ...

    @element
    def MultiLineTextbox(self, **kwargs):
        """Multi-line textbox with auto-expanding height.

        Args:
            **kwargs: value, lbl, height, width.
        """
        ...

    @element
    def CharCounterTextarea(self, **kwargs):
        """Textarea with a live character counter display.

        Args:
            **kwargs: value, lbl, maxLength, height, width.
        """
        ...

    @element(sub_tags='*')
    def QuickEditor(self, **kwargs):
        """Quick record editor — compact form for editing a single record inline.

        Args:
            **kwargs: table, formId, store, datapath.
        """
        ...

    # =====================================================================
    # Bag editors
    # =====================================================================

    @element(sub_tags='*')
    def bagEditor(self, storepath=None, **kwargs):
        """Tree-based editor for inspecting and modifying a Bag structure.

        Args:
            storepath: Datastore path to the Bag to edit.
            **kwargs: labelAttribute, addrow, delrow, addcol, height, width.
        """
        ...

    @element(sub_tags='*')
    def BagNodeEditor(self, **kwargs):
        """Editor for a single BagNode's value and attributes.

        Args:
            **kwargs: storepath, nodeId.
        """
        ...

    @element(sub_tags='*')
    def FlatBagEditor(self, **kwargs):
        """Flat (non-hierarchical) Bag editor displayed as a grid.

        Args:
            **kwargs: storepath, columns.
        """
        ...

    # =====================================================================
    # Document and template widgets
    # =====================================================================

    @element(sub_tags='*')
    def DocumentFrame(self, **kwargs):
        """Frame for rendering HTML documents/templates.

        Args:
            **kwargs: storepath, src, height, width.
        """
        ...

    @element
    def DocItem(self, **kwargs):
        """Document item widget for structured document content.

        Args:
            **kwargs: content, template, datapath.
        """
        ...

    @element
    def TemplateChunk(self, **kwargs):
        """Renderable template chunk bound to datastore values.

        Args:
            **kwargs: template, datasource, editable, _class.
        """
        ...

    @element
    def PagedHtml(self, **kwargs):
        """Paginated HTML viewer widget.

        Args:
            **kwargs: storepath, value, pageSize, height, width.
        """
        ...

    # =====================================================================
    # User object widgets
    # =====================================================================

    @element(sub_tags='*')
    def UserObjectLayout(self, **kwargs):
        """Layout container for user-defined objects (saved views, prints).

        Args:
            **kwargs: objtype, table, tbl, datapath.
        """
        ...

    @element(sub_tags='*')
    def UserObjectBar(self, **kwargs):
        """Toolbar for selecting and managing saved user objects.

        Args:
            **kwargs: objtype, table, tbl, datapath.
        """
        ...

    # =====================================================================
    # Menu and navigation widgets
    # =====================================================================

    @element
    def MenuDiv(self, **kwargs):
        """Div that opens a context menu on click or right-click.

        Args:
            **kwargs: storepath, action, _class.
        """
        ...

    @element
    def ComboArrow(self, **kwargs):
        """Dropdown arrow button that opens a selection popup.

        Args:
            **kwargs: storepath, action, values.
        """
        ...

    @element
    def ComboMenu(self, **kwargs):
        """Combo-style menu widget.

        Args:
            **kwargs: storepath, values, action.
        """
        ...

    # =====================================================================
    # Tooltip and popup widgets
    # =====================================================================

    @element(sub_tags='*')
    def TooltipPane(self, **kwargs):
        """Pane that appears as a tooltip on hover or focus.

        Args:
            **kwargs: connectId, position, showDelay, _class.
        """
        ...

    @element
    def Semaphore(self, **kwargs):
        """Visual semaphore indicator (red/yellow/green status).

        Args:
            **kwargs: value, colors, _class.
        """
        ...

    # =====================================================================
    # Media widgets
    # =====================================================================

    @element
    def VideoPlayer(self, **kwargs):
        """Video player widget.

        Args:
            **kwargs: src, value, height, width, autoplay, controls.
        """
        ...

    @element
    def VideoPickerPalette(self, **kwargs):
        """Palette for selecting and previewing video files.

        Args:
            **kwargs: paletteCode, title, storepath.
        """
        ...

    # =====================================================================
    # Geo and map widgets
    # =====================================================================

    @element
    def GeoCoderField(self, **kwargs):
        """Text input with geocoding integration.

        Args:
            **kwargs: value, lbl, lat_path, lng_path.
        """
        ...

    @element
    def StaticMap(self, **kwargs):
        """Static map image widget.

        Args:
            **kwargs: lat, lng, zoom, width, height, mapType.
        """
        ...

    @element
    def GeoSearch(self, **kwargs):
        """Geographic search widget with autocomplete.

        Args:
            **kwargs: value, lbl, width, onResult.
        """
        ...

    # =====================================================================
    # Scanner and specialized input
    # =====================================================================

    @element
    def qrscanner(self, **kwargs):
        """QR code scanner widget using device camera.

        Args:
            **kwargs: value, onScan, width, height.
        """
        ...

    # =====================================================================
    # Shared and collaborative widgets
    # =====================================================================

    @element
    def SharedObject(self, **kwargs):
        """Widget for real-time shared/collaborative data objects.

        Args:
            **kwargs: objectId, storepath, onUpdate.
        """
        ...

    @element
    def IframeDiv(self, **kwargs):
        """Div that loads content via an internal iframe.

        Args:
            **kwargs: src, height, width, _class.
        """
        ...
