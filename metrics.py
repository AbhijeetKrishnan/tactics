import argparse
import logging
import math
from typing import List, Optional, TextIO, Tuple

import chess
import chess.engine
import chess.pgn
from pyswip import Prolog
from pyswip.prolog import PrologError
from tqdm import tqdm

from parser import parse_file, to_pred
from util import (BK_FILE, LICHESS_2013, MAIA_1100, STOCKFISH, fen_to_contents,
                  get_engine)

# TODO: brainstorm how to add this info in the bias file
PRED_VALUE = {
    'make_move': 0,
    'legal_move': 0,
    'attacks': 1,
    'behind': 1,
    'piece_at': 2,
    'different_pos': 3,
    'other_side': 3
}

logger = logging.getLogger(__name__)
logger.propagate = False # https://stackoverflow.com/a/2267567

def games(pgn_file_handle: TextIO):
    while game := chess.pgn.read_game(pgn_file_handle):
        yield game

def get_evals(engine: chess.engine.SimpleEngine, board: chess.Board, suggestions: List[chess.Move]) -> List[Tuple[float, chess.Move]]:
    evals = []
    for move in suggestions:
        analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), root_moves=[move])
        if 'pv' in analysis: 
            evals.append((analysis['score'].relative, analysis['pv'][0]))
    return evals

def evaluate(evaluated_suggestions: List[Tuple[float, chess.Move]], top_moves: List[chess.Move]) -> float:
    dcg = 0
    for idx, (evaluated_move, top_move) in enumerate(zip(evaluated_suggestions, top_moves)):
        score, move = evaluated_move
        eval = score.score(mate_score=2000)
        score_top, move_top = top_move
        top_eval = score_top.score(mate_score=2000)
        error = abs(top_eval - eval)
        dcg += error / math.log2(1 + (idx + 1))
    return dcg

def evaluate_avg(evaluated_suggestions: List[Tuple[float, chess.Move]], top_moves: List[chess.Move]) -> float:
    total = 0
    for idx, (evaluated_move, top_move) in enumerate(zip(evaluated_suggestions, top_moves)):
        score, move = evaluated_move
        eval = score.score(mate_score=2000)
        score_top, move_top = top_move
        top_eval = score_top.score(mate_score=2000)
        total += abs(top_eval - eval)
    return total / len(top_moves)

def get_top_n_moves(engine: chess.engine.SimpleEngine, n: int, board: chess.Board) -> List[Tuple[float, chess.Move]]:
    analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), multipv=n)
    top_n_moves = [(root['score'].relative, root['pv'][0]) for root in analysis]
    return top_n_moves[:n]

def tactic(prolog, text: str, board: chess.Board, limit: int=3, time_limit_sec: int=5) -> Tuple[Optional[bool], Optional[List[chess.Move]]]:
    "Given the text of a Prolog-based tactic, and a position, check whether the tactic matched in the given position or and if so, what were the suggested moves"
    
    position = fen_to_contents(board.fen())
    
    prolog.assertz(text)
    # assert legal moves based on current position
    for move in board.legal_moves:
        from_sq = chess.square_name(move.from_square)
        to_sq = chess.square_name(move.to_square)
        legal_move_pred = f'legal_move({from_sq}, {to_sq}, {position})'
        logger.debug(f'Legal move predicate: {legal_move_pred}')
        prolog.assertz(legal_move_pred)

    query = f"f({position}, From, To)"
    logger.debug(f'Launching query: {query} with time limit: {time_limit_sec}s')
    try:
        results = list(prolog.query(f'call_with_time_limit({time_limit_sec}, {query})', maxresult=limit))
        logger.debug(f'Results: {results}')
    except PrologError:
        logger.warning(f'timeout after {time_limit_sec}s on tactic {text}')
        return None, None
    if not results:
        match, suggestions = False, None
    else:
        match = True
        # convert suggestions to chess.Moves
        def suggestion_to_move(suggestion):
            from_sq = chess.parse_square(suggestion['From'])
            to_sq = chess.parse_square(suggestion['To'])
            return chess.Move(from_sq, to_sq)
        suggestions = list(map(suggestion_to_move, results))
    prolog.retract(text)
    prolog.retractall('legal_move(_, _, _)')
    return match, suggestions

def print_metrics(metrics: dict, log_level=logging.INFO, **kwargs) -> None:
    tactic_text = kwargs['tactic_text']
    logger.log(log_level, f"Tactic: {tactic_text}")
    logger.log(log_level, f"# of games: {metrics['total_games']}")
    logger.log(log_level, f"# of positions: {metrics['total_positions']}")
    logger.log(log_level, f"Coverage: {metrics['total_matches'] / metrics['total_positions'] * 100:.2f}%") # % of matched positions
    logger.log(log_level, f"# of empty suggestions: {metrics['empty_suggestions']}/{metrics['total_positions']}") # number of positions where tactic did not suggest any move
    logger.log(log_level, f"DCG = {metrics['dcg']:.2f}")
    logger.log(log_level, f"Average = {metrics['avg']:.2f}")

def calc_metrics(prolog, tactic_text: str, engine: chess.engine.SimpleEngine, pgn_file_handle: TextIO, game_limit: int=10, pos_limit: int=10) -> None:
    metrics = {
        'total_games': 0,  # total number of games
        'total_positions': 0, # total number of positions (across all games)
        'total_matches': 0,
        'dcg': 0,
        'avg': 0,
        'empty_suggestions': 0
    }

    for game in tqdm(games(pgn_file_handle), total=game_limit * pos_limit, desc='Positions', unit='positions', leave=False):
        curr_positions = 0
        node = game.next() # skip start position
        while not node.is_end():
            board = node.board()
            match, suggestions = tactic(prolog, tactic_text, board, limit=3)
            if match is None:
                return
            if match:
                metrics['total_matches'] += 1
                if suggestions:
                    evals = get_evals(engine, board, suggestions)
                    top_n_moves = get_top_n_moves(engine, len(suggestions), board)
                    metrics['dcg'] += evaluate(evals, top_n_moves)
                    metrics['avg'] += evaluate_avg(evals, top_n_moves)
                else:
                    metrics['empty_suggestions'] += 1
            curr_positions += 1
            metrics['total_positions'] += 1
            if pos_limit and curr_positions >= pos_limit:
                break
            node = node.next()
        metrics['total_games'] += 1
        if game_limit and metrics['total_games'] >= game_limit:
            break
    
    if metrics['total_matches'] > 0:
        print_metrics(metrics, log_level=logging.INFO, tactic_text=tactic_text)
    else:
        print_metrics(metrics, log_level=logging.DEBUG, tactic_text=tactic_text)

def parse_result_to_str(parse_result) -> str:
    "Converts a parsed hypothesis space into a list of tactics represented by strings"

    head_pred_str = to_pred(parse_result[0])
    body_preds = parse_result[1:]
    body_preds.sort(key=lambda pred: PRED_VALUE[pred.id])
    body_preds_str = ','.join([to_pred(pred) for pred in body_preds])
    tactic_str = f'{head_pred_str}:-{body_preds_str}'
    logger.debug(f'Tactic str: {tactic_str}')
    return tactic_str

def main():
    parser = argparse.ArgumentParser(description='Calculate metrics for a set of chess tactics')
    parser.add_argument('tactics_file', type=str, help='file containing list of tactics')
    parser.add_argument('--log', dest='log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Set the logging level', default='INFO')
    parser.add_argument('-n', '--num_tactics', dest='tactics_limit', type=int, help='Number of tactics to analyze', default=100)
    parser.add_argument('-e', '--engine', dest='engine_path', default=STOCKFISH, help='Path to engine executable to use for calculating divergence')
    parser.add_argument('-p', '--position_db', dest='position_db', default=LICHESS_2013, help='Path to PGN file of positions to use for calculating divergence')
    parser.add_argument('--num-games', dest='num_games', type=int, default=10, help='Number of games to use')
    parser.add_argument('--pos-per-game', dest='pos_per_game', type=int, default=10, help='Number of positions to use per game')
    args = parser.parse_args()

    logging.basicConfig(level=getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)
    fmt = logging.Formatter('[%(levelname)s] [%(asctime)s] %(funcName)s:%(lineno)d - %(message)s')
    hdlr = logging.FileHandler('info.log', encoding='utf-8')
    hdlr.setFormatter(fmt)
    hdlr.setLevel(logging.DEBUG)
    logger.addHandler(hdlr)

    hspace_filename = args.tactics_file
    tactics_limit = args.tactics_limit
    engine_path = args.engine_path # for calculating divergence
    position_db = args.position_db
    position_handle = open(position_db)
    game_limit=args.num_games
    pos_limit = args.pos_per_game

    tactics = parse_file(hspace_filename)
    tactics = sorted(tactics, key=lambda ele: len(ele) - 1)
    tactics = list(map(parse_result_to_str, tactics))
    
    with get_engine(engine_path) as engine:
        prolog = Prolog()
        prolog.consult(BK_FILE)
        for tactic in tqdm(tactics[:tactics_limit], desc='Tactics', unit='tactics'):
            tactic_text = tactic
            logger.debug(tactic_text)
            calc_metrics(prolog, tactic_text, engine, position_handle, game_limit=game_limit, pos_limit=pos_limit)

if __name__ == '__main__':
    main()
