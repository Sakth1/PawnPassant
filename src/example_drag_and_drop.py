import flet as ft

IMAGE_URLS = [
    "https://picsum.photos/seed/forest/400/400",
    "https://picsum.photos/seed/ocean/400/400",
    "https://picsum.photos/seed/mountain/400/400",
    "https://picsum.photos/seed/desert/400/400",
]

LABELS = ["Forest", "Ocean", "Mountain", "Desert"]


def main(page: ft.Page):
    page.title = "Image Drag & Drop Grid"
    page.bgcolor = "#1a1a2e"
    page.padding = 40
    page.window.width = 700
    page.window.height = 750

    # slot index -> image index
    slot_images = {0: 0, 1: 1, 2: 2, 3: 3}

    grid = ft.GridView(
        runs_count=2,
        max_extent=300,
        spacing=16,
        run_spacing=16,
        expand=True,
    )

    def make_image_stack(image_index: int) -> ft.Stack:
        return ft.Stack(
            controls=[
                ft.Image(
                    src=IMAGE_URLS[image_index],
                    width=280,
                    height=280,
                    fit=ft.BoxFit.COVER,
                    border_radius=ft.border_radius.all(12),
                ),
                ft.Container(
                    content=ft.Text(
                        LABELS[image_index],
                        color="white",
                        size=14,
                        weight=ft.FontWeight.BOLD,
                    ),
                    alignment=ft.Alignment.BOTTOM_LEFT,
                    padding=ft.padding.only(left=10, bottom=10),
                    gradient=ft.LinearGradient(
                        begin=ft.Alignment.TOP_CENTER,
                        end=ft.Alignment.BOTTOM_CENTER,
                        colors=["transparent", "#aa000000"],
                    ),
                    border_radius=ft.border_radius.all(12),
                    width=280,
                    height=280,
                ),
            ],
            width=280,
            height=280,
        )

    def build_slot(slot_index: int) -> ft.DragTarget:
        img_idx = slot_images[slot_index]

        inner = ft.Container(
            content=make_image_stack(img_idx),
            border_radius=ft.border_radius.all(14),
            border=ft.Border.all(2, "#2a2a4a"),
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
            shadow=ft.BoxShadow(
                spread_radius=0,
                blur_radius=20,
                color="#44000000",
                offset=ft.Offset(0, 8),
            ),
        )

        draggable = ft.Draggable(
            group="images",
            content=inner,
            content_feedback=ft.Container(
                content=ft.Image(
                    src=IMAGE_URLS[img_idx],
                    width=120,
                    height=120,
                    fit=ft.BoxFit.COVER,
                    border_radius=ft.border_radius.all(10),
                    opacity=0.85,
                ),
                shadow=ft.BoxShadow(
                    spread_radius=2,
                    blur_radius=20,
                    color="#88e94560",
                    offset=ft.Offset(0, 4),
                ),
            ),
            content_when_dragging=ft.Container(
                width=280,
                height=280,
                border_radius=ft.border_radius.all(14),
                bgcolor="#2a2a4a",
                border=ft.Border.all(2, "#e94560"),
                content=ft.Icon(
                    ft.Icons.IMAGE_OUTLINED,
                    color="#e94560",
                    size=48,
                ),
                alignment=ft.Alignment.CENTER,
            ),
        )

        def on_will_accept(e: ft.DragWillAcceptEvent, si=slot_index):
            # e.accept: bool in 0.82.x (replaces e.data == "true")
            e.control.content.border = ft.Border.all(
                3, "#e94560" if e.accept else "#555555"
            )
            e.control.update()

        def on_accept(e: ft.DragTargetEvent, dst=slot_index):
            src_draggable = page.get_control(e.src_id)

            # Find the source slot by matching the draggable control reference
            src_slot = None
            for si, dt in enumerate(grid.controls):
                if dt.content is src_draggable:
                    src_slot = si
                    break

            if src_slot is not None and src_slot != dst:
                slot_images[src_slot], slot_images[dst] = (
                    slot_images[dst],
                    slot_images[src_slot],
                )
                rebuild_slot(src_slot)
                rebuild_slot(dst)
            else:
                e.control.content.border = ft.Border.all(2, "#2a2a4a")
                e.control.update()

        def on_leave(e: ft.DragTargetLeaveEvent):
            e.control.content.border = ft.Border.all(2, "#2a2a4a")
            e.control.update()

        return ft.DragTarget(
            group="images",
            content=draggable,
            on_will_accept=on_will_accept,
            on_accept=on_accept,
            on_leave=on_leave,
        )

    def rebuild_slot(slot_index: int):
        grid.controls[slot_index] = build_slot(slot_index)
        grid.update()

    for i in range(4):
        grid.controls.append(build_slot(i))

    page.add(
        ft.Column(
            controls=[
                ft.Text(
                    "Drag & Drop Gallery",
                    size=28,
                    weight=ft.FontWeight.BOLD,
                    color="white",
                    font_family="monospace",
                ),
                ft.Text(
                    "Drag images between slots to rearrange",
                    size=13,
                    color="#888888",
                ),
                ft.Container(height=16),
                grid,
            ],
            expand=True,
        )
    )


ft.run(main)