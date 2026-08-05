"""GenroPy dijit widgets — Dojo form, button, menu, dialog and misc widgets.

Formal documentation of the dijit namespace widgets available on GnrDomSrc.
These methods are generated at runtime via __getattr__ -> child(tag, **kwargs).
"""
from __future__ import annotations

from genro_bag.builder import element


class DijitWidgets:
    """Mixin documenting Dojo dijit widgets (form, buttons, menus, dialogs, misc)."""

    # =====================================================================
    # Form — Text inputs
    # =====================================================================

    @element
    def textBox(self, value: str | None = None,
                trim: bool = False,
                maxLength: int | None = None,
                **kwargs):
        """A base class for textbox form inputs.

        Args:
            value: Current value of the textbox.
            trim: If True, removes leading and trailing whitespace.
            maxLength: Maximum number of characters allowed.
        """
        ...

    @element
    def validationTextBox(self, value: str | None = None,
                          regExp: str | None = None,
                          required: bool = False,
                          invalidMessage: str | None = None,
                          promptMessage: str | None = None,
                          **kwargs):
        """A TextBox with the ability to validate content and provide user feedback.

        Args:
            value: Current value of the textbox.
            regExp: Regular expression string for validation.
            required: If True, the field must be filled in.
            invalidMessage: Message displayed when the value is invalid.
            promptMessage: Message displayed when the field is focused and empty.
        """
        ...

    @element
    def numberTextBox(self, value: float | None = None,
                      constraints: dict | None = None,
                      required: bool = False,
                      invalidMessage: str | None = None,
                      **kwargs):
        """A validating, serializable, range-bound text box for numbers.

        Args:
            value: Current numeric value.
            constraints: Dict with min, max, places, pattern constraints.
            required: If True, the field must be filled in.
            invalidMessage: Message displayed when the value is invalid.
        """
        ...

    @element
    def currencyTextBox(self, value: float | None = None,
                        currency: str | None = None,
                        constraints: dict | None = None,
                        required: bool = False,
                        **kwargs):
        """A validating currency textbox.

        Args:
            value: Current currency value.
            currency: ISO 4217 currency code (e.g. 'USD', 'EUR').
            constraints: Dict with min, max, places constraints.
            required: If True, the field must be filled in.
        """
        ...

    @element
    def dateTextBox(self, value: str | None = None,
                    constraints: dict | None = None,
                    required: bool = False,
                    invalidMessage: str | None = None,
                    **kwargs):
        """A validating, serializable, range-bound date text box with a popup calendar.

        Args:
            value: Current date value (ISO format string).
            constraints: Dict with min, max, datePattern constraints.
            required: If True, the field must be filled in.
            invalidMessage: Message displayed when the value is invalid.
        """
        ...

    @element
    def datetimeTextBox(self, value: str | None = None,
                        constraints: dict | None = None,
                        required: bool = False,
                        **kwargs):
        """A validating, serializable, range-bound date/time text box.

        Args:
            value: Current datetime value (ISO format string).
            constraints: Dict with min, max constraints.
            required: If True, the field must be filled in.
        """
        ...

    @element
    def timeTextBox(self, value: str | None = None,
                    constraints: dict | None = None,
                    required: bool = False,
                    **kwargs):
        """A validating, serializable, range-bound time text box with a popup time picker.

        Args:
            value: Current time value (ISO format string).
            constraints: Dict with min, max, clickableIncrement, visibleRange constraints.
            required: If True, the field must be filled in.
        """
        ...

    # =====================================================================
    # Form — Textarea
    # =====================================================================

    @element
    def textarea(self, value: str | None = None,
                 **kwargs):
        """A resizing textarea widget. Grows vertically to fit its content.

        Does not support cols or rows; set width via CSS style.

        Args:
            value: Current text content.
        """
        ...

    @element
    def simpleTextarea(self, value: str | None = None,
                       rows: int | None = None,
                       cols: int | None = None,
                       **kwargs):
        """A simple textarea that does not auto-resize. Works with dijit.form.Form.

        Args:
            value: Current text content.
            rows: Number of visible text rows.
            cols: Number of visible text columns.
        """
        ...

    # =====================================================================
    # Form — Checkboxes and radio
    # =====================================================================

    @element
    def checkBox(self, value: bool | None = None,
                 checked: bool = False,
                 **kwargs):
        """Same as an HTML checkbox, but with Dojo styling.

        Supports both high-contrast mode and normal mode rendering.

        Args:
            value: Value submitted with the form when checked.
            checked: If True, the checkbox is initially checked.
        """
        ...

    @element
    def radioButton(self, value: str | None = None,
                    checked: bool = False,
                    name: str | None = None,
                    **kwargs):
        """Same as an HTML radio button, but with Dojo styling.

        Radio grouping is managed by dijit, not by the browser.

        Args:
            value: Value submitted with the form when selected.
            checked: If True, this radio is initially selected.
            name: Group name for mutually exclusive radio buttons.
        """
        ...

    # =====================================================================
    # Form — ComboBox and FilteringSelect
    # =====================================================================

    @element
    def comboBox(self, value: str | None = None,
                 store: str | None = None,
                 searchAttr: str | None = None,
                 autoComplete: bool = True,
                 hasDownArrow: bool = True,
                 **kwargs):
        """Auto-completing text box. Base class for FilteringSelect.

        Values in the drop-down are populated from a data provider that
        filters based on user input.

        Args:
            value: Current value.
            store: Data store providing the list of values.
            searchAttr: Attribute of store items to search against.
            autoComplete: If True, auto-completes the first matching value.
            hasDownArrow: If True, shows the drop-down arrow button.
        """
        ...

    @element
    def filteringSelect(self, value: str | None = None,
                        store: str | None = None,
                        searchAttr: str | None = None,
                        labelAttr: str | None = None,
                        autoComplete: bool = True,
                        hasDownArrow: bool = True,
                        required: bool = False,
                        **kwargs):
        """An enhanced SELECT populated dynamically. Only allows values from the list.

        The submitted value is the hidden value, not the displayed label.
        Filters the drop-down list as you type.

        Args:
            value: Current hidden value (e.g. 'CA').
            store: Data store providing the list of values.
            searchAttr: Attribute to search against.
            labelAttr: Attribute for the displayed text (defaults to searchAttr).
            autoComplete: If True, auto-completes the first matching value.
            hasDownArrow: If True, shows the drop-down arrow button.
            required: If True, the field must have a value.
        """
        ...

    @element
    def multiSelect(self, value: list | None = None,
                    size: int | None = None,
                    **kwargs):
        """Wrapper for a native select with multiple='true'. Works with dijit.form.Form.

        Args:
            value: List of currently selected values.
            size: Number of visible elements in the list.
        """
        ...

    # =====================================================================
    # Form — Sliders and spinners
    # =====================================================================

    @element
    def horizontalSlider(self, value: float | None = None,
                         minimum: float = 0,
                         maximum: float = 100,
                         discreteValues: int | None = None,
                         showButtons: bool = True,
                         **kwargs):
        """A form widget to select a value with a horizontally draggable handle.

        Args:
            value: Current slider value.
            minimum: Minimum value of the slider.
            maximum: Maximum value of the slider.
            discreteValues: Number of discrete positions (snapping).
            showButtons: If True, shows increment/decrement buttons at the ends.
        """
        ...

    @element
    def verticalSlider(self, value: float | None = None,
                       minimum: float = 0,
                       maximum: float = 100,
                       discreteValues: int | None = None,
                       showButtons: bool = True,
                       **kwargs):
        """A form widget to select a value with a vertically draggable handle.

        Args:
            value: Current slider value.
            minimum: Minimum value of the slider.
            maximum: Maximum value of the slider.
            discreteValues: Number of discrete positions (snapping).
            showButtons: If True, shows increment/decrement buttons at the ends.
        """
        ...

    @element
    def numberSpinner(self, value: float | None = None,
                      smallDelta: float = 1,
                      largeDelta: float = 10,
                      constraints: dict | None = None,
                      **kwargs):
        """A NumberTextBox with up/down arrows for incremental value changes.

        Args:
            value: Current numeric value.
            smallDelta: Amount to increment/decrement on each arrow click.
            largeDelta: Amount to increment/decrement on Page Up/Down.
            constraints: Dict with min, max, places constraints.
        """
        ...

    # =====================================================================
    # Form — InlineEditBox
    # =====================================================================

    @element
    def inlineEditBox(self, value: str | None = None,
                      editor: str | None = None,
                      autoSave: bool = True,
                      buttonSave: str | None = None,
                      buttonCancel: str | None = None,
                      **kwargs):
        """An element with in-line edit capabilities.

        When clicked, an editor replaces the text. Optionally shows Save/Cancel
        buttons. Default editor is Textarea (or TextBox for inline values).

        Args:
            value: Current displayed/editable value.
            editor: Widget class to use as editor (e.g. 'dijit.Editor', 'dijit.form.Slider').
            autoSave: If True, saves on blur without requiring Save button.
            buttonSave: Label for the save button (empty string to hide).
            buttonCancel: Label for the cancel button (empty string to hide).
        """
        ...

    # =====================================================================
    # Buttons
    # =====================================================================

    @element
    def button(self, label: str | None = None,
               iconClass: str | None = None,
               showLabel: bool = True,
               **kwargs):
        """A styled button. Same as an HTML button with Dojo styling.

        Args:
            label: Text displayed on the button.
            iconClass: CSS class for the button icon.
            showLabel: If False, hides the label text (icon only).
        """
        ...

    @element
    def toggleButton(self, label: str | None = None,
                     checked: bool = False,
                     iconClass: str | None = None,
                     **kwargs):
        """A button that can be in two states (checked or not).

        Can be used as base for tabs, checkboxes or radio buttons.

        Args:
            label: Text displayed on the button.
            checked: If True, the button is initially in the checked state.
            iconClass: CSS class for the button icon.
        """
        ...

    @element
    def comboButton(self, label: str | None = None,
                    iconClass: str | None = None,
                    **kwargs):
        """A normal button combined with a drop-down menu.

        Clicking the button fires onClick; clicking the arrow opens the menu.

        Args:
            label: Text displayed on the button.
            iconClass: CSS class for the button icon.
        """
        ...

    @element
    def dropDownButton(self, label: str | None = None,
                       iconClass: str | None = None,
                       **kwargs):
        """A button that opens a popup (menu or tooltip dialog) when clicked.

        Args:
            label: Text displayed on the button.
            iconClass: CSS class for the button icon.
        """
        ...

    # =====================================================================
    # Menu
    # =====================================================================

    @element(sub_tags='*')
    def menu(self, targetNodeIds: list | None = None,
             contextMenuForWindow: bool = False,
             **kwargs):
        """A context menu that can be assigned to multiple elements.

        Args:
            targetNodeIds: List of DOM node IDs to bind this menu to.
            contextMenuForWindow: If True, makes this the context menu for the whole window.
        """
        ...

    @element
    def menubar(self, **kwargs):
        """A horizontal menu bar, typically placed at the top of a page or dialog."""
        ...

    @element
    def menuItem(self, label: str | None = None,
                 iconClass: str | None = None,
                 disabled: bool = False,
                 **kwargs):
        """A line item in a Menu widget.

        Renders with three columns: icon, label, and expand arrow (for sub-menus).

        Args:
            label: Text displayed for this menu item.
            iconClass: CSS class for the item icon.
            disabled: If True, the item is grayed out and not clickable.
        """
        ...

    # =====================================================================
    # Toolbar
    # =====================================================================

    @element(sub_tags='*')
    def toolbar(self, **kwargs):
        """A toolbar container for buttons, typically used with dijit.Editor."""
        ...

    @element
    def toolbarSeparator(self, **kwargs):
        """A visual separator line within a Toolbar."""
        ...

    # =====================================================================
    # Dialog
    # =====================================================================

    @element(sub_tags='*')
    def dialog(self, title: str | None = None,
               href: str | None = None,
               draggable: bool = True,
               **kwargs):
        """A modal dialog widget. Blocks access to the screen with an overlay.

        Extended from ContentPane, so supports href for remote content loading.

        Args:
            title: Title text displayed in the dialog header.
            href: URL to load content from via ajax.
            draggable: If True, the dialog can be dragged by its title bar.
        """
        ...

    @element(sub_tags='*')
    def tooltipDialog(self, title: str | None = None,
                      **kwargs):
        """A popup dialog that appears like a Tooltip. Typically used with DropDownButton.

        Args:
            title: Description of the tooltip dialog (required for accessibility).
        """
        ...

    # =====================================================================
    # Progress
    # =====================================================================

    @element
    def progressBar(self, progress: str | None = None,
                    maximum: float = 100,
                    places: int = 0,
                    indeterminate: bool = False,
                    **kwargs):
        """A progress indication widget.

        Progress can be specified as a percentage string (e.g. '30%') or
        as an absolute value between 0 and maximum.

        Args:
            progress: Initial progress value (percentage string or number).
            maximum: Maximum value for absolute progress.
            places: Number of decimal places to display.
            indeterminate: If True, shows an animated indeterminate progress bar.
        """
        ...

    # =====================================================================
    # TitlePane
    # =====================================================================

    @element(sub_tags='*')
    def titlePane(self, title: str | None = None,
                  open: bool = True,
                  duration: int | None = None,
                  **kwargs):
        """A pane with a title that can be opened or collapsed.

        Extended from ContentPane; supports href for remote content loading.

        Args:
            title: Title text displayed in the heading.
            open: If True, the pane is initially open; if False, collapsed.
            duration: Animation duration in milliseconds.
        """
        ...

    # =====================================================================
    # Tooltip
    # =====================================================================

    @element
    def tooltip(self, label: str | None = None,
                connectId: str | list | None = None,
                showDelay: int = 400,
                position: list | None = None,
                **kwargs):
        """A tooltip that pops up a help message when hovering over a node.

        Args:
            label: Text to display in the tooltip (supports HTML).
            connectId: ID (or list of IDs) of nodes to attach the tooltip to.
            showDelay: Milliseconds to wait before showing the tooltip.
            position: List of preferred positions ('above', 'below', 'after', 'before').
        """
        ...

    # =====================================================================
    # ColorPalette
    # =====================================================================

    @element
    def colorPalette(self, palette: str | None = None,
                     **kwargs):
        """A keyboard-accessible color-picking grid widget.

        Can be used standalone or as a popup. Users pick from a grid of colors.

        Args:
            palette: Palette size to use ('7x10' or '3x4').
        """
        ...

    # =====================================================================
    # Editor
    # =====================================================================

    @element(sub_tags='*')
    def editor(self, value: str | None = None,
               plugins: list | None = None,
               extraPlugins: list | None = None,
               height: str | None = None,
               **kwargs):
        """A rich-text editing widget based on an iframe contentEditable area.

        Args:
            value: Initial HTML content.
            plugins: List of plugin names or instances to load.
            extraPlugins: Additional plugins appended to the default set.
            height: Editor height CSS value (e.g. '300px').
        """
        ...

    # =====================================================================
    # Tree
    # =====================================================================

    @element(sub_tags='*')
    def tree(self, model: str | None = None,
             store: str | None = None,
             query: dict | None = None,
             label: str | None = None,
             showRoot: bool = True,
             persist: bool = False,
             **kwargs):
        """Displays hierarchical data from a store as an expandable tree.

        Loads children lazily as the user expands nodes. Technically a forest
        (multiple roots) unless label is specified to create a single root.

        Args:
            model: Data model providing the tree structure.
            store: Data store to query items from (may be removed in Dojo 2.0).
            query: Query object to get top-level children from the store.
            label: Label for a synthetic root node (makes it a single-root tree).
            showRoot: If True, shows the root node; if False, only children are visible.
            persist: If True, saves expand/collapse state in a cookie.
        """
        ...
