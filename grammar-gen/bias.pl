% enforce snake_case for pred names
% make sure format of bias predicates is correct, no error handling

max_body(5).
max_vars(5).

head_pred(f, 3).
type(f, (Pos, Square, Square)).
direction(f, (in, in, in)).

body_pred(make_move, 4).
type(make_move, (Square, Square, Pos, Pos)).
direction(make_move, (in, in, in, out)).

body_pred(attacks, 3).
type(attacks, (Square, Square, Pos)).
direction(attacks, (in, out, out)).

body_pred(different_pos, 2).
type(different_pos, (Square, Square)).
direction(different_pos, (out, out)).

body_pred(behind, 4).
type(behind, (Square, Square, Square, Pos)).
direction(behind, (in, out, out, in)).

body_pred(piece_at, 4).
type(piece_at, (Square, Pos, Side, Piece)).
direction(piece_at, (in, in, in, out)).

body_pred(other_side, 2).
type(other_side, (Side, Side)).
direction(other_side, (in, in)).