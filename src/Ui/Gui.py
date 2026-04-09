"""Convenience exports for the UI package."""

from ui.app import ChessApp, main
from ui.board import ChessBoard
from ui.chess_piece import ChessPiece
from ui.square import Square

__all__ = ["ChessPiece", "Square", "ChessBoard", "ChessApp", "main"]
