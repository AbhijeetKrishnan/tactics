import argparse
import csv
import os
import random
from contextlib import contextmanager
from typing import List, Optional, TextIO, Union
import code

Seed = Optional[Union[int, float, str, bytes, bytearray]]
PathLike = Union[str, bytes, os.PathLike]

import chess
import chess.engine
import chess.pgn

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

def sample_pgn(handle: TextIO, num_games: int=10, pos_per_game: int=10, seed: Seed=1) -> List[chess.Board]:
    "Sample positions from games in a PGN file"
    random.seed(seed)
    result = []

    # obtain num_game offsets from list of games
    offsets = []
    # code.interact(local=locals())
    while _ := chess.pgn.read_headers(handle) is not None:
        offset = handle.tell()
        offsets.append(offset)
    sampled_offsets = random.sample(offsets, num_games)

    # obtain pos_per_game positions from sampled list of games
    for offset in sampled_offsets:
        handle.seek(offset)
        game = chess.pgn.read_game(handle)
        positions = []
        node = game.next()
        while not node.is_end():
            board = node.board()
            positions.append(board)
            node = node.next()
        sampled_positions = random.sample(positions, pos_per_game)
        result.extend(sampled_positions)

    return result

def get_engine_moves(engine: chess.engine.SimpleEngine, position: chess.Board, pos_limit: int=3) -> List[chess.Move]:
    "Get engine move recommendations for a given position"
    analysis = engine.analyse(position, limit=chess.engine.Limit(depth=1), multipv=pos_limit)
    top_n_moves = [(root['score'].relative, root['pv'][0]) for root in analysis][:pos_limit]
    return top_n_moves

def gen_exs(exs_pgn_path: PathLike, engine_path: PathLike, num_games: int=10, pos_per_game: int=10, neg_to_pos_ratio: int=3):
    
    with open(exs_pgn_path) as handle:
        sample_positions = sample_pgn(handle, num_games=num_games, pos_per_game=pos_per_game)
    
    with get_engine(engine_path) as engine:
        for position in sample_positions:
            moves = get_engine_moves(engine, position, neg_to_pos_ratio + 1)
            if not moves:
                continue
            _, top_move = moves[0]
            yield {'fen': position.fen(), 'uci': top_move.uci(), 'label': 1}
            for _, move in moves[1:]:
                yield {'fen': position.fen(), 'uci': move.uci(), 'label': 0}

def main():
    parser = argparse.ArgumentParser(description='Generate tactic training examples and write them to a csv file')
    parser.add_argument('example_file', type=str, help='File to write generated examples to')
    parser.add_argument('-i', '--pgn', dest='pgn_file', type=str, default=LICHESS_2013, help='PGN file containing games')
    parser.add_argument('-e', '--engine', dest='engine_path', default=STOCKFISH, help='Path to engine executable to use for recommending moves')
    parser.add_argument('-n', '--num-games', dest='num_games', type=int, default=10, help='Number of games to use')
    parser.add_argument('-p', '--pos-per-game', dest='pos_per_game', type=int, default=10, help='Number of positions to use per game')
    parser.add_argument('-r', '--ratio', dest='neg_to_pos_ratio', type=int, default=3, help='Ratio of negative to positive examples to generate')
    args = parser.parse_args()

    with open(args.example_file, 'w') as output:
        field_names = ['fen', 'uci', 'label']
        writer = csv.DictWriter(output, fieldnames=field_names)

        writer.writeheader()
        for ex in gen_exs(args.pgn_file, args.engine_path, args.num_games, args.pos_per_game, args.neg_to_pos_ratio):
            writer.writerow(ex)

if __name__ == '__main__':
    main()
