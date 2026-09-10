# Raylib Python Text Layout and Grouping

## 1. Purpose

This document specifies a small retained-mode text layout system built on top of Raylib's drawing API.

The system exists to solve one problem:

> Allow multiple text elements to be treated as a single structured object, with automatic positioning and styling, instead of manually calculating coordinates for every `DrawText()` call.

The implementation must separate three concerns:

1. **Text data** — what text exists and how it is styled.
2. **Layout** — where each text element belongs.
3. **Rendering** — drawing already-positioned elements through Raylib.

The first implementation is intentionally limited to text and text groups.

---

## 2. Design Goals

The system must provide:

* Hierarchical text groups.
* Relative coordinates.
* Automatic vertical and horizontal layouts.
* Padding.
* Gap between children.
* Horizontal and vertical alignment.
* Text measurement.
* Basic text wrapping.
* Style inheritance.
* Visibility.
* Layout invalidation.
* A deterministic layout pass.

The system should make this possible:

```python
panel = TextGroup(
    x=100,
    y=100,
    width=400,
    padding=16,
    gap=8,
    direction="vertical",
)

panel.add(Text("Hello"))
panel.add(Text("This is some text."))
panel.add(Text("Goodbye"))

panel.layout()
panel.draw()
```

The caller should not need to manually calculate the Y coordinate of each child.

---

## 3. Explicit Non-Goals

The initial implementation does not include:

* Buttons.
* Mouse input.
* Keyboard input.
* Focus management.
* Animation.
* Scrolling.
* Automatic resizing of the application window.
* Flexbox.
* CSS.
* Constraint solving.
* Text editing.
* Rich text within one `Text` object.
* Automatic widget event propagation.

Those can be built on top of this system later.

Do not implement them as hidden dependencies of the basic layout system.

---

## 4. Core Object Model

The system consists of three primary types:

```text
UIElement
    |
    +-- Text
    |
    +-- TextGroup
```

`UIElement` provides properties common to all elements.

`Text` represents a drawable piece of text.

`TextGroup` contains other `UIElement` objects and determines their positions.

A group may contain another group:

```text
Root
└── Group
    ├── Text
    ├── Text
    └── Group
        ├── Text
        └── Text
```

This hierarchy is important because it allows a complete section of UI to be moved by changing one group's position.

---

## 5. Coordinate System

Every element has a local position:

```python
x
y
```

The position is relative to its parent.

For a root element:

```text
absolute_x = x
absolute_y = y
```

For a child:

```text
absolute_x = parent.absolute_x + child.x
absolute_y = parent.absolute_y + child.y
```

Therefore:

```text
Root at (100, 50)

Group at (20, 30)
    Text at (10, 5)
```

results in:

```text
Text absolute position = (130, 85)
```

The implementation may alternatively store absolute coordinates during layout, but the externally observable model must behave as though positions are relative to the parent.

---

## 6. UIElement

The base class should conceptually contain:

```python
class UIElement:
    parent: UIElement | None

    x: float
    y: float

    width: float
    height: float

    visible: bool

    dirty: bool
```

It must provide:

```python
layout()
draw()
mark_dirty()
```

`UIElement` does not determine its own layout policy.

That is the responsibility of the concrete element or its parent.

---

## 7. Text

A `Text` object represents one logical text element.

Minimum properties:

```python
class Text(UIElement):
    content: str

    font
    font_size: float

    color
    spacing: float

    wrap: bool
    max_width: float | None
```

Example:

```python
Text(
    "Hello world",
    font=font,
    font_size=24,
)
```

The text element is responsible for determining its own dimensions.

For unwrapped text:

```text
width  = measured text width
height = font line height
```

For wrapped text:

```text
width  = available width
height = number_of_lines * line_height
```

The exact line-height calculation should be centralized rather than independently implemented by every caller.

---

## 8. Text Measurement

Raylib is responsible for determining the actual dimensions of rendered text.

The UI system should expose a wrapper around Raylib's text measurement functionality.

Conceptually:

```python
width = measure_text(...)
```

The `Text` class should cache its measured dimensions until something affecting measurement changes.

Measurement must be invalidated when:

```text
content changes
font changes
font size changes
spacing changes
wrapping configuration changes
maximum width changes
```

Example:

```python
text.content = "New content"
text.mark_dirty()
```

The next layout pass recalculates its dimensions.

---

## 9. TextGroup

`TextGroup` is the primary grouping and layout object.

Minimum properties:

```python
class TextGroup(UIElement):
    children: list[UIElement]

    direction: "vertical" | "horizontal"

    padding_left: float
    padding_right: float
    padding_top: float
    padding_bottom: float

    gap: float

    horizontal_align: "left" | "center" | "right"
    vertical_align: "top" | "center" | "bottom"
```

It also owns a default text style.

---

## 10. Adding and Removing Children

The group must provide:

```python
group.add(element)
group.remove(element)
```

When an element is added:

```python
element.parent = group
group.mark_dirty()
```

When an element is removed:

```python
element.parent = None
group.mark_dirty()
```

The group owns the ordering of its children.

Therefore:

```python
group.add(a)
group.add(b)
group.add(c)
```

means the layout order is:

```text
a
b
c
```

---

## 11. Layout Responsibilities

`layout()` is the only operation responsible for calculating child positions.

It must:

1. Ensure children have valid dimensions.
2. Calculate the position of every child.
3. Calculate the group's resulting dimensions when its dimensions are content-driven.
4. Propagate layout into child groups.
5. Clear the dirty state.

`draw()` must not perform layout calculations.

This separation is mandatory.

Correct:

```python
group.layout()
group.draw()
```

Incorrect:

```python
group.draw()  # secretly calculates positions
```

---

## 12. Vertical Layout

For a vertical group, children are placed from top to bottom.

Given:

```text
group.y
padding_top
gap
```

the first child's Y coordinate is:

```text
group.y + padding_top
```

The next child's Y coordinate is:

```text
previous_child.y
+ previous_child.height
+ gap
```

Conceptually:

```python
cursor_y = padding_top

for child in children:
    child.y = cursor_y
    cursor_y += child.height + gap
```

After all children have been placed:

```text
content_height =
    sum(child.height)
    + gap * (child_count - 1)
```

The group's total required height is:

```text
height =
    padding_top
    + content_height
    + padding_bottom
```

If there are zero children, the gap contribution is zero.

---

## 13. Horizontal Layout

For a horizontal group, children are placed from left to right.

Conceptually:

```python
cursor_x = padding_left

for child in children:
    child.x = cursor_x
    cursor_x += child.width + gap
```

The required width is:

```text
width =
    padding_left
    + sum(child.width)
    + gap * (child_count - 1)
    + padding_right
```

Again, no gap is added when there are zero or one children.

---

## 14. Alignment

Alignment only applies along the axis perpendicular to the group's layout direction.

For a vertical group, horizontal alignment controls the X position.

For a horizontal group, vertical alignment controls the Y position.

## Vertical group

Given:

```text
available_width
child_width
```

left:

```text
child.x = padding_left
```

center:

```text
child.x =
    padding_left
    + (available_width - padding_left - padding_right - child.width) / 2
```

right:

```text
child.x =
    available_width
    - padding_right
    - child.width
```

### Horizontal group

Given:

```text
available_height
child_height
```

top:

```text
child.y = padding_top
```

center:

```text
child.y =
    padding_top
    + (available_height - padding_top - padding_bottom - child.height) / 2
```

bottom:

```text
child.y =
    available_height
    - padding_bottom
    - child.height
```

The formulas must never produce positions outside the group's intended content area unless the element itself is larger than that area.

---

## 15. Group Dimensions

A group can operate in one of two ways:

```text
fixed dimension
content dimension
```

For example:

```python
TextGroup(
    width=400,
    height=None,
)
```

means the width is fixed while height may be calculated from its children.

The initial implementation should support this distinction explicitly.

A practical representation is:

```python
width: float | None
height: float | None
```

where:

```text
None = content-driven
number = fixed
```

For example:

```python
TextGroup(width=400)
```

allows the group to know its available width, which is important for text wrapping.

---

## 16. Layout Order

Layout must happen in this order:

```text
1. Determine available group dimensions.
2. Layout children that require measurement.
3. Obtain child dimensions.
4. Calculate child positions.
5. Calculate content-driven group dimensions.
6. Repeat child positioning if the newly calculated group dimension affects alignment.
7. Mark the group clean.
```

For the first implementation, avoid complicated circular dependencies.

In particular:

> A child's width must not depend on the group's automatically calculated width when the group's width itself depends on that child's width.

When such a dependency exists, the caller must provide the relevant fixed dimension.

This is especially important for wrapping.

---

## 17. Text Wrapping

Wrapping belongs to `Text`, not `TextGroup`.

A group provides an available width.

A text element decides how its content fits inside that width.

For example:

```python
group = TextGroup(width=400)

group.add(
    Text(
        "A very long sentence...",
        wrap=True,
    )
)
```

During layout, the text receives an available width of approximately:

```text
400 - left_padding - right_padding
```

The text then determines:

```text
line 1
line 2
line 3
...
```

and calculates its height accordingly.

The group treats the resulting text dimensions as ordinary child dimensions.

---

## 18. Style Inheritance

A group may provide default style values.

For example:

```python
group = TextGroup(
    font=font,
    font_size=20,
    color=WHITE,
)
```

A child without an explicit value inherits the group's value.

Conceptually:

```text
Text.font
    ↓
if unset:
    Parent.font
        ↓
if unset:
    Root/default font
```

The same mechanism may apply to:

```text
font
font_size
color
spacing
```

The initial implementation should use simple inheritance.

Do not implement CSS-like cascading rules.

---

## 19. Visibility

Every element has:

```python
visible: bool
```

If an element is invisible:

```python
visible == False
```

it must not be rendered.

A group's visibility applies to its entire subtree.

Therefore:

```python
group.visible = False
```

causes all descendants to be skipped during drawing.

Visibility does not automatically remove an element from layout.

This distinction matters.

For the initial implementation, an invisible element still occupies layout space.

If later required, a separate `display`/`layout_enabled` concept can be introduced.

---

## 20. Rendering

Rendering must operate on the results produced by layout.

Conceptually:

```python
def draw(self):
    if not self.visible:
        return

    for child in self.children:
        child.draw()
```

A `Text` draws itself using its calculated position and resolved style.

A `TextGroup` does not draw anything by itself unless a future background/border feature is added.

Therefore:

```text
layout()
    calculates state

draw()
    consumes state
```

---

## 21. Dirty State

Layout should not necessarily execute every frame.

Every element has:

```python
dirty: bool
```

An element becomes dirty when something changes that can affect its size or position.

Examples:

```text
text content changed
font changed
font size changed
group size changed
padding changed
gap changed
alignment changed
direction changed
child added
child removed
```

`mark_dirty()` must propagate upward.

For example:

```text
Text
  ↓
Group A
  ↓
Group B
```

If the text changes:

```text
Text.mark_dirty()
        ↓
Group A becomes dirty
        ↓
Group B becomes dirty
```

This is necessary because a child's size can affect the position of siblings and therefore the size of its ancestors.

---

## 22. Layout Pass

The root UI object should be laid out before rendering.

A typical frame should look like:

```python
ui.update()

if ui.dirty:
    ui.layout()

begin_drawing()

ui.draw()

end_drawing()
```

`update()` is optional for the basic text system and exists as an extension point.

The essential sequence is:

```text
change state
    ↓
mark dirty
    ↓
layout
    ↓
draw
```

---

## 23. Recommended Initial API

The first usable API should remain small.

```python
class UIElement:
    def layout(self):
        ...

    def draw(self):
        ...

    def mark_dirty(self):
        ...


class Text(UIElement):
    def __init__(
        self,
        content,
        *,
        font=None,
        font_size=None,
        color=None,
        spacing=None,
        wrap=False,
        max_width=None,
    ):
        ...


class TextGroup(UIElement):
    def __init__(
        self,
        *,
        x=0,
        y=0,
        width=None,
        height=None,
        direction="vertical",
        gap=0,
        padding=0,
        horizontal_align="left",
        vertical_align="top",
        **style,
    ):
        ...

    def add(self, child):
        ...

    def remove(self, child):
        ...
```

`padding` may initially be a single value:

```python
padding=16
```

and internally become:

```text
padding_left   = 16
padding_right  = 16
padding_top    = 16
padding_bottom = 16
```

A later API can allow four independent values.

---

## 24. Example

Given:

```python
group = TextGroup(
    x=100,
    y=100,
    width=400,
    direction="vertical",
    gap=10,
    padding=20,
    horizontal_align="center",
)

group.add(Text("Hello", font_size=24))
group.add(Text("World", font_size=24))
group.add(Text("This is a longer piece of text.", font_size=18))

group.layout()
group.draw()
```

The layout process is conceptually:

```text
Group:
    absolute position = (100, 100)
    width = 400
    padding = 20
    gap = 10

Available content width:
    400 - 20 - 20
    = 360
```

The children are measured.

Suppose their resulting dimensions are:

```text
Hello:
    60 × 28

World:
    65 × 28

This is a longer piece of text.:
    250 × 22
```

Their vertical positions become:

```text
Hello:
    y = 120

World:
    y = 158

Long text:
    y = 196
```

because:

```text
120 + 28 + 10 = 158
158 + 28 + 10 = 196
```

Because the group uses centered horizontal alignment, their X positions are calculated independently from their widths.

The renderer then simply draws them at those calculated positions.

---

## 25. Implementation Order

Implementation should follow this order.

### Phase 1 — Base element

Implement:

```text
UIElement
parent
x/y
width/height
visible
dirty
mark_dirty()
```

Do not implement wrapping or alignment yet.

### Phase 2 — Text

Implement:

```text
content
font
font size
color
measurement
draw()
```

Verify that a single `Text` can correctly report its dimensions and render itself.

### Phase 3 — Grouping

Implement:

```text
children
add()
remove()
vertical layout
```

Verify:

```text
Text
Text
Text
```

automatically stack vertically.

### Phase 4 — Horizontal layout

Add:

```text
direction="horizontal"
```

and verify horizontal stacking.

### Phase 5 — Padding and gap

Add:

```text
padding
gap
```

These should modify layout calculations only.

### Phase 6 — Alignment

Add:

```text
horizontal_align
vertical_align
```

Implement only the alignment rules defined in this document.

### Phase 7 — Style inheritance

Add inherited:

```text
font
font_size
color
spacing
```

### Phase 8 — Wrapping

Add text wrapping after fixed group dimensions work correctly.

### Phase 9 — Dirty layout

Add invalidation and cached measurements.

Only after the previous phases work should layout caching be introduced.

---

## 26. Invariants

The implementation should maintain these invariants.

A child always has either:

```text
parent == None
```

or:

```text
child.parent == containing_group
```

A group's children are always laid out in list order.

`draw()` never changes layout coordinates.

`layout()` does not perform rendering.

Changing a property that affects layout marks the appropriate element dirty.

A clean element may be skipped by the layout system.

An invisible element is skipped by rendering.

A group may contain another group.

A child group's local coordinates remain relative to that group.

---

## 27. What `layout()` Means

The implementation should treat `layout()` as a deterministic transformation:

```text
Input:
    element hierarchy
    element sizes
    group dimensions
    padding
    gap
    alignment
    layout direction

Output:
    positions
    dimensions
```

It is therefore useful to think of the system as:

```text
                 ┌──────────────┐
                 │ Element Tree │
                 └──────┬───────┘
                        │
                        ▼
                 ┌──────────────┐
                 │    layout()  │
                 └──────┬───────┘
                        │
                        ▼
              ┌────────────────────┐
              │ Calculated Geometry │
              └─────────┬──────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │    draw()    │
                 └──────┬───────┘
                        │
                        ▼
                     Raylib
```

This is the central architecture.

The layout system owns geometry.

Raylib owns rendering.

The application owns the semantic content.

---

## 28. Extension Boundary

Future functionality should extend this model rather than modifying the meaning of existing operations.

For example:

```text
TextGroup
    ↓
ScrollGroup
    ↓
Panel
    ↓
Button
```

can eventually be implemented as additional element types.

Likewise, additional layout algorithms can be introduced:

```text
VerticalLayout
HorizontalLayout
GridLayout
AbsoluteLayout
```

without changing what `Text` means.

The initial implementation should therefore avoid embedding application-specific behavior into `TextGroup`.

---

## 29. Final Architecture

The resulting system should have a clear division of responsibility:

```text
Text
    Owns:
        content
        text measurement
        text rendering
        text style

TextGroup
    Owns:
        children
        layout direction
        spacing
        padding
        alignment
        inherited defaults

UIElement
    Owns:
        hierarchy relationship
        geometry
        visibility
        dirty state

Application
    Owns:
        what elements exist
        what their content means
        when their properties change

Raylib
    Owns:
        actual rendering
```

The key principle is simple:

> Construct a tree describing what should exist, run a layout pass that determines where everything belongs, then render the resulting geometry.

That is the entire foundation. Everything else should be added only when there is an actual requirement for it.
