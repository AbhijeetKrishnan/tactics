import os
from contextlib import contextmanager
from typing import Optional, Union

import chess
import chess.engine

from pyswip import Prolog
from pyswip.prolog import PrologError

Seed = Optional[Union[int, float, str, bytes, bytearray]]
PathLike = Union[str, bytes, os.PathLike]

BK_FILE = os.path.join('bk.pl')

LICHESS_2013 = os.path.join('data', 'lichess_db_standard_rated_2013-01.pgn')

STOCKFISH = os.path.join('bin', 'stockfish_14_x64')
MAIA_1100 = os.path.join(os.path.expanduser('~'), 'repos', 'lc0', 'build', 'release', 'lc0')

@contextmanager
def get_engine(engine_path: PathLike):
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        yield engine
    except chess.engine.EngineError:
        pass
    finally:
        engine.close()

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
