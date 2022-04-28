import math
import os
from typing import List
import asyncio

import chess
import chess.engine
import chess.pgn
from pyswip import Prolog
from fen_to_contents import fen_to_contents

from grammar_gen import TacticGrammar
from parser import parse_file

BK_FILE = os.path.join('bk.pl')

LICHESS_2013 = os.path.join('data', 'lichess_db_standard_rated_2013-01.pgn')
STOCKFISH = os.path.join('bin', 'stockfish_14_x64')
MAIA_1100 = os.path.join(os.path.expanduser('~'), 'repos', 'lc0', 'build', 'release', 'lc0')

def games(pgn):
    while game := chess.pgn.read_game(pgn):
        yield game

def get_evals(engine, board, suggestions):
    evals = []
    for move in suggestions:
        # print(move)
        analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), root_moves=[move])
        # print(analysis)
        # TODO: how to handle illegal move in suggestions?
        if 'pv' in analysis: 
            evals.append((analysis['score'].relative, analysis['pv'][0]))
    return evals

def evaluate(evaluated_suggestions, top_moves):
    dcg = 0
    for idx, (evaluated_move, top_move) in enumerate(zip(evaluated_suggestions, top_moves)):
        # print(evaluated_move, top_move)
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
        # print(evaluated_move, top_move)
        score, move = evaluated_move
        eval = score.score(mate_score=2000)
        score_top, move_top = top_move
        top_eval = score_top.score(mate_score=2000)
        total += abs(top_eval - eval)
    return total / len(top_moves)

def get_top_n_moves(engine, n, board):
    analysis = engine.analyse(board, limit=chess.engine.Limit(depth=1), multipv=n)
    # print(analysis)
    top_n_moves = [(root['score'].relative, root['pv'][0]) for root in analysis]
    return top_n_moves[:n]

def tactic(text, position: List, limit=3):
    "Given the text of a Prolog-based tactic, and a position, check whether the tactic matched in the given position or and if so, what were the suggested moves"
    prolog = Prolog()
    prolog.consult(BK_FILE)
    # print(text)
    prolog.assertz(text)
    results = list(prolog.query(f"f({position}, From, To)"))
    #print(results[:limit])
    if not results:
        match, suggestions = None, None
    else:
        match = True
        # convert suggestions to chess.Moves
        def suggestion_to_move(suggestion):
            from_sq = chess.parse_square(suggestion['From'])
            to_sq = chess.parse_square(suggestion['To'])
            return chess.Move(from_sq, to_sq)
        
        suggestions = list(map(suggestion_to_move, results))
        suggestions = suggestions[:limit]
    return match, suggestions

# TODO: filter tactic text based on heuristics
def tactic_filter(tactic_text) -> bool:
    pass

def calc_metrics(tactic_text, engine_path, positions, game_limit=10, pos_limit=10):

    # print(tactic_text)

    total_games = 0  # total number of games
    total_positions = 0 # total number of positions
    total_matches = 0
    dcg = 0
    avg = 0

    engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    for game in games(positions):
        curr_positions = 0
        node = game.next() # skip start position
        while not node.is_end():
            board = node.board()
            board_predicate = fen_to_contents(board.fen())
            #print(board.fen())
            match, suggestions = tactic(tactic_text, board_predicate, limit=3)
            # print(match, suggestions)
            if match:
                total_matches += 1
                try:
                    evals = get_evals(engine, board, suggestions)
                    top_n_moves = get_top_n_moves(engine, len(suggestions), board)
                    dcg += evaluate(evals, top_n_moves)
                    avg += evaluate_avg(evals, top_n_moves)
                except chess.engine.EngineTerminatedError:
                    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
                    continue
            curr_positions += 1
            total_positions += 1
            if pos_limit and curr_positions >= pos_limit:
                break
            node = node.next()
        total_games += 1
        # if total_games % 5 == 0:
        #     print(f'# of games: {total_games}')
        #     print(f'# of positions: {total_positions}')
        #     print(f'Coverage: {total_matches}') # number of matched positions per game
        #     print(f'DCG = {dcg}')
        #     print(f'Average = {avg}')
        if game_limit and total_games >= game_limit:
            break
    engine.quit()

    print(f'Tactic: {tactic_text}')       
    print(f'# of games: {total_games}')
    print(f'# of positions: {total_positions}')
    print(f'Coverage: {total_matches}') # number of matched positions per game
    print(f'DCG = {dcg}')
    print(f'Average = {avg}')

def pred2str(predicate):
    return f'{predicate.id}({",".join(predicate.args)})'

def parse_result_to_str(parse_result):
    head_pred = pred2str(parse_result[0])
    body_preds = ','.join([pred2str(pred) for pred in parse_result[1:]])
    return f'{head_pred}:-{body_preds}'

def main():
    tactics = parse_file('hspace.txt')
    tactics = sorted(tactics, key=lambda ele: len(ele) - 1)
    tactics = map(parse_result_to_str, tactics)
    # print(tactics)
    tactics = filter(lambda ele: ele.count('make_move') > 0, tactics)
    # print(tactics)
    for tactic in tactics:
        tactic_text = tactic
        print(tactic_text)
        # calc_metrics(tactic_text, STOCKFISH, open(LICHESS_2013), game_limit=1, pos_limit=1)

if __name__ == '__main__':
    main()