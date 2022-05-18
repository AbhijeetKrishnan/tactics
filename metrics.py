import argparse
import csv
import logging
import math
from collections.abc import Callable
from typing import Generator, List, Optional, Tuple

import chess
import chess.engine
import chess.pgn
from pyswip import Prolog
from pyswip.prolog import PrologError
from tqdm import tqdm

from prolog_parser import create_parser, parse_result_to_str
from util import (BK_FILE, LICHESS_2013, MAIA_1100, STOCKFISH, fen_to_contents,
                  get_engine, get_evals, get_top_n_moves, positions_pgn, positions_list)

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
    prolog.retract(text)
    prolog.retractall('legal_move(_, _, _)')
    return match, suggestions

def print_metrics(metrics: dict, log_level=logging.INFO, **kwargs) -> None:
    tactic_text = kwargs['tactic_text']
    logger.log(log_level, f"Tactic: {tactic_text}")
    logger.log(log_level, f"# of positions: {metrics['total_positions']}")
    logger.log(log_level, f"Coverage: {metrics['total_matches'] / metrics['total_positions'] * 100:.2f}%") # % of matched positions
    if metrics['total_matches'] > 0:
        logger.log(log_level, f"Average number of suggestions per matched position: {metrics['num_suggestions'] / metrics['total_matches']:.2f}")
    logger.log(log_level, f"# of empty suggestions: {metrics['empty_suggestions']}/{metrics['total_positions']}") # number of positions where tactic did not suggest any move
    logger.log(log_level, f"Divergence = {metrics['divergence']:.2f}")
    logger.log(log_level, f"Average = {metrics['avg']:.2f}")

def write_metrics(metrics_list: List[dict], csv_filename: str) -> None:
    "Write metrics to csv file for analysis"
    with open(csv_filename, 'w') as csv_file:
        field_names = ['text', 'total_positions', 'total_matches', 'num_suggestions', 'divergence', 'avg']
        writer = csv.DictWriter(csv_file, fieldnames=field_names)
        writer.writeheader()
        for metrics in metrics_list:
            row = {
                'text': metrics['tactic_text'],
                'total_positions': metrics['total_positions'],
                'total_matches': metrics['total_matches'],
                'num_suggestions': metrics['num_suggestions'],
                'divergence': metrics['divergence'],
                'avg': metrics['avg']
            }
            writer.writerow(row)

def calc_metrics(prolog, tactic_text: str, engine: chess.engine.SimpleEngine, positions: Generator[chess.Board, None, None]) -> Optional[dict]:
    metrics = {
        'total_positions': 0, # total number of positions (across all games)
        'total_matches': 0,
        'divergence': 0.0,
        'avg': 0.0,
        'empty_suggestions': 0,
        'num_suggestions': 0
    }

    divergence_fn = lambda idx, error: error / math.log2(1 + (idx + 1))
    avg_fn = lambda _, error: error

    with tqdm(desc='Positions', unit='positions', leave=False) as pos_progress_bar:
        for board in positions:
            logger.debug(board)
            match, suggestions = get_tactic_match(prolog, tactic_text, board, limit=3)
            if match is None:
                return None
            metrics['total_positions'] += 1 # don't include a position for which we don't have a result
            pos_progress_bar.update(1)
            logger.debug(f'Suggestions: {suggestions}')
            if match:
                metrics['total_matches'] += 1
                if suggestions:
                    evals = get_evals(engine, board, suggestions)
                    top_n_moves = get_top_n_moves(engine, board, len(suggestions))
                    metrics['divergence'] += evaluate(evals, top_n_moves, divergence_fn)
                    metrics['avg'] += evaluate(evals, top_n_moves, avg_fn)
                    metrics['num_suggestions'] += len(suggestions)
            else:
                logger.debug(f'Updated empty suggestions')
                metrics['empty_suggestions'] += 1
    
    print_metrics(metrics, log_level=logging.DEBUG, tactic_text=tactic_text)
    return metrics

def parse_args():
    parser = argparse.ArgumentParser(description='Calculate metrics for a set of chess tactics')
    parser.add_argument('tactics_file', type=str, help='file containing list of tactics')
    parser.add_argument('--log', dest='log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Set the logging level', default='INFO')
    parser.add_argument('-n', '--num_tactics', dest='tactics_limit', type=int, help='Number of tactics to analyze', default=100)
    parser.add_argument('-e', '--engine', dest='engine_path', default=STOCKFISH, help='Path to engine executable to use for calculating divergence')
    parser.add_argument('--pgn', dest='pgn_file', default=LICHESS_2013, help='Path to PGN file of positions to use for calculating divergence')
    parser.add_argument('--num-games', dest='num_games', type=int, default=10, help='Number of games to use')
    parser.add_argument('--pos-per-game', dest='pos_per_game', type=int, default=10, help='Number of positions to use per game')
    parser.add_argument('--data-path', dest='data_path', type=str, default='metrics_data.csv', help='File path to which metrics should be written')
    parser.add_argument('--pos-list', dest='pos_list', type=str, help='Path to file contatining list of positions to use for calculating divergence')
    return parser.parse_args()

def create_logger(log_level):
    logging.basicConfig(level=getattr(logging, log_level))
    logger = logging.getLogger(__name__)
    fmt = logging.Formatter('[%(levelname)s] [%(asctime)s] %(funcName)s:%(lineno)d - %(message)s')
    hdlr = logging.FileHandler('info.log', encoding='utf-8')
    hdlr.setFormatter(fmt)
    hdlr.setLevel(logging.DEBUG)
    logger.addHandler(hdlr)
    return logger

def main():
    # Create argument parser
    args = parse_args()

    # Create logger
    logger = create_logger(args.log_level)
    
    # Calculate metrics for each tactic
    prolog_parser = create_parser()
    prolog = Prolog()
    prolog.consult(BK_FILE)
    metrics_list = []
    with get_engine(args.engine_path) as engine:
        with open(args.tactics_file) as hspace_handle:
            tactics_seen = 0
            with tqdm(total=args.tactics_limit, desc='Tactics', unit='tactics') as tactics_progress_bar:
                for line in hspace_handle:
                    logger.debug(line)
                    if line[0] == '%': # skip comments
                        continue
                    
                    # Get tactic
                    tactic = prolog_parser.parse_string(line)
                    logger.debug(tactic)
                    tactic_text = parse_result_to_str(tactic)
                    logger.debug(tactic_text)

                    # Get position list
                    if args.pos_list:
                        positions = positions_list(args.pos_list)
                    elif args.pgn_file:
                        positions = positions_pgn(args.pgn_file, args.num_games, args.pos_per_game)
                    
                    metrics = calc_metrics(prolog, tactic_text, engine, positions)
                    if metrics:
                        metrics['tactic_text'] = tactic_text
                        metrics_list.append(metrics)
                    tactics_seen += 1
                    tactics_progress_bar.update(1)
                    if tactics_seen >= args.tactics_limit:
                        break
    logger.info(f'% Calculated metrics for {tactics_seen} tactics')
    write_metrics(metrics_list, args.data_path)

if __name__ == '__main__':
    main()
