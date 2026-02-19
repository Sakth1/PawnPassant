import flet as ft

from Core import Game


def main():
    game = Game.Game()

    while True:
        move = input("Enter your move (e.g., e4, Nf3, etc.): ")
        if move.lower() == "exit":
            break
        if game.make_move(move):
            print(game.board.unicode(borders=True))
        else:
            print("Invalid move. Please try again.")