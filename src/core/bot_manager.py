from stockfish import Stockfish

from utils.events import PieceMovedEvent
from utils.signals import bus


class BotManager:
    def __init__(self):
        self.stockfish = Stockfish(
            r"C:\Users\HP\Desktop\stockfish\stockfish-windows-x86-64-avx2.exe", depth=10
        )

    def set_depth(self, depth):
        self.stockfish.set_depth(depth)

    def set_elo(self, elo):
        self.stockfish.set_elo_rating(elo)

    def set_skill_level(self, skill_level):
        self.stockfish.set_skill_level(skill_level)

    # have to write a bot that gets remaining time of self and opponent, possible moves, and other relsted stuff and return moves.


if __name__ == "__main__":
    bot_manager = BotManager()
