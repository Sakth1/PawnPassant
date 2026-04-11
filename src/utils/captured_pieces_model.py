"""Model for tracking captured pieces and their ownership.

Pieces are tracked by the player who captured them, and displayed on the
opponent's side (e.g., White's captured pieces appear on Black's side).
"""

from dataclasses import dataclass, field


@dataclass
class CapturedPiecesModel:
    """Tracks captured pieces indexed by the capturing player.
    
    Ownership is reversed in display:
    - black_captured_pieces: pieces captured BY black (appear on white's side)
    - white_captured_pieces: pieces captured BY white (appear on black's side)
    """

    black_captured_pieces: list[str] = field(default_factory=list)
    white_captured_pieces: list[str] = field(default_factory=list)

    def add_captured_piece(self, piece_type: str, captured_by: str) -> None:
        """Add a captured piece.
        
        Args:
            piece_type: Type of piece ("pawn", "knight", "bishop", "rook", "queen", "king")
            captured_by: Player who captured the piece ("white" or "black")
        """
        if captured_by == "white":
            self.white_captured_pieces.append(piece_type)
        elif captured_by == "black":
            self.black_captured_pieces.append(piece_type)
        else:
            raise ValueError(f"Invalid player: {captured_by}")

    def get_captured_pieces(self, player: str) -> list[str]:
        """Get pieces captured by a specific player.
        
        Args:
            player: "white" or "black"
            
        Returns:
            List of piece types captured by this player
        """
        if player == "white":
            return self.white_captured_pieces
        elif player == "black":
            return self.black_captured_pieces
        else:
            raise ValueError(f"Invalid player: {player}")

    def get_pieces_to_display_for_side(self, side: str) -> list[str]:
        """Get pieces that should be displayed on a given side.
        
        Note: pieces are displayed on the opposite side from where they were captured.
        E.g., pieces captured BY white are displayed on the BLACK side.
        
        Args:
            side: "white" or "black" (the side to display pieces on)
            
        Returns:
            List of piece types to display on this side
        """
        if side == "white":
            # Display pieces captured by black
            return self.black_captured_pieces
        elif side == "black":
            # Display pieces captured by white
            return self.white_captured_pieces
        else:
            raise ValueError(f"Invalid side: {side}")

    def clear(self) -> None:
        """Clear all captured pieces (for game reset)."""
        self.black_captured_pieces.clear()
        self.white_captured_pieces.clear()

    def to_dict(self) -> dict:
        """Export model state as dictionary."""
        return {
            "black_captured_pieces": self.black_captured_pieces.copy(),
            "white_captured_pieces": self.white_captured_pieces.copy(),
        }
