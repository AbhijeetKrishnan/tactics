import logging
import os
from contextlib import contextmanager
from typing import Generator, List, Optional, Tuple, Union

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

def side_to_str(side: bool) -> str:
    return 'white' if side == chess.WHITE else 'black'

def str_to_side(side_str: str) -> bool:
    return chess.WHITE if side_str.lower() == 'white' else chess.BLACK

def fen_to_contents(fen: str) -> str:
    "Convert a FEN position into a contents predicate"

    board = chess.Board()
    board.set_fen(fen)
    board_str_list = []
    for square in chess.SQUARES:
        piece = board.piece_at(square)
        if piece:
            color = side_to_str(piece.color)
            piece_name = chess.piece_name(piece.piece_type)
            row = chess.square_rank(square) + 1
            col = chess.square_file(square) + 1
            board_str_list.append(f'contents({color}, {piece_name}, {col}, {row})')

    side_str = side_to_str(board.turn)
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

def parse_piece(name: str) -> int:
    name = name.lower()
    if name == 'pawn':
        ret_val = chess.PAWN
    elif name == 'knight':
        ret_val = chess.KNIGHT
    elif name == 'bishop':
        ret_val = chess.BISHOP
    elif name == 'rook':
        ret_val = chess.ROOK
    elif name == 'queen':
        ret_val = chess.QUEEN
    elif name == 'king':
        ret_val = chess.KING
    return ret_val

def convert_pos_to_board(pos: List[pyswip.easy.Functor]) -> chess.Board:
    "Convert a list of contents/4 predicates into a board that can be used to generate legal moves"

    board = chess.Board(None)
    for predicate in pos:
        predicate_name = predicate.name.value
        side_str = predicate.args[0].value
        side = str_to_side(side_str)
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
        
    if isinstance(_from, pyswip.easy.Variable):
        if 0 <= index < len(legal_moves):
            move = legal_moves[index]
            _from.unify(chess.square_name(move.from_square))
            to.unify(chess.square_name(move.to_square))
            return_value = pyswip.core.PL_retry(index)
    elif isinstance(_from, pyswip.easy.Atom):
        target = chess.Move(chess.parse_square(_from.value), chess.parse_square(to.value))
        return_value = target in legal_moves

    return return_value

def get_prolog() -> pyswip.prolog.Prolog:
    "Create the Prolog object and initialize it for the tactic-unification process"

    prolog = pyswip.Prolog()
    prolog.consult(BK_FILE)
    return prolog
