chat gpt's root cause analysis for the visual bug:
**Root Cause**

The visual glitch comes from split ownership of the same move.

In your board, the dragged piece is represented by three different systems:

- Flet’s native drag visuals in [src/Ui/square.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/square.py#L158), where each piece is a `Draggable` with `content_when_dragging` and `content_feedback`.
- Per-square piece state in [src/Ui/square.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/square.py#L131), where `update_content()` rebuilds a fresh draggable for a square.
- A separate board-level move presentation layer in [src/Ui/board.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/board.py#L95) and [src/Ui/board.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/board.py#L582), used for animated moves.

For drag-drop specifically, the drop path is:

- `DragTarget.on_accept` forwards to board logic in [src/Ui/square.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/square.py#L95)
- the board handles it in [src/Ui/board.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/board.py#L307)
- then `move_piece()` commits the chess move and rebuilds source/destination squares in [src/Ui/board.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/board.py#L642) and [src/Ui/board.py](d:/Personal/Personal_Projects/PawnPassant/src/Ui/board.py#L352)

So the piece under the pointer is not the same UI object that ends up on the destination square. Flet finishes the drag lifecycle first, which makes the source square’s normal content reappear, and only after that your board commit/re-render creates a new piece on the destination square. That is the “goes back, then goes forward” effect.

**Why The Docs Example Feels Smooth**

In the Flet cookbook example, the source and destination visuals are changed directly in `on_accept`, and Flet explicitly says it’s the developer’s job to define what happens to source and target on acceptance:
https://docs.flet.dev/cookbook/drag-and-drop/

That example has one visual state transition: accept drop -> mutate source/target content. Your app has two transitions: drag ends -> source visual returns, then board state commits -> destination visual appears.

**Architectural Fix**

Use one visual owner for a move, not multiple.

The clean design change is to unify drag-drop and click-move under a single move-presentation pipeline with explicit phases like `idle -> dragging -> accepted/committing -> settled`. In that design:

- the board owns the visual truth of piece positions
- drag feedback is only a preview of that board-owned state
- drop acceptance atomically changes the presented board state from source occupied/destination empty to source empty/destination occupied
- engine commit and UI commit happen as one transaction, not as a later re-creation pass

In practice, that means choosing one of these architectures and sticking to it:

- Native Flet drag architecture: let drag/drop be state-driven at `on_accept`, and do not layer a second board-managed move animation on top of it.
- Custom board animation architecture: own drag visuals entirely at board level and stop relying on Flet’s built-in drag feedback as the movement visual.

The current issue exists because the app is mixing both.

---

Have to rework how dragtarget is constructed. will have to construct target for each piece everytime, update instantly on_accept.