# Genropy Learnings

## Framework Architecture

### Layout Components

#### Gridbox
- CSS Grid-based 2D layout container
- Parameters: `columns` (int or CSS template), `gap`, `column_gap`, `row_gap`
- Child items can use `colspan` and `rowspan` for spanning
- `item_*` parameters for consistent styling of all children
- Best for: dashboards, forms, complex 2D layouts

#### Flexbox
- CSS Flexbox-based 1D layout container
- Parameters: `flex_direction`, `flex_wrap`, `justify_content`, `align_items`
- Children can use `flex`, `flex_grow`, `flex_shrink`, `flex_basis`
- Best for: responsive single-direction layouts, toolbars, vertical stacks

#### Formlet
- Modern grid-based form layout (alternative to formbuilder)
- Built on top of gridbox with form-specific features
- Parameters: `cols`/`columns`, `gap`, `item_*` for global field styling
- Uses CSS Grid instead of HTML tables (unlike formbuilder)
- Better for responsive/mobile designs

### Form Components

#### Parameter Inheritance System
**item_* parameters**: Used in formlet/gridbox to set default values for all children
- `item_lbl_side` → inherited as `lbl_side` on each field
- `item_border` → inherited as `border`
- `item_rounded` → inherited as `rounded`
- Implementation: `dictExtract(kwargs, 'item_', pop=False, slice_prefix=True)` extracts all `item_*` params and propagates them

#### Field Widgets

**Checkbox behavior**:
- Has two label parameters: `lbl` (field label) and `label` (checkbox text)
- In formlet (no fbuilder): automatically converts `lbl` to `label` and sets `lbl='&nbsp;'`
- Automatically adds `box__class='formlet_fakelabel'` to hide empty label row
- Code location: `gnrwebstruct.py` line ~2083

**Field creation methods**:
- `.textbox()`, `.checkbox()`, `.dateTextBox()`, etc. for explicit widget types
- `.field()` only works with database tables (TableHandler/resources)
- Use explicit methods when creating fields without database backing

### Code Patterns

#### Using dictExtract
```python
# Extract parameters with a prefix
item_params = dictExtract(kwargs, 'item_', pop=False, slice_prefix=True)
# Returns dict with prefix removed: {'lbl_side': 'top', 'border': '1px solid'}
```

#### Reactive Bindings
- Avoid reactive bindings (`'^.columns'`) on structural parameters (cols, item_*)
- Causes re-rendering and duplicate elements
- Use static values or create separate examples for different configurations

#### labledBox wrapper
- Fields in formlet/formbuilder are wrapped in labledBox for label+content layout
- `box__class='formlet_fakelabel'` hides the label portion
- Used when label is not needed (e.g., checkboxes with their own internal label)

### File Locations

**Core framework**:
- `/gnrpy/gnr/web/gnrwebstruct.py` - Main DOM structure and widget methods

**Documentation**:
- `/docs/genro/webpage_elements/widgets/form_widgets/*.rst`

**Tests**:
- `/projects/gnrcore/packages/test/webpages/gnrwdg/*.py`

### Testing Patterns

**Test structure**:
```python
class GnrCustomWebPage(object):
    py_requires="gnrcomponents/testhandler:TestHandlerFull"

    def test_0_basic(self, pane):
        """Test description"""
        # pane is the container
```

**Avoid**:
- frameForm for simple test examples (too complex)
- Reactive bindings on structural parameters
- save/cancel logic in tests (unnecessary)

**Prefer**:
- Simple pane-based layouts
- Static examples showing different configurations
- Helper methods for repeated patterns (like `_formSection`)

### Bug Fixes Implemented

1. **Checkbox formlet_fakelabel auto-addition**
   - Location: `gnrwebstruct.py` checkbox() method
   - Condition: `lbl and not label and not getattr(self,'fbuilder',None)`
   - Auto-adds `box__class='formlet_fakelabel'` if not already set

2. **item_* parameter propagation**
   - Location: `gnrwebstruct.py` formlet() method
   - Uses `dictExtract()` to extract all `item_*` parameters
   - Propagates as inherited parameters to child fields

3. **lblpos to item_lbl_side conversion**
   - Location: `gnrwebstruct.py` formbuilder_formlet() method
   - Converts formbuilder lblpos ('L','T','R','B') to formlet item_lbl_side

### Best Practices Learned

1. **Don't guess parameters** - Search the codebase for real usage examples
2. **Use dictExtract** - Framework utility for parameter extraction
3. **Check for fbuilder** - Distinguishes formbuilder from formlet context
4. **Icons in Genro** - Use `iconClass='iconbox iconname'`, not text
5. **Field methods** - Use `.textbox()`, not `.field()` without database
6. **Checkbox labels** - Just use `lbl`, not separate `label` parameter in formlet

### Common Mistakes to Avoid

1. Using `box=False` or other made-up parameters
2. Trying to use `.field()` without a database table
3. Adding checkboxes outside formlet to avoid wrapper
4. Not understanding item_* parameter inheritance
5. Using reactive bindings on structural layout parameters
