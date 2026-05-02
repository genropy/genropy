// State / plugins / selections.
import {
    EditorState,
    Plugin,
    PluginKey,
    Transaction,
    Selection,
    TextSelection,
    NodeSelection,
    AllSelection
} from "prosemirror-state";

// View, decorations.
import {
    EditorView,
    Decoration,
    DecorationSet
} from "prosemirror-view";

// Document model.
import {
    Schema,
    Node as PMNode,
    Mark,
    Fragment,
    Slice,
    NodeRange,
    DOMParser,
    DOMSerializer
} from "prosemirror-model";

// Transformations.
import {
    Transform,
    Step,
    ReplaceStep,
    AddMarkStep,
    RemoveMarkStep
} from "prosemirror-transform";

// High-level commands.
import {
    baseKeymap,
    chainCommands,
    toggleMark,
    setBlockType,
    wrapIn,
    lift,
    joinUp,
    joinDown,
    selectAll,
    deleteSelection,
    selectParentNode,
    newlineInCode,
    createParagraphNear,
    liftEmptyBlock,
    splitBlock,
    exitCode
} from "prosemirror-commands";

// Keymap helper.
import { keymap } from "prosemirror-keymap";

// Undo/redo.
import {
    history,
    undo,
    redo,
    undoDepth,
    redoDepth
} from "prosemirror-history";

// Input rules (typing-driven shortcuts: ## -> heading, > -> blockquote, ...).
import {
    inputRules,
    InputRule,
    textblockTypeInputRule,
    wrappingInputRule,
    emDash,
    ellipsis,
    smartQuotes,
    undoInputRule
} from "prosemirror-inputrules";

// Pre-built schemas.
import { schema as basicSchema } from "prosemirror-schema-basic";
import {
    addListNodes,
    orderedList,
    bulletList,
    listItem,
    splitListItem,
    liftListItem,
    sinkListItem
} from "prosemirror-schema-list";

// UI helpers.
import { dropCursor } from "prosemirror-dropcursor";
import { gapCursor } from "prosemirror-gapcursor";

// Menu primitives (toolbar / dropdown / menu items).
import {
    MenuItem,
    Dropdown,
    DropdownSubmenu,
    menuBar,
    blockTypeItem,
    joinUpItem,
    liftItem,
    selectParentNodeItem,
    undoItem,
    redoItem,
    icons,
    wrapItem
} from "prosemirror-menu";

// Pre-baked editor setup: input rules + keymap + menubar wired to the basic
// schema. Mirrors the demo on the prosemirror.net front page.
import {
    exampleSetup,
    buildMenuItems,
    buildKeymap,
    buildInputRules
} from "prosemirror-example-setup";

// Tables: rowspan/colspan with column resizing and header cells.
import {
    tableNodes,
    tableEditing,
    columnResizing,
    goToNextCell,
    addColumnAfter,
    addColumnBefore,
    deleteColumn,
    addRowAfter,
    addRowBefore,
    deleteRow,
    mergeCells,
    splitCell,
    deleteTable,
    toggleHeaderColumn,
    toggleHeaderRow,
    toggleHeaderCell,
    fixTables
} from "prosemirror-tables";

// Trailing node: keep an empty paragraph at the very end so users can always
// click below the last block to position the cursor.
import { trailingNode } from "prosemirror-trailing-node";

// Collab: Operational Transform plugin for multi-user editing. Pairs naturally
// with Genropy SharedObject as the canonical server-side state store.
import {
    collab,
    getVersion,
    sendableSteps,
    receiveTransaction
} from "prosemirror-collab";

// Changeset: produces a diff (inserted / deleted ranges) between two document
// versions, intended for review-mode UIs (track changes, suggestion mode, etc).
import { ChangeSet } from "prosemirror-changeset";

// Compose pre-built schemas:
// - basic               raw schema-basic
// - basicWithLists      basic + bullet/ordered lists
// - basicWithListsAndTables  basic + lists + tables (HTML <table>)
const basicWithListsSchema = new Schema({
    nodes: addListNodes(basicSchema.spec.nodes, "paragraph block*", "block"),
    marks: basicSchema.spec.marks
});

const tableNodesSpec = tableNodes({
    tableGroup: "block",
    cellContent: "block+",
    cellAttributes: {
        background: {
            default: null,
            getFromDOM(dom){ return dom.style.backgroundColor || null; },
            setDOMAttr(value, attrs){
                if(value){ attrs.style = (attrs.style || "") + `background-color: ${value};`; }
            }
        }
    }
});

const basicWithListsAndTablesSchema = new Schema({
    nodes: addListNodes(basicSchema.spec.nodes, "paragraph block*", "block").append(tableNodesSpec),
    marks: basicSchema.spec.marks
});

window.ProseMirror = {
    // state
    EditorState,
    Plugin,
    PluginKey,
    Transaction,
    Selection,
    TextSelection,
    NodeSelection,
    AllSelection,
    // view
    EditorView,
    Decoration,
    DecorationSet,
    // model
    Schema,
    Node: PMNode,
    Mark,
    Fragment,
    Slice,
    NodeRange,
    DOMParser,
    DOMSerializer,
    // transform
    Transform,
    Step,
    ReplaceStep,
    AddMarkStep,
    RemoveMarkStep,
    // commands
    baseKeymap,
    chainCommands,
    toggleMark,
    setBlockType,
    wrapIn,
    lift,
    joinUp,
    joinDown,
    selectAll,
    deleteSelection,
    selectParentNode,
    newlineInCode,
    createParagraphNear,
    liftEmptyBlock,
    splitBlock,
    exitCode,
    // keymap
    keymap,
    // history
    history,
    undo,
    redo,
    undoDepth,
    redoDepth,
    // inputrules
    inputRules,
    InputRule,
    textblockTypeInputRule,
    wrappingInputRule,
    emDash,
    ellipsis,
    smartQuotes,
    undoInputRule,
    // list helpers
    addListNodes,
    orderedList,
    bulletList,
    listItem,
    splitListItem,
    liftListItem,
    sinkListItem,
    // ui
    dropCursor,
    gapCursor,
    // menu primitives (toolbar / dropdown)
    menu: {
        MenuItem,
        Dropdown,
        DropdownSubmenu,
        menuBar,
        blockTypeItem,
        joinUpItem,
        liftItem,
        selectParentNodeItem,
        undoItem,
        redoItem,
        icons,
        wrapItem
    },
    // example-setup: turnkey input rules + keymap + menubar
    exampleSetup,
    buildMenuItems,
    buildKeymap,
    buildInputRules,
    // tables
    tables: {
        tableNodes,
        tableEditing,
        columnResizing,
        goToNextCell,
        addColumnAfter,
        addColumnBefore,
        deleteColumn,
        addRowAfter,
        addRowBefore,
        deleteRow,
        mergeCells,
        splitCell,
        deleteTable,
        toggleHeaderColumn,
        toggleHeaderRow,
        toggleHeaderCell,
        fixTables
    },
    // trailing node
    trailingNode,
    // collab (Operational Transform: pair with Genropy SharedObject server-side)
    collab: {
        collab,
        getVersion,
        sendableSteps,
        receiveTransaction
    },
    // changeset (diff between document versions, for review/suggestion mode)
    ChangeSet,
    // pre-built schemas
    schemas: {
        basic: basicSchema,
        basicWithLists: basicWithListsSchema,
        basicWithListsAndTables: basicWithListsAndTablesSchema
    }
};
