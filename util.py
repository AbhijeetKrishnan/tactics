import logging
import os
from contextlib import contextmanager
from typing import Generator, List, Optional, TextIO, Tuple, Union

import chess
import chess.engine
import chess.pgn
import pyswip

Seed = Optional[Union[int, float, str, bytes, bytearray]]
PathLike = Union[str, List[str]]

BK_FILE = os.path.join('bk.pl')

LICHESS_2013 = os.path.join('data', 'lichess_db_standard_rated_2013-01.pgn')

STOCKFISH = os.path.join('bin', 'stockfish_14_x64')
MAIA_1100 = os.path.join('bin' 'lc0', 'build', 'release', 'lc0')

logger = logging.getLogger(__name__)

@contextmanager
def get_engine(engine_path: PathLike):
    try:
        engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        yield engine
    except chess.engine.EngineError:
        pass
    finally:
        engine.close()

def convert_side(side: Union[str, bool]) -> Union[bool, str]:
    if isinstance(side, bool):
        side_str = 'white' if side == chess.WHITE else 'black'
        return side_str
    elif isinstance(side, str):
        side_val = chess.WHITE if side == 'white' else chess.BLACK
        return side_val

def fen_to_contents(fen: str) -> str:
    "Convert a FEN position into a contents predicate"

    board = chess.Board()
    board.set_fen(fen)
    board_str_list = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            color = convert_side(piece.color)
            piece_name = chess.piece_name(piece.piece_type)
            row = chess.square_rank(square) + 1
            col = chess.square_file(square) + 1
            board_str_list.append(f'contents({color}, {piece_name}, {col}, {row})')

    side_str = convert_side(board.turn)
    turn_pred = f'turn({side_str})'
    board_str_list.append(turn_pred)

    castling_preds = []
    for side, side_str in zip([chess.WHITE, chess.BLACK], ['white', 'black']):
        if board.has_kingside_castling_rights(side):
            castling_preds.append(f'kingside_castle({side_str})')
        if board.has_queenside_castling_rights(side):
            castling_preds.append(f'queenside_castle({side_str})')
    board_str_list.extend(castling_preds)

    return f'[{", ".join(board_str_list)}]'

def games(pgn_filename: PathLike) -> Generator[Optional[chess.pgn.Game], None, None]:
    "Generator to yield list of games in a PGN file"
    with open(pgn_filename) as pgn_file_handle:
        while game := chess.pgn.read_game(pgn_file_handle):
            yield game

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

def parse_piece(name: str) -> chess.Piece:
    name = name.lower()
    if name == 'pawn':
        return chess.PAWN
    elif name == 'knight':
        return chess.KNIGHT
    elif name == 'bishop':
        return chess.BISHOP
    elif name == 'rook':
        return chess.ROOK
    elif name == 'queen':
        return chess.QUEEN
    elif name == 'king':
        return chess.KING

def convert_pos_to_board(pos: List[pyswip.easy.Functor]) -> chess.Board:
    "Convert a list of contents/4 predicates into a board that can be used to generate legal moves"

    board = chess.Board(None)
    for predicate in pos:
        predicate_name = predicate.name.value
        side_str = predicate.args[0].value
        side = convert_side(side_str)
        if predicate_name == 'contents':
            piece_str = predicate.args[1].value
            file = predicate.args[2]
            rank = predicate.args[3]
            piece = chess.Piece(parse_piece(piece_str), side)
            square = chess.square(file - 1, rank - 1)
            board.set_piece_at(square, piece)
        elif predicate_name == 'turn':
            board.turn = side
        elif predicate_name == 'kingside_castle':
            if side == chess.WHITE:
                board.castling_rights |= chess.BB_H1
            else:
                board.castling_rights |= chess.BB_H8
        elif predicate_name == 'queenside_castle':
            if side == chess.WHITE:
                board.castling_rights |= chess.BB_A1
            else:
                board.castling_rights |= chess.BB_A8
        else:
            logger.error(f'Unknown predicate in position list: {predicate_name}')
    return board

# https://stackoverflow.com/a/63156085
def legal_move(_from, to, pos, handle):
    "Implementation of a foreign predicate which unifies with legal moves in the position"

    control = pyswip.core.PL_foreign_control(handle)

    index = None
    return_value = False

    if control == pyswip.core.PL_FIRST_CALL: # First call of legal_move
        index = 0
    
    if control == pyswip.core.PL_REDO:  # Subsequent call of legal_move
        last_index = pyswip.core.PL_foreign_context(handle)  # retrieve the index of the last call
        index = last_index + 1

    if control == pyswip.core.PL_PRUNED:  # A cut has destroyed the choice point
        return False
    
    board = convert_pos_to_board(pos)
    legal_moves = list(board.legal_moves)
    if 0 <= index < len(legal_moves):
        move = legal_moves[index]
        _from.unify(chess.square_name(move.from_square))
        to.unify(chess.square_name(move.to_square))
        return_value = pyswip.core.PL_retry(index)

    return return_value

def get_prolog() -> pyswip.prolog.Prolog:
    "Create the Prolog object and initialize it for the tactic-unification process"

    pyswip.registerForeign(legal_move, arity=3, flags=pyswip.core.PL_FA_NONDETERMINISTIC)
    prolog = pyswip.Prolog()
    prolog.consult(BK_FILE)
    return prolog

if __name__ == '__main__':
    prolog = get_prolog()
    contents = '[contents(white, rook, 1, 1), contents(white, knight, 2, 1), contents(white, bishop, 3, 1), contents(white, queen, 4, 1), contents(white, king, 5, 1), contents(white, bishop, 6, 1), contents(white, knight, 7, 1), contents(white, rook, 8, 1), contents(white, pawn, 1, 2), contents(white, pawn, 2, 2), contents(white, pawn, 3, 2), contents(white, pawn, 4, 2), contents(white, pawn, 6, 2), contents(white, pawn, 7, 2), contents(white, pawn, 8, 2), contents(white, pawn, 5, 4), contents(black, pawn, 5, 5), contents(black, pawn, 1, 7), contents(black, pawn, 2, 7), contents(black, pawn, 3, 7), contents(black, pawn, 4, 7), contents(black, pawn, 6, 7), contents(black, pawn, 7, 7), contents(black, pawn, 8, 7), contents(black, rook, 1, 8), contents(black, knight, 2, 8), contents(black, bishop, 3, 8), contents(black, queen, 4, 8), contents(black, king, 5, 8), contents(black, bishop, 6, 8), contents(black, knight, 7, 8), contents(black, rook, 8, 8), turn(white), kingside_castle(white), queenside_castle(white), kingside_castle(black), queenside_castle(black)]'
    r = prolog.query(f'legal_move(From, To, {contents})', maxresult=5)
    print(list(r))
