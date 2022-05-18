import os
from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple, Union

import chess
import chess.engine
import chess.pgn

Seed = Optional[Union[int, float, str, bytes, bytearray]]
PathLike = Union[str, List[str]]

BK_FILE = os.path.join('bk.pl')

LICHESS_2013 = os.path.join('data', 'lichess_db_standard_rated_2013-01.pgn')

STOCKFISH = os.path.join('bin', 'stockfish_14_x64')
MAIA_1100 = os.path.join('bin' 'lc0', 'build', 'release', 'lc0')

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

def positions_pgn(pgn_file: PathLike, num_games: int=10, pos_per_game: int=10) -> Generator[chess.Board, None, None]:
    "Generator to yield list of positions from games in a PGN file"
    with open(pgn_file) as pgn_file_handle:
        curr_games = 0
        while game := chess.pgn.read_game(pgn_file_handle):
            curr_positions = 0
            node = game.next() # skip start position
            while node and not node.is_end():
                board = node.board()
                yield board
                curr_positions += 1
                if pos_per_game and curr_positions >= pos_per_game:
                    break
                node = node.next()
            curr_games += 1
            if num_games and curr_games >= num_games:
                break

def positions_list(pos_list: PathLike) -> Generator[chess.Board, None, None]:
    "Generator to yield positions listed in FEN notation in a file"
    with open(pos_list) as pos_list_handle:
        for line in pos_list_handle:
            board = chess.Board()
            board.set_board_fen(line)
            yield board

def get_evals(engine: chess.engine.SimpleEngine, board: chess.Board, suggestions: List[chess.Move]) -> List[Tuple[chess.engine.Score, chess.Move]]:
    "Obtain engine evaluations for a list of moves in a given position"
    evals = []
    for move in suggestions:
        analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), root_moves=[move])
        if 'pv' in analysis: 
            evals.append((analysis['score'].relative, analysis['pv'][0]))
    return evals

def get_top_n_moves(engine: chess.engine.SimpleEngine, board: chess.Board, n: int) -> List[Tuple[chess.engine.Score, chess.Move]]:
    "Get the top-n engine-recommended moves for a given position"
    analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), multipv=n)
    top_n_moves = [(root['score'].relative, root['pv'][0]) for root in analysis]
    return top_n_moves[:n]
