import argparse
import logging
import math
from collections.abc import Callable
from typing import List, Optional, TextIO, Tuple

import chess
import chess.engine
import chess.pgn
from pyswip import Prolog
from pyswip.prolog import PrologError
from tqdm import tqdm

from prolog_parser import create_parser, parse_result_to_str
from util import (BK_FILE, LICHESS_2013, MAIA_1100, STOCKFISH, fen_to_contents,
                  games, get_engine, get_evals, get_top_n_moves)


logger = logging.getLogger(__name__)
logger.propagate = False # https://stackoverflow.com/a/2267567

def evaluate(evaluated_suggestions: List[Tuple[chess.engine.Score, chess.Move]], top_moves: List[Tuple[chess.engine.Score, chess.Move]], metric_fn: Callable[[int, float], float], mate_score: int=2000) -> float:
    "Calculate a metric by comparing a given list of evaluated moves to the top recommended moves"
    metric: float = 0
    for idx, (evaluated_move, top_move) in enumerate(zip(evaluated_suggestions, top_moves)):
        score, move = evaluated_move
        eval = score.score(mate_score=mate_score)
        score_top, move_top = top_move
        top_eval = score_top.score(mate_score=mate_score)
        error = abs(top_eval - eval)
        metric = metric_fn(idx, error)
    return metric

def get_tactic_match(prolog, text: str, board: chess.Board, limit: int=3, time_limit_sec: int=5) -> Tuple[Optional[bool], Optional[List[chess.Move]]]:
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

def calc_metrics(prolog, tactic_text: str, engine: chess.engine.SimpleEngine, pgn_file_handle: TextIO, game_limit: int=10, pos_limit: int=10) -> bool:
    metrics = {
        'total_games': 0,  # total number of games
        'total_positions': 0, # total number of positions (across all games)
        'total_matches': 0,
        'dcg': 0.0,
        'avg': 0.0,
        'empty_suggestions': 0
    }

    dcg_fn = lambda idx, error: error / math.log2(1 + (idx + 1))
    avg_fn = lambda _, error: error

    with tqdm(total=game_limit * pos_limit, desc='Positions', unit='positions', leave=False) as pos_progress_bar:
        for game in games(pgn_file_handle):
            metrics['total_games'] += 1
            curr_positions = 0
            node = game.next() # skip start position
            while not node.is_end():
                board = node.board()
                match, suggestions = get_tactic_match(prolog, tactic_text, board, limit=3)
                if match is None:
                    return False
                metrics['total_positions'] += 1 # don't include a position for which we don't have a result
                pos_progress_bar.update(1)
                logger.debug(f'Suggestions: {suggestions}')
                if match:
                    metrics['total_matches'] += 1
                    if suggestions:
                        evals = get_evals(engine, board, suggestions)
                        top_n_moves = get_top_n_moves(engine, board, len(suggestions))
                        metrics['dcg'] += evaluate(evals, top_n_moves, dcg_fn)
                        metrics['avg'] += evaluate(evals, top_n_moves, avg_fn)
                else:
                    logger.debug(f'Updated empty suggestions')
                    metrics['empty_suggestions'] += 1
                curr_positions += 1
                if pos_limit and curr_positions >= pos_limit:
                    break
                node = node.next()
            if game_limit and metrics['total_games'] >= game_limit:
                break
    
    if metrics['total_matches'] > 0:
        print_metrics(metrics, log_level=logging.INFO, tactic_text=tactic_text)
    else:
        print_metrics(metrics, log_level=logging.DEBUG, tactic_text=tactic_text)
    return True

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Calculate metrics for a set of chess tactics')
    parser.add_argument('tactics_file', type=str, help='file containing list of tactics')
    parser.add_argument('--log', dest='log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Set the logging level', default='INFO')
    parser.add_argument('-n', '--num_tactics', dest='tactics_limit', type=int, help='Number of tactics to analyze', default=100)
    parser.add_argument('-e', '--engine', dest='engine_path', default=STOCKFISH, help='Path to engine executable to use for calculating divergence')
    parser.add_argument('-p', '--position_db', dest='position_db', default=LICHESS_2013, help='Path to PGN file of positions to use for calculating divergence')
    parser.add_argument('--num-games', dest='num_games', type=int, default=10, help='Number of games to use')
    parser.add_argument('--pos-per-game', dest='pos_per_game', type=int, default=10, help='Number of positions to use per game')
    args = parser.parse_args()

    # Create logger
    logging.basicConfig(level=getattr(logging, args.log_level))
    logger = logging.getLogger(__name__)
    fmt = logging.Formatter('[%(levelname)s] [%(asctime)s] %(funcName)s:%(lineno)d - %(message)s')
    hdlr = logging.FileHandler('info.log', encoding='utf-8')
    hdlr.setFormatter(fmt)
    hdlr.setLevel(logging.DEBUG)
    logger.addHandler(hdlr)

    # Unpack cmdline arguments
    hspace_filename = args.tactics_file
    tactics_limit = args.tactics_limit
    engine_path = args.engine_path # for calculating divergence
    position_db = args.position_db
    position_handle = open(position_db) # TODO: pass file handle or filename as param?
    game_limit=args.num_games
    pos_limit = args.pos_per_game
    
    # Calculate metrics for each tactic
    prolog_parser = create_parser()
    with get_engine(engine_path) as engine:
        with open(hspace_filename) as hspace_handle:
            tactics_seen = 0
            with tqdm(total=tactics_limit, desc='Tactics', unit='tactics') as tactics_progress_bar:
                for line in hspace_handle:
                    logger.debug(line)
                    if line[0] == '%': # skip comments
                        continue
                    tactic = prolog_parser.parse_string(line)
                    logger.debug(tactic)
                    tactic_text = parse_result_to_str(tactic)
                    logger.debug(tactic_text)
                    
                    prolog = Prolog()
                    prolog.consult(BK_FILE)

                    success = calc_metrics(prolog, tactic_text, engine, position_handle, game_limit=game_limit, pos_limit=pos_limit)
                    tactics_seen += 1
                    tactics_progress_bar.update(1)
                    if tactics_seen >= tactics_limit:
                        break
    logger.info(f'% Calculated metrics for {tactics_seen} tactics')
    position_handle.close()

if __name__ == '__main__':
    main()
