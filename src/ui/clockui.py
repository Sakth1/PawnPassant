"""Clock UI component supporting both combined and split display modes.

- Combined mode (desktop/tablet): Both clocks stacked vertically
- Split mode (mobile): Clocks positioned in opposite corners
"""

import flet as ft

from ui.layout import AppLayout, resolve_app_layout
from core.clock import Clock
from utils.signals import bus
from utils.events import (
    ClockStateEvent,
    ClockTickEvent,
    GameEndedEvent,
    GameStartedEvent,
    PieceModevedEvent,
)
from utils.models import ActiveColor, TimeControl


def time_control_to_string(time_control: TimeControl) -> str:
    return f"{time_control[0]:02}:00"


class SingleClockDisplay(ft.Container):
    """Reusable single clock display for one player.
    
    Can be used standalone or composed into CombinedClock or MobileClockSplit.
    """

    def __init__(self, color: str, time_control: TimeControl, size: int = 100):
        """Initialize a single clock display.
        
        Args:
            color: "white" or "black"
            time_control: TimeControl tuple
            size: Base size for font scaling
        """
        super().__init__()
        self.color = color
        self.size_hint = size
        
        self.timer_main = ft.Text(
            time_control_to_string(time_control),
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=24,
            weight=ft.FontWeight.BOLD,
            margin=ft.margin.Margin(5, 5, 5, 5),
        )
        
        self.timer_ms = ft.Text(
            "",
            text_align=ft.TextAlign.CENTER,
            color=ft.Colors.GREY_400,
            font_family="RobotoMono",
            size=12,
            weight=ft.FontWeight.BOLD,
            offset=ft.Offset(0, 0.1),
            margin=ft.margin.Margin(0, 0, 5, 0),
        )
        
        self.content = ft.Row(
            controls=[self.timer_main, self.timer_ms],
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.END,
            spacing=2,
            margin=ft.margin.Margin(5, 5, 5, 5),
        )
        
        self.bgcolor = "#262626"
        self.border_radius = 12
        self.padding = 8

    def update_time(self, minutes: int, seconds: int, milliseconds: int, is_critical: bool) -> None:
        """Update the displayed time.
        
        Args:
            minutes: Remaining minutes
            seconds: Remaining seconds
            milliseconds: Remaining milliseconds (for critical display)
            is_critical: Whether time is critical (<10 seconds)
        """
        self.timer_main.value = f"{minutes:02}:{seconds:02}"
        self.timer_main.color = ft.Colors.GREY_400
        self.timer_ms.bgcolor = None
        
        if is_critical:
            self.timer_ms.value = f".{milliseconds // 10:02}"
            self.bgcolor = "#250E0E"
            self.timer_ms.bgcolor = "#250E0E"
        else:
            self.timer_ms.value = ""
            self.bgcolor = "#262626"
        
        self._safe_update(self)

    def apply_size(self, timer_font_size: int, timer_ms_size: int, timer_padding: int, timer_radius: int) -> None:
        """Apply responsive sizing.
        
        Args:
            timer_font_size: Main time text size
            timer_ms_size: Milliseconds text size
            timer_padding: Internal padding
            timer_radius: Border radius
        """
        self.timer_main.size = timer_font_size
        self.timer_ms.size = timer_ms_size
        self.padding = timer_padding
        self.border_radius = timer_radius
        self._safe_update(self)

    @staticmethod
    def _safe_update(control: ft.Control):
        """Safely update a control."""
        try:
            control.update()
        except RuntimeError:
            pass


class ClockUI(ft.Container):
    """Main clock UI component supporting combined and split display modes.
    
    - Combined mode (desktop/tablet): Stacked black and white clocks
    - Split mode (mobile): Corner-positioned clocks (handled by main app layout)
    """

    def __init__(self, time_control: TimeControl = TimeControl.THREE_PLUS_TWO):
        super().__init__()
        self.layout = resolve_app_layout(960, 800)
        self.time_control = time_control
        self.mode = "combined"  # Will be set to "split" for mobile
        
        # Create individual clock displays
        self.black_clock = SingleClockDisplay("black", time_control)
        self.white_clock = SingleClockDisplay("white", time_control)
        
        # Divider for combined mode
        self.divider = ft.Container(
            height=3,
            bgcolor=ft.Colors.GREY_400,
            width=200,
            margin=ft.margin.Margin(20, 0, 20, 0),
        )
        
        # Combined layout (default for desktop/tablet)
        self.content = ft.Column(
            controls=[
                self.black_clock,
                self.divider,
                self.white_clock,
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )
        
        self.bgcolor = "#262626"
        self.expand = False
        self.alignment = ft.Alignment.CENTER
        self.border_radius = self.layout.timer_radius
        
        # Clock management
        self.clock = Clock(time_control=time_control)
        self.active_color: ActiveColor = ActiveColor.WHITE
        self.game_over = False
        
        # Event subscriptions
        bus.connect(ClockStateEvent, self._handle_clock_state)
        bus.connect(ClockTickEvent, self._handle_clock_tick)
        bus.connect(PieceModevedEvent, self._handle_piece_moved)
        bus.connect(GameStartedEvent, self._start_clock)
        bus.connect(GameEndedEvent, self._handle_game_ended)
        
        self.apply_layout(self.layout)

    def apply_layout(self, layout: AppLayout) -> None:
        """Apply responsive layout, switching modes if needed.
        
        Args:
            layout: Resolved AppLayout with current metrics
        """
        self.layout = layout
        
        # Determine display mode based on layout type
        new_mode = "split" if layout.layout_type == "mobile" else "combined"
        if new_mode != self.mode:
            self.mode = new_mode
            self._switch_display_mode()
        
        # Apply size metrics
        self.width = layout.clock_width if self.mode == "combined" else None
        self.border_radius = layout.timer_radius
        
        # Update clock displays
        self.black_clock.apply_size(
            layout.timer_font_size,
            layout.timer_ms_size,
            layout.timer_padding,
            layout.timer_radius,
        )
        self.white_clock.apply_size(
            layout.timer_font_size,
            layout.timer_ms_size,
            layout.timer_padding,
            layout.timer_radius,
        )
        
        # Update divider
        self.divider.width = layout.divider_extent
        self.content.spacing = max(10, layout.gap)
        
        self._safe_update(self)

    def _switch_display_mode(self) -> None:
        """Switch between combined and split display modes."""
        if self.mode == "combined":
            # Combined: stacked vertically
            self.content = ft.Column(
                controls=[
                    self.black_clock,
                    self.divider,
                    self.white_clock,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            )
        else:
            # Split mode: handled by main app layout
            # This component only manages the individual clock displays
            # The main app will position black_clock (top-right) and white_clock (bottom-right)
            pass

    def _safe_page(self):
        """Safely get the page reference."""
        try:
            return self.page
        except RuntimeError:
            return None

    def _handle_clock_tick(self, event: ClockTickEvent) -> None:
        """Handle clock tick events."""
        if self.game_over:
            return
        page = self._safe_page()
        if page is None:
            return
        page.run_task(self._update_ui_async, event)

    async def _update_ui_async(self, event: ClockTickEvent) -> None:
        """Async UI update wrapper."""
        self._update_ui(event)

    def _update_ui(self, event: ClockTickEvent) -> None:
        """Update clock display with new time."""
        is_white = event.color == ActiveColor.WHITE
        target_clock = self.white_clock if is_white else self.black_clock
        
        target_clock.update_time(
            event.minutes,
            event.seconds,
            event.milliseconds,
            event.is_critical,
        )

    def _start_clock(self, _event: GameStartedEvent) -> None:
        """Start the clock when game begins."""
        self.game_over = False
        self.clock.start()

    def _handle_piece_moved(self, _event: PieceModevedEvent) -> None:
        """Switch clock when a piece is moved."""
        if self.game_over:
            return
        self.clock.switch()
        self._flip_clock()

    def _handle_clock_state(self, event: ClockStateEvent) -> None:
        """Handle flag-fall (time expired)."""
        if event.state != "flagged" or event.active_color is None or self.game_over:
            return

        winner = "Black" if event.active_color == ActiveColor.WHITE else "White"
        bus.emit(
            GameEndedEvent(
                winner=winner,
                reason="time",
                message=f"{winner} wins on time.",
            )
        )

    def _flip_clock(self) -> None:
        """Reverse the clock display orientation."""
        if self.mode == "combined":
            self.content.controls.reverse()
            self._safe_update(self)

    def _handle_game_ended(self, _event: GameEndedEvent) -> None:
        """Stop clock when game ends."""
        self.game_over = True
        self.clock.stop()

    @staticmethod
    def _safe_update(control: ft.Control) -> None:
        """Safely update a control, handling page detach."""
        try:
            control.update()
        except RuntimeError:
            pass

