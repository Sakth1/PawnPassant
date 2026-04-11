"""Layout templates for different screen types (desktop, tablet, mobile).

Each template defines:
- UI structure (component hierarchy, containers, positioning)
- Captured pieces grid layout
- Clock display mode
- Spacing and padding rules
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


LayoutType = Literal["desktop", "tablet", "mobile"]
ClockMode = Literal["combined", "split"]
CapturedPiecesGridShape = tuple[int, int]  # (rows, cols)


@dataclass
class LayoutTemplateConfig:
    """Configuration for a specific layout template."""

    layout_type: LayoutType
    clock_mode: ClockMode
    captured_pieces_grid_shape: CapturedPiecesGridShape
    captured_pieces_scrollable: bool
    is_stacked: bool  # Components stacked vertically (mobile) vs. side-by-side (desktop/tablet)


class LayoutTemplate(ABC):
    """Abstract base class for layout templates.
    
    Each subclass defines how components should be arranged for a specific screen type.
    """

    @abstractmethod
    def get_layout_type(self) -> LayoutType:
        """Return the layout type identifier."""
        pass

    @abstractmethod
    def get_config(self) -> LayoutTemplateConfig:
        """Return the configuration for this template."""
        pass

    @abstractmethod
    def get_component_positions(self) -> dict:
        """Return a dict of component positions and sizing info.
        
        Used by layout_builder to position components correctly.
        """
        pass

    @abstractmethod
    def get_responsive_row_cols(self) -> dict:
        """Return ResponsiveRow col definitions for components.
        
        Format: {"xs": 12, "md": 8, "lg": 8} for different breakpoints.
        """
        pass


class DesktopLayout(LayoutTemplate):
    """Desktop layout: horizontal arrangement (captured | board | clock)."""

    def get_layout_type(self) -> LayoutType:
        return "desktop"

    def get_config(self) -> LayoutTemplateConfig:
        return LayoutTemplateConfig(
            layout_type="desktop",
            clock_mode="combined",
            captured_pieces_grid_shape=(4, 4),  # 4 rows x 4 cols per side
            captured_pieces_scrollable=False,
            is_stacked=False,
        )

    def get_component_positions(self) -> dict:
        """Desktop components positioned horizontally in ResponsiveRow."""
        return {
            "captured_pieces": {
                "flex": 1,
                "alignment": "center",
                "description": "Left side: 4×4 combined grid (black top, white bottom)",
            },
            "board": {
                "flex": 2,
                "alignment": "center",
                "description": "Center: 8×8 chess board",
            },
            "clock": {
                "flex": 1,
                "alignment": "center",
                "description": "Right side: combined clock (black/white stacked)",
            },
        }

    def get_responsive_row_cols(self) -> dict:
        """Use 12-column grid: captured (2 cols) | board (5 cols) | clock (5 cols)."""
        return {
            "captured_pieces": {"xs": 12, "md": 3, "lg": 2},
            "board": {"xs": 12, "md": 5, "lg": 5},
            "clock": {"xs": 12, "md": 4, "lg": 5},
        }


class TabletLayout(LayoutTemplate):
    """Tablet layout: intermediate between desktop and mobile.
    
    Inherits desktop's horizontal arrangement but with tighter spacing.
    """

    def get_layout_type(self) -> LayoutType:
        return "tablet"

    def get_config(self) -> LayoutTemplateConfig:
        return LayoutTemplateConfig(
            layout_type="tablet",
            clock_mode="combined",
            captured_pieces_grid_shape=(4, 4),  # Same as desktop
            captured_pieces_scrollable=False,
            is_stacked=False,
        )

    def get_component_positions(self) -> dict:
        """Tablet: similar to desktop but with optimized spacing for medium screens."""
        return {
            "captured_pieces": {
                "flex": 0.8,
                "alignment": "center",
                "description": "Left side: compact 4×4 grid",
            },
            "board": {
                "flex": 1.5,
                "alignment": "center",
                "description": "Center: 8×8 board (scaled to fit)",
            },
            "clock": {
                "flex": 0.8,
                "alignment": "center",
                "description": "Right side: combined clock (compact)",
            },
        }

    def get_responsive_row_cols(self) -> dict:
        """Tighter column allocation."""
        return {
            "captured_pieces": {"xs": 12, "md": 2, "lg": 2},
            "board": {"xs": 12, "md": 7, "lg": 7},
            "clock": {"xs": 12, "md": 3, "lg": 3},
        }


class MobileLayout(LayoutTemplate):
    """Mobile layout: board-focused with split UI elements.
    
    Clock: split into two corners (opponent top-right, current player bottom-right)
    Captured pieces: split into two sections (opponent above board, current player below)
    Board: primary focus, fills most of viewport
    """

    def get_layout_type(self) -> LayoutType:
        return "mobile"

    def get_config(self) -> LayoutTemplateConfig:
        return LayoutTemplateConfig(
            layout_type="mobile",
            clock_mode="split",
            captured_pieces_grid_shape=(2, 8),  # 2 rows x 8 cols per section
            captured_pieces_scrollable=True,
            is_stacked=True,
        )

    def get_component_positions(self) -> dict:
        """Mobile: stacked vertically with board as primary focus."""
        return {
            "opponent_captured_pieces": {
                "position": "top",
                "flex": 1,
                "description": "Above board: opponent's captured pieces (2×8 grid)",
            },
            "board": {
                "position": "center",
                "flex": 3,
                "description": "Primary focus: 8×8 board, fills most space",
            },
            "current_player_captured_pieces": {
                "position": "bottom",
                "flex": 1,
                "description": "Below board: current player's captured pieces (2×8 grid)",
            },
            "opponent_clock": {
                "position": "top-right",
                "overlay": True,
                "description": "Corner overlay: opponent's clock, non-obstructive",
            },
            "current_player_clock": {
                "position": "bottom-right",
                "overlay": True,
                "description": "Corner overlay: current player's clock, non-obstructive",
            },
        }

    def get_responsive_row_cols(self) -> dict:
        """Full-width stacking for mobile."""
        return {
            "opponent_captured_pieces": {"xs": 12, "md": 12},
            "board": {"xs": 12, "md": 12},
            "current_player_captured_pieces": {"xs": 12, "md": 12},
        }


def get_layout_template(layout_type: LayoutType) -> LayoutTemplate:
    """Factory function to get the appropriate layout template.
    
    Args:
        layout_type: One of "desktop", "tablet", "mobile"
        
    Returns:
        Appropriate LayoutTemplate subclass instance
        
    Raises:
        ValueError: If layout_type is not recognized
    """
    if layout_type == "desktop":
        return DesktopLayout()
    elif layout_type == "tablet":
        return TabletLayout()
    elif layout_type == "mobile":
        return MobileLayout()
    else:
        raise ValueError(f"Unknown layout type: {layout_type}")
