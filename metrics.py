import logging
import math
import os
import sys
from parser import parse_file
from typing import List
import argparse

import chess
import chess.engine
import chess.pgn
from pyswip import Prolog
from pyswip.prolog import PrologError
from tqdm import tqdm

from fen_to_contents import fen_to_contents

BK_FILE = os.path.join('bk.pl')

LICHESS_2013 = os.path.join('data', 'lichess_db_standard_rated_2013-01.pgn')
STOCKFISH = os.path.join('bin', 'stockfish_14_x64')
MAIA_1100 = os.path.join(os.path.expanduser('~'), 'repos', 'lc0', 'build', 'release', 'lc0')

prolog = Prolog()
prolog.consult(BK_FILE)

logger = logging.getLogger(__name__)
logger.propagate = False # https://stackoverflow.com/a/2267567

def games(pgn):
    while game := chess.pgn.read_game(pgn):
        yield game

def get_evals(engine, board, suggestions):
    evals = []
    for move in suggestions:
        analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), root_moves=[move])
        # TODO: how to handle illegal move in suggestions?
        if 'pv' in analysis: 
            evals.append((analysis['score'].relative, analysis['pv'][0]))
    return evals

def evaluate(evaluated_suggestions, top_moves):
    dcg = 0
    for idx, (evaluated_move, top_move) in enumerate(zip(evaluated_suggestions, top_moves)):
        score, move = evaluated_move
        eval = score.score(mate_score=2000)
        score_top, move_top = top_move
        top_eval = score_top.score(mate_score=2000)
        error = abs(top_eval - eval)
        dcg += error / math.log2(1 + (idx + 1))
    return dcg

def evaluate_avg(evaluated_suggestions, top_moves):
    total = 0
    for idx, (evaluated_move, top_move) in enumerate(zip(evaluated_suggestions, top_moves)):
        score, move = evaluated_move
        eval = score.score(mate_score=2000)
        score_top, move_top = top_move
        top_eval = score_top.score(mate_score=2000)
        total += abs(top_eval - eval)
    return total / len(top_moves)

def get_top_n_moves(engine, n, board):
    analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), multipv=n)
    top_n_moves = [(root['score'].relative, root['pv'][0]) for root in analysis]
    return top_n_moves[:n]

def tactic(text, position: List, limit=3, time_limit_sec=20):
    "Given the text of a Prolog-based tactic, and a position, check whether the tactic matched in the given position or and if so, what were the suggested moves"
    
    prolog.assertz(text)
    query = f"f({position}, From, To)"
    logger.debug(f'Launching query: {query} with time limit: {time_limit_sec}s')
    try:
        results = list(prolog.query(f'call_with_time_limit({time_limit_sec}, {query})', maxresult=limit))
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
    return match, suggestions

def calc_metrics(tactic_text, engine, positions, game_limit=10, pos_limit=10):
    total_games = 0  # total number of games
    total_positions = 0 # total number of positions
    total_matches = 0
    dcg = 0
    avg = 0

    for game in games(positions):
        curr_positions = 0
        node = game.next() # skip start position
        while not node.is_end():
            board = node.board()
            board_predicate = fen_to_contents(board.fen())
            match, suggestions = tactic(tactic_text, board_predicate, limit=3)
            if match is None:
                return
            if match:
                total_matches += 1
                evals = get_evals(engine, board, suggestions)
                top_n_moves = get_top_n_moves(engine, len(suggestions), board)
                dcg += evaluate(evals, top_n_moves)
                avg += evaluate_avg(evals, top_n_moves)
            curr_positions += 1
            total_positions += 1
            if pos_limit and curr_positions >= pos_limit:
                break
            node = node.next()
        total_games += 1
        if game_limit and total_games >= game_limit:
            break
    
    if total_matches > 0:
        logger.info(f'Tactic: {tactic_text}')
        logger.info(f'# of games: {total_games}')
        logger.info(f'# of positions: {total_positions}')
        logger.info(f'Coverage: {total_matches}') # number of matched positions per game
        logger.info(f'DCG = {dcg}')
        logger.info(f'Average = {avg}')
    else:
        logger.debug(f'Tactic: {tactic_text}')
        logger.debug(f'# of games: {total_games}')
        logger.debug(f'# of positions: {total_positions}')
        logger.debug(f'Coverage: {total_matches}') # number of matched positions per game
        logger.debug(f'DCG = {dcg}')
        logger.debug(f'Average = {avg}')

def pred2str(predicate):
    "Converts a parsed predicate into its string representation"
    return f'{predicate.id}({",".join(predicate.args)})'

def parse_result_to_str(parse_result):
    "Converts a parsed hypothesis space into a list of tactics represented by strings"
    head_pred = pred2str(parse_result[0])
    body_preds = ','.join([pred2str(pred) for pred in parse_result[1:]])
    return f'{head_pred}:-{body_preds}'

def main():
    parser = argparse.ArgumentParser(description='Calculate metrics for a set of chess tactics')
    parser.add_argument('tactics_file', type=str, help='file containing list of tactics')
    parser.add_argument('--log', dest='log_level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], help='Set the logging level', default='INFO')
    parser.add_argument('-n', '--num_tactics', dest='tactics_limit', type=int, help='Number of tactics to analyze', default=100)
    parser.add_argument('-e', '--engine', dest='engine_path', default=STOCKFISH, help='Path to engine executable to use for calculating divergence')
    parser.add_argument('-p', '--position_db', dest='position_db', default=LICHESS_2013, help='Path to PGN file of positions to use for calculating divergence')
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

    tactics = parse_file(hspace_filename)
    tactics = sorted(tactics, key=lambda ele: len(ele) - 1)
    tactics = list(map(parse_result_to_str, tactics))
    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
    
    for tactic in tqdm(tactics[:tactics_limit]):
        tactic_text = tactic
        logger.debug(tactic_text)
        try:
            calc_metrics(tactic_text, engine, open(position_db), game_limit=10, pos_limit=10)
        except chess.engine.EngineTerminatedError:
            engine = chess.engine.SimpleEngine.popen_uci(engine_path)
            # TODO: how to handle engine failure on a tactic? Need to restart it
            tactics.append(tactic_text)
            continue
    engine.close()

if __name__ == '__main__':
    main()
