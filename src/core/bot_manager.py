from stockfish import Stockfish

from utils.events import PieceMovedEvent
from utils.signals import bus


class BotManager:
    def __init__(self):
        self.stockfish = Stockfish(
            r"C:\Users\HP\Desktop\stockfish\stockfish-windows-x86-64-avx2.exe", depth=10
        )
        bus.connect(PieceMovedEvent, lambda event: self._on_piece_moved(event))

    def _on_piece_moved(self, event: PieceMovedEvent):
        print(event)


if __name__ == "__main__":
    bot_manager = BotManager()
