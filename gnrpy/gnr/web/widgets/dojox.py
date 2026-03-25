"""GenroPy dojox widgets — FloatingPane, Gallery, Grid, etc.

Formal documentation of the dojoxNS widgets available on GnrDomSrc.
These methods are generated at runtime via __getattr__ -> child(tag, **kwargs).
"""
from __future__ import annotations
from genro_bag.lib.element import element


class DojoxWidgets:
    """Mixin documenting Dojo Extended (dojox) widgets."""

    # --- dojox.layout ---

    @element(sub_tags='*')
    def floatingPane(self, title: str | None = None,
                     closable: bool = True,
                     dockable: bool = True,
                     resizable: bool = False,
                     maxable: bool = False,
                     resizeAxis: str | None = None,
                     dockTo: str | None = None,
                     duration: int | None = None,
                     contentClass: str | None = None,
                     **kwargs):
        """Non-modal floating window pane, draggable by title bar.

        Args:
            title: Title displayed in the header bar.
            closable: Allow closure of this pane.
            dockable: Allow minimizing (docking) of the pane.
            resizable: Allow resizing of the pane.
            maxable: Allow maximizing the pane to fill the viewport.
            resizeAxis: Resize direction constraint ('x', 'y', or 'xy').
            dockTo: Id of the Dock widget to minimize into.
            duration: Time in ms for toggle animation.
            contentClass: CSS class applied to inner content node.
        """
        ...

    @element
    def dock(self, autoPosition: str | None = None,
             **kwargs):
        """Dock widget that tracks minimized FloatingPanes and handles their layout.

        Args:
            autoPosition: Position of the dock ('south' for bottom of viewport).
        """
        ...

    @element(sub_tags='*')
    def radioGroup(self, duration: int | None = None,
                   hasButtons: bool = True,
                   **kwargs):
        """StackContainer that transitions between children on hover of generated buttons.

        Args:
            duration: Animation duration in ms for Fade/Slide variants.
            hasButtons: If True, generates internal hover buttons for each child.
        """
        ...

    @element
    def resizeHandle(self, targetId: str | None = None,
                     targetContainer: str | None = None,
                     resizeAxis: str | None = None,
                     activeResize: bool = False,
                     activeResizeClass: str | None = None,
                     animateSizing: bool = True,
                     animateMethod: str | None = None,
                     animateDuration: int | None = None,
                     minHeight: int | None = None,
                     minWidth: int | None = None,
                     **kwargs):
        """Draggable handle to resize an attached node.

        Args:
            targetId: Id of the Widget or DomNode to resize.
            targetContainer: Direct DomNode reference to resize (overrides targetId).
            resizeAxis: Axis constraint ('x', 'y', or 'xy').
            activeResize: If True, node resizes in realtime with mouse movement.
            activeResizeClass: CSS class for the virtual resize clone node.
            animateSizing: If True, animate to new size on mouseUp (only when activeResize is False).
            animateMethod: Animation style ('chain' or 'combine').
            animateDuration: Animation duration in ms.
            minHeight: Minimum height in px.
            minWidth: Minimum width in px.
        """
        ...

    @element(sub_tags='*')
    def sizingPane(self, **kwargs):
        """Dojox SizingPane layout widget."""
        ...

    @element(sub_tags='*')
    def borderContainer(self, **kwargs):
        """Dojox BorderContainer (deprecated, moved to dijit.layout.BorderContainer)."""
        ...

    @element(sub_tags='*')
    def scrollPane(self, orientation: str | None = None,
                   **kwargs):
        """Pane that scrolls its content based on relative mouse position.

        Args:
            orientation: Scroll direction ('horizontal' or 'vertical').
        """
        ...

    # --- dojox.widget ---

    @element(sub_tags='*')
    def fisheyeList(self, itemWidth: int | None = None,
                    itemHeight: int | None = None,
                    itemMaxWidth: int | None = None,
                    itemMaxHeight: int | None = None,
                    orientation: str | None = None,
                    isFixed: bool = False,
                    conservativeTrigger: bool = False,
                    effectUnits: int | None = None,
                    itemPadding: int | None = None,
                    attachEdge: str | None = None,
                    labelEdge: str | None = None,
                    **kwargs):
        """Mac OS-style fisheye menu with icon magnification on hover.

        Args:
            itemWidth: Dormant item width in px.
            itemHeight: Dormant item height in px.
            itemMaxWidth: Fully enlarged item width in px.
            itemMaxHeight: Fully enlarged item height in px.
            orientation: Layout direction ('horizontal' or 'vertical').
            isFixed: If True, adds window scroll listener for fixed positioning.
            conservativeTrigger: If True, enlarge only when mouse is over an item.
            effectUnits: How much reaction the menu makes relative to mouse distance.
            itemPadding: Padding in px between each menu item.
            attachEdge: Border that items expand from ('center','left','right','top','bottom').
            labelEdge: Position of labels relative to icons ('center','left','right','top','bottom').
        """
        ...

    @element
    def loader(self, loadIcon: str | None = None,
               loadMessage: str | None = None,
               hasVisuals: bool = True,
               attachToPointer: bool = True,
               duration: int | None = None,
               **kwargs):
        """Global XHR listener that displays a loading indicator during requests.

        Args:
            loadIcon: URL to the loading icon image.
            loadMessage: Text to display during loading.
            hasVisuals: If True, shows a fixed loading message in the corner.
            attachToPointer: If True, shows indicator near the mouse cursor.
            duration: Time in ms to toggle the visual indicator in/out.
        """
        ...

    @element
    def toaster(self, messageTopic: str | None = None,
                defaultType: str | None = None,
                positionDirection: str | None = None,
                duration: int | None = None,
                separator: str | None = None,
                **kwargs):
        """Notification message that slides in from a screen corner.

        Args:
            messageTopic: Topic name; messages published here are displayed.
            defaultType: Default message type ('message','warning','error','fatal').
            positionDirection: Slide-in origin ('br-up','br-left','bl-up','bl-right',
                'tr-down','tr-left','tl-down','tl-right').
            duration: Time in ms to show the message.
            separator: HTML string to separate consecutive messages.
        """
        ...

    @element
    def fileInput(self, label: str | None = None,
                  cancelText: str | None = None,
                  name: str | None = None,
                  **kwargs):
        """Styled file input with browse button and cancel control.

        Args:
            label: Text label on the browse button.
            cancelText: Text label on the cancel button.
            name: Name attribute for the file input field.
        """
        ...

    @element
    def fileInputBlind(self, url: str | None = None,
                       blurDelay: int | None = None,
                       duration: int | None = None,
                       uploadMessage: str | None = None,
                       label: str | None = None,
                       cancelText: str | None = None,
                       name: str | None = None,
                       **kwargs):
        """File input that shows only a button (no visible text field), with background upload.

        Args:
            url: URL for background file upload.
            blurDelay: Time in ms before upload starts after losing focus.
            duration: Animation duration in ms.
            uploadMessage: Text shown during upload progress.
            label: Text label on the browse button.
            cancelText: Text label on the cancel button.
            name: Name attribute for the file input field.
        """
        ...

    @element
    def fileInputAuto(self, url: str | None = None,
                      blurDelay: int | None = None,
                      duration: int | None = None,
                      uploadMessage: str | None = None,
                      label: str | None = None,
                      cancelText: str | None = None,
                      name: str | None = None,
                      **kwargs):
        """File input with automatic background upload on blur.

        Args:
            url: URL for background file upload.
            blurDelay: Time in ms before upload starts after losing focus.
            duration: Animation duration in ms.
            uploadMessage: Text shown during upload progress.
            label: Text label on the browse button.
            cancelText: Text label on the cancel button.
            name: Name attribute for the file input field.
        """
        ...

    @element
    def colorPicker(self, showRgb: bool = True,
                    showHsv: bool = True,
                    showHex: bool = True,
                    webSafe: bool = True,
                    animatePoint: bool = True,
                    slideDuration: int | None = None,
                    **kwargs):
        """HSV color picker similar to Photoshop's color selection tool.

        Args:
            showRgb: Show/update RGB input fields.
            showHsv: Show/update HSV input fields.
            showHex: Show/update hex value field.
            webSafe: Show web-safe color preview.
            animatePoint: If True, animate cursor movement on click.
            slideDuration: Animation duration in ms when animatePoint is True.
        """
        ...

    @element(sub_tags='*')
    def sortList(self, title: str | None = None,
                 heading: str | None = None,
                 descending: bool = True,
                 sortable: bool = True,
                 store: str | None = None,
                 key: str | None = None,
                 **kwargs):
        """Sortable unordered list with a fixed header.

        Args:
            title: Title displayed in the header.
            heading: Alternate title for parent container (TabContainer, AccordionContainer).
            descending: If True, sort in descending order.
            sortable: Enable/disable sorting.
            store: Data store reference name.
            key: Attribute name to use from the store.
        """
        ...

    @element
    def timeSpinner(self, required: bool = False,
                    smallDelta: int | None = None,
                    largeDelta: int | None = None,
                    value: str | None = None,
                    **kwargs):
        """Spinner widget for time component of a date, using minute increments.

        Args:
            required: If True, the field is required.
            smallDelta: Minute increment for small step (default 5).
            largeDelta: Minute increment for large step (default 30).
            value: Initial time value string (e.g. '12:00 AM').
        """
        ...

    @element(sub_tags='*')
    def iterator(self, store: str | None = None,
                 query: str | None = None,
                 data: str | None = None,
                 start: int | None = None,
                 fetchMax: int | None = None,
                 defaultValue: str | None = None,
                 **kwargs):
        """Repeater widget that iterates over store items or data arrays using a template.

        Args:
            store: Data store providing the items.
            query: Query object for the store fetch.
            data: Direct array of objects or strings to iterate.
            start: Start index for fetching.
            fetchMax: Maximum number of items to fetch.
            defaultValue: Default value for missing attributes.
        """
        ...

    # --- dojox.image ---

    @element(sub_tags='*')
    def gallery(self, imageHeight: int | None = None,
                imageWidth: int | None = None,
                pageSize: int | None = None,
                autoLoad: bool = True,
                linkAttr: str | None = None,
                imageThumbAttr: str | None = None,
                imageLargeAttr: str | None = None,
                titleAttr: str | None = None,
                slideshowInterval: int | None = None,
                **kwargs):
        """Image gallery combining a ThumbnailPicker and SlideShow.

        Args:
            imageHeight: Maximum image height in px in the slideshow.
            imageWidth: Maximum image width in px in the slideshow.
            pageSize: Number of records to retrieve from the store per request.
            autoLoad: If True, preload images before the user views them.
            linkAttr: Store attribute name for image link URL.
            imageThumbAttr: Store attribute name for thumbnail URL.
            imageLargeAttr: Store attribute name for full-size image URL.
            titleAttr: Store attribute name for image title.
            slideshowInterval: Seconds between automatic image transitions.
        """
        ...

    @element
    def lightbox(self, group: str | None = None,
                 title: str | None = None,
                 href: str | None = None,
                 duration: int | None = None,
                 **kwargs):
        """Modal lightbox for displaying images with keyboard navigation.

        Args:
            group: Group name to create slideshow-like navigation among images.
            title: Caption text shown beneath the image.
            href: URL of the image to display.
            duration: Animation duration in ms.
        """
        ...

    @element
    def slideShow(self, imageHeight: int | None = None,
                  imageWidth: int | None = None,
                  title: str | None = None,
                  titleTemplate: str | None = None,
                  noLink: bool = False,
                  loop: bool = True,
                  hasNav: bool = True,
                  pageSize: int | None = None,
                  autoLoad: bool = True,
                  autoStart: bool = False,
                  fixedHeight: bool = False,
                  imageStore: str | None = None,
                  linkAttr: str | None = None,
                  imageLargeAttr: str | None = None,
                  titleAttr: str | None = None,
                  slideshowInterval: int | None = None,
                  **kwargs):
        """Image slideshow widget with automatic and manual navigation.

        Args:
            imageHeight: Maximum image height in px.
            imageWidth: Maximum image width in px.
            title: Initial slideshow title.
            titleTemplate: Template for title text (supports ${title}, ${current}, ${total}).
            noLink: If True, disable anchor link around the displayed image.
            loop: If True, loop back to the first image after the last.
            hasNav: Show/hide visual navigation controls.
            pageSize: Number of images to request per batch.
            autoLoad: If True, preload images before viewing.
            autoStart: If True, start the slideshow immediately.
            fixedHeight: If True, widget height stays fixed regardless of image size.
            imageStore: Data store implementing dojo.data Read API.
            linkAttr: Store attribute name for image link URL.
            imageLargeAttr: Store attribute name for full-size image URL.
            titleAttr: Store attribute name for image title.
            slideshowInterval: Seconds between automatic transitions.
        """
        ...

    @element
    def thumbnailPicker(self, imageStore: str | None = None,
                        request: str | None = None,
                        size: int | None = None,
                        thumbHeight: int | None = None,
                        thumbWidth: int | None = None,
                        useLoadNotifier: bool = False,
                        useHyperlink: bool = False,
                        hyperlinkTarget: str | None = None,
                        isClickable: bool = True,
                        isScrollable: bool = True,
                        isHorizontal: bool = True,
                        autoLoad: bool = True,
                        linkAttr: str | None = None,
                        imageThumbAttr: str | None = None,
                        **kwargs):
        """Scrolling thumbnail picker for navigating image collections.

        Args:
            imageStore: Data store implementing dojo.data Read API.
            request: Dojo data Read API request object.
            size: Width or height in px (depending on orientation).
            thumbHeight: Default thumbnail height in px.
            thumbWidth: Default thumbnail width in px.
            useLoadNotifier: If True, show colored DIV under each thumb for loading status.
            useHyperlink: If True, clicking a thumbnail opens its link.
            hyperlinkTarget: 'new' to open in new window, else current window.
            isClickable: If True, show pointer cursor over thumbnails.
            isScrollable: If True, use smooth scrolling between pages.
            isHorizontal: If True, layout thumbnails horizontally.
            autoLoad: If True, preload thumbnail images.
            linkAttr: Store attribute name for link URL.
            imageThumbAttr: Store attribute name for thumbnail URL.
        """
        ...

    # --- dojox.charting ---

    @element
    def chart(self, **kwargs):
        """Dojox charting widget placeholder for Chart2D/Chart3D integration."""
        ...

    # --- dojox.presentation ---

    @element(sub_tags='*')
    def deck(self, fullScreen: bool = True,
             useNav: bool = True,
             navDuration: int | None = None,
             noClick: bool = False,
             setHash: bool = True,
             **kwargs):
        """Presentation deck — a StackContainer with slide transitions and keyboard control.

        Args:
            fullScreen: If True, presentation takes over the full window.
            useNav: If True, show navigation popup with prev/next controls.
            navDuration: Fade duration in ms for the navigation popup.
            noClick: If True, disable click-to-advance (keyboard/auto only).
            setHash: If True, update URL hash with current slide number.
        """
        ...

    @element(sub_tags='*')
    def slide(self, title: str | None = None,
              noClick: bool = False,
              **kwargs):
        """Single slide within a presentation Deck.

        Args:
            title: Slide title displayed in the header.
            noClick: If True, disable click-to-advance on this slide.
        """
        ...

    # --- dojox.geo ---

    @element
    def googleMap(self, **kwargs):
        """Google Maps integration widget."""
        ...

    @element
    def googleChart(self, **kwargs):
        """Google Chart API visualization widget."""
        ...

    @element
    def googleVisualization(self, **kwargs):
        """Google Visualization API widget."""
        ...

    # --- dojox.grid ---

    @element
    def dojoGrid(self, model: str | None = None,
                 structure: str | None = None,
                 rowCount: int | None = None,
                 rowsPerPage: int | None = None,
                 autoWidth: bool = False,
                 autoHeight: bool = False,
                 autoRender: bool = True,
                 defaultHeight: str | None = None,
                 elasticView: int | None = None,
                 singleClickEdit: bool = False,
                 keepRows: int | None = None,
                 **kwargs):
        """Dojox data-bound grid with virtual scrolling and cell editing.

        Args:
            model: Data model (string name or object).
            structure: View layout definition (object or string name).
            rowCount: Number of rows to display.
            rowsPerPage: Number of rows to render per page.
            autoWidth: If True, grid width auto-fits the data.
            autoHeight: If True, grid height auto-fits the data.
            autoRender: If True, grid renders itself after initialization.
            defaultHeight: Default grid height as CSS value (e.g. '15em').
            elasticView: Index of the view to make elastic (fills available space).
            singleClickEdit: If True, single click starts cell editing.
            keepRows: Number of rows to keep in the rendering cache.
        """
        ...

    @element
    def virtualGrid(self, structure: str | None = None,
                    rowCount: int | None = None,
                    rowsPerPage: int | None = None,
                    autoWidth: bool = False,
                    autoHeight: bool = False,
                    autoRender: bool = True,
                    defaultHeight: str | None = None,
                    elasticView: int | None = None,
                    singleClickEdit: bool = False,
                    keepRows: int | None = None,
                    **kwargs):
        """Virtual scrolling grid without direct data store binding.

        Args:
            structure: View layout definition (object or string name).
            rowCount: Number of rows to display.
            rowsPerPage: Number of rows to render per page.
            autoWidth: If True, grid width auto-fits the data.
            autoHeight: If True, grid height auto-fits the data.
            autoRender: If True, grid renders itself after initialization.
            defaultHeight: Default grid height as CSS value (e.g. '15em').
            elasticView: Index of the view to make elastic (fills available space).
            singleClickEdit: If True, single click starts cell editing.
            keepRows: Number of rows to keep in the rendering cache.
        """
        ...

    @element
    def virtualStaticGrid(self, structure: str | None = None,
                          rowCount: int | None = None,
                          rowsPerPage: int | None = None,
                          autoWidth: bool = False,
                          autoHeight: bool = False,
                          autoRender: bool = True,
                          defaultHeight: str | None = None,
                          **kwargs):
        """GenroPy wrapper around VirtualGrid for static data display.

        Args:
            structure: View layout definition (object or string name).
            rowCount: Number of rows to display.
            rowsPerPage: Number of rows to render per page.
            autoWidth: If True, grid width auto-fits the data.
            autoHeight: If True, grid height auto-fits the data.
            autoRender: If True, grid renders itself after initialization.
            defaultHeight: Default grid height as CSS value (e.g. '15em').
        """
        ...

    # --- mywidgets (registered via dojox namespace) ---

    @element
    def calendar(self, **kwargs):
        """Calendar date picker widget."""
        ...
