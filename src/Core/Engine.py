from chess import Board 


class Game:
    def __init__(self):
        self.board: Board = Board()
        #print(self.board.unicode(borders=True))
        #print(self.board.legal_moves)
        
    
    def get_board_fen(self):
        return self.board.fen()

    def is_game_over(self):
        return self.board.is_game_over()

    def get_winner(self):
        if self.board.is_checkmate():
            return "Black" if self.board.turn else "White"
        elif self.board.is_stalemate() or self.board.is_insufficient_material() or self.board.is_seventyfive_moves() or self.board.is_fivefold_repetition():
            return "Draw"
        else:
            return None