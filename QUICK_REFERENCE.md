# Developer Quick Reference: UI Responsiveness System

## For Game Logic Integration

### Emitting a Piece Capture Event
When a piece is captured, emit the `PieceCapturedEvent` event:

```python
from utils.signals import bus
from utils.events import PieceCapturedEvent

# After validating capture:
bus.emit(PieceCapturedEvent(
    piece_type="pawn",    # One of: pawn, knight, bishop, rook, queen, king
    captured_by="white"   # The player who captured it
))
```

The system automatically:
1. Animates the piece from board to captured area (200ms)
2. Updates the CapturedPiecesModel
3. Re-renders the captured pieces display with animation

### Subscribing to Layout Changes
If a component needs to respond to layout type transitions:

```python
from utils.signals import bus
from utils.events import LayoutChangedEvent

def handle_layout_change(event: LayoutChangedEvent):
    print(f"Layout changed: {event.from_layout} → {event.to_layout}")
    # Handle new layout as needed

bus.connect(LayoutChangedEvent, handle_layout_change)
```

## For UI Component Development

### Creating a Layout-Aware Component
All UI components should implement the `apply_layout()` interface:

```python
import flet as ft
from ui.layout import AppLayout

class MyComponent(ft.Container):
    def __init__(self):
        super().__init__()
        self.layout: AppLayout | None = None
    
    def apply_layout(self, layout: AppLayout) -> None:
        """Apply responsive metrics to this component."""
        self.layout = layout
        
        # Use layout metrics to scale:
        font_size = int(layout.board_square_size * 0.5)
        self.width = layout.clock_width
        self.padding = layout.timer_padding
        
        self._safe_update(self)
    
    @staticmethod
    def _safe_update(control: ft.Control):
        """Safely update a control."""
        try:
            control.update()
        except RuntimeError:
            pass
```

### Creating a Layout-Specific Display Component
Inherit from `PieceDisplayBase` if creating components that vary by layout:

```python
from ui.captured_pieces import PieceDisplayBase

class MyCustomDisplay(PieceDisplayBase):
    def _render_layout(self) -> None:
        """Called when layout changes or needs re-render."""
        if not self.layout or not self.template:
            return
        
        config = self.template.get_config()
        
        if self.template.get_layout_type() == "mobile":
            # Mobile-specific rendering
            self._render_mobile_layout()
        else:
            # Desktop/tablet rendering
            self._render_desktop_layout()
```

## Using Captured Pieces Data

### Reading Captured Pieces
Access the model directly or through events:

```python
from utils.signals import bus
from utils.events import CapturedPiecesUpdatedEvent

def on_captured_pieces_updated(event: CapturedPiecesUpdatedEvent):
    # Access the display component to get current captured pieces
    # Or store a reference to the model
    pass

bus.connect(CapturedPiecesUpdatedEvent, on_captured_pieces_updated)
```

### Testing with Captured Pieces
```python
from utils.captured_pieces_model import CapturedPiecesModel

def test_captured_pieces():
    model = CapturedPiecesModel()
    
    # Add captures
    model.add_captured_piece("pawn", "white")
    model.add_captured_piece("knight", "white")
    
    # Verify ownership reversal
    on_white_side = model.get_pieces_to_display_for_side("white")
    assert "pawn" not in on_white_side  # White's captures appear on black's side
    
    # Clear for new game
    model.clear()
```

## Understanding Layout Detection

### Breakpoints
The layout type is determined automatically:

```
Mobile:   width < 700px    → MobileLayout (split UI, stacked)
Tablet:   700px ≤ w < 1100px → TabletLayout (compact horizontal)
Desktop:  width ≥ 1100px   → DesktopLayout (spacious horizontal)
```

### Accessing Current Layout Type
```python
from ui.layout import resolve_app_layout

layout = resolve_app_layout(page.width, page.height)
print(layout.layout_type)        # "desktop", "tablet", or "mobile"
print(layout.layout_template)    # LayoutTemplate instance
```

## Animation Coordinator API

### Manual Animation (Advanced)
```python
from ui.piece_capture_animator import PieceCaptureAnimator

animator = PieceCaptureAnimator()

# Calculate target position
target = animator.calculate_capture_target(
    board_position=(100, 100),
    captured_by="white",
    layout_type="desktop",
    viewport_metrics={
        "captured_area_left": 20,
        "captured_area_top": 20,
        "captured_area_width": 120,
        "captured_area_height": 240,
    }
)

# Run animation
await animator.animate_captured_piece(
    piece_control=my_piece_control,
    source_position=(100, 100),
    target_position=target,
    layout_type="desktop",
    on_animation_complete=callback
)
```

## Event Flow Diagram

```
User Action (Piece Captured)
    ↓
Board Logic validates capture
    ↓
emit(PieceCapturedEvent)
    ↓
PieceCaptureAnimator animates piece
    ↓
CapturedPiecesModel receives event & updates
    ↓
emit(CapturedPiecesUpdatedEvent)
    ↓
PieceDisplay re-renders
    ↓
UI shows piece in captured area
```

## Common Tasks

### Add a new layout variant
1. Create class inheriting from `LayoutTemplate`
2. Implement required methods
3. Update `get_layout_template()` factory function
4. Optionally create corresponding display component inheriting from `PieceDisplayBase`

### Change animation timing
```python
# In piece_capture_animator.py
class PieceCaptureAnimator:
    CAPTURE_ANIMATION_DURATION_MS = 300  # Change from 200 to 300
```

### Customize captured pieces grid
```python
# In layout_templates.py
class CustomLayout(LayoutTemplate):
    def get_config(self):
        return LayoutTemplateConfig(
            layout_type="custom",
            clock_mode="combined",
            captured_pieces_grid_shape=(3, 5),  # 3 rows x 5 cols
            # ...
        )
```

### Select layout for testing
```python
# Simulate different screen sizes:
from ui.layout import resolve_app_layout

mobile = resolve_app_layout(500, 800)      # Mobile layout
tablet = resolve_app_layout(900, 800)      # Tablet layout
desktop = resolve_app_layout(1400, 800)    # Desktop layout
```

## Debugging

### Verify layout type
```python
from ui.layout import resolve_app_layout

layout = resolve_app_layout(page.width, page.height)
print(f"Layout type: {layout.layout_type}")
print(f"Template: {type(layout.layout_template).__name__}")
print(f"Clock mode: {layout.layout_template.get_config().clock_mode}")
```

### Check captured pieces model
```python
from utils.signals import bus
from utils.events import PieceCapturedEvent

def debug_captures(event: PieceCapturedEvent):
    print(f"Piece captured: {event.piece_type} by {event.captured_by}")

bus.connect(PieceCapturedEvent, debug_captures)
```

### Verify animation timing
```python
import time
from ui.piece_capture_animator import PieceCaptureAnimator

animator = PieceCaptureAnimator()
duration = animator.get_animation_duration_ms()
print(f"Animation duration: {duration}ms")
```
