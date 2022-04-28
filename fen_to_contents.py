#!/usr/bin/env python3

import sys
import chess

def fen_to_contents(fen: str) -> str:
    "Convert a FEN position into a contents predicate"
    board = chess.Board()
    board.set_fen(fen)
    piece_str_list = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            color = 'white' if piece.color else 'black'
            piece_name = chess.piece_name(piece.piece_type)
            row = chess.square_rank(square) + 1
            col = chess.square_file(square) + 1
            piece_str_list.append(f'contents({color}, {piece_name}, {col}, {row})')
    return f'[{", ".join(piece_str_list)}]'

if __name__ == '__main__':
    fen = sys.argv[1]
    # fen = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
    print(fen_to_contents(fen))