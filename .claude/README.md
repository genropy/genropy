# Genropy Project Context

## Code Style Guidelines

### Comments
- **Always write comments in English** for all code in the Genropy project
- This applies to:
  - Python files (`.py`)
  - JavaScript files (`.js`)
  - Documentation
  - Commit messages

### Example
```javascript
// ✅ Good: Use English comments
// Flag to prevent automatic conversions until user actually modifies content
let changeListenerActive = false;

// ❌ Bad: Don't use Italian comments
// Flag per evitare conversioni automatiche finché l'utente non modifica
let changeListenerActive = false;
```

## Project Information

- **Framework**: Genro Web Framework
- **Language**: Python (backend), JavaScript (frontend)
- **Main codebase**: `/Users/dgpaci/sviluppo/gnrenv/genropy`

## Architecture

### Frontend (JavaScript)
- **Location**: `gnrjs/gnr_d11/js/`
- **Main file**: `genro_extra.js` - Contains custom widget implementations
- **Widget system**: Dojo-based declarative widgets
  - `gnr.widgets.MDEditor` - Markdown editor based on Toast UI Editor
  - `gnr.widgets.TinyMCE` - Rich text editor
  - `gnr.widgets.codemirror` - Code editor

### Backend (Python)
- **Structure**: Package-based organization
  - `projects/gnrcore/packages/` - Core packages
  - Each package has:
    - `model/` - Database table definitions
    - `resources/` - Business logic and UI components
    - `resources/tables/` - Table handlers (views, forms)
    - `webpages/` - Web pages

### Key Concepts

#### Datastore and Datapath
- **Datastore**: Client-side reactive data structure
- **Datapath**: Path notation to access data (e.g., `#FORM.record.sourcebag`)
- **Reactive binding**: Use `^` for subscriptions, `=` for one-time reads

#### Forms and Data Binding
- **multiButtonForm**: Component for managing related records
  - `parentForm=True` - Shares parent form context (can cause reactivity conflicts)
  - `datapath` - Isolates form data in specific path
- **dataController**: JavaScript functions that react to data changes
- **Reactivity loops**: Be careful with nested forms and shared datapaths

#### Widgets Pattern
- **creating()**: Initialize widget attributes, extract configuration
- **created()**: Load external resources (JS/CSS libraries)
- **initialize()**: Setup widget with loaded resources
- **attachHooks()**: Wire up event handlers
- **mixin_gnr_***: Methods exposed to external API

### Common Patterns

#### Preventing Automatic Conversions
When implementing editors that transform content (text→HTML, markdown→HTML):
```javascript
attachHooks: function(editor, editor_attrs, sourceNode) {
    let changeListenerActive = false;
    let originalContent = null;

    editor.on('focus', () => {
        if (!changeListenerActive) {
            originalContent = editor.getContent();
            changeListenerActive = true;
        }
    });

    editor.on('blur', () => {
        if (!changeListenerActive) return;

        let newContent = editor.getContent();
        if (newContent !== originalContent) {
            this.setInDatastore(editor, sourceNode);
            originalContent = newContent;
        }
    });
}
```

This prevents unwanted conversions when loading existing data.

### Important Files

- `gnrjs/gnr_d11/js/genro_extra.js` - Custom widget implementations
- `projects/gnrcore/packages/docu/resources/docu_components.py` - Documentation components
- `projects/gnrcore/packages/docu/resources/tables/documentation/th_documentation.py` - Documentation form

### Known Issues & Solutions

#### Issue #288: MDEditor auto-conversion
**Problem**: MDEditor automatically converts text to HTML on load, even without user modifications.

**Solution**: Implemented `changeListenerActive` flag to defer conversion until first user interaction.

**Files affected**:
- `gnrjs/gnr_d11/js/genro_extra.js` (MDEditor widget)

**Branch**: Applied to `feature/mdeditor` and `feature/docu_content`

### Development Tips

1. **Avoid reading files unnecessarily** - Don't explore with Read/Grep, use Task tool with Explore agent
2. **Use specialized tools** - Edit for changes, not bash sed/awk
3. **Watch for form conflicts** - `parentForm=True` + dataControllers can create reactivity loops
4. **Test data loading** - Ensure existing records don't get modified on open
5. **Check git branches** - Solutions may exist in other branches (e.g., TinyMCE fix in `feature/tinymce`)
