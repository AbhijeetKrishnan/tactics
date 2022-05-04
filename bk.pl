square(1,1). square(1,2). square(1,3). square(1,4). square(1,5). square(1,6). square(1,7). square(1,8).
square(2,1). square(2,2). square(2,3). square(2,4). square(2,5). square(2,6). square(2,7). square(2,8).
square(3,1). square(3,2). square(3,3). square(3,4). square(3,5). square(3,6). square(3,7). square(3,8).
square(4,1). square(4,2). square(4,3). square(4,4). square(4,5). square(4,6). square(4,7). square(4,8).
square(5,1). square(5,2). square(5,3). square(5,4). square(5,5). square(5,6). square(5,7). square(5,8).
square(6,1). square(6,2). square(6,3). square(6,4). square(6,5). square(6,6). square(6,7). square(6,8).
square(7,1). square(7,2). square(7,3). square(7,4). square(7,5). square(7,6). square(7,7). square(7,8).
square(8,1). square(8,2). square(8,3). square(8,4). square(8,5). square(8,6). square(8,7). square(8,8).

sameRow(X1,Y1,X2,Y2) :-
    square(X1,Y1),
    square(X2,Y2),
    X1 == X2.

sameCol(X1,Y1,X2,Y2) :-
    square(X1,Y1),
    square(X2,Y2),
    Y1 == Y2.

side(white).
side(black).
other_side(white,black).
other_side(black,white).

piece(Piece) :-
    member(Piece, [pawn, knight, bishop, rook, queen, king]).

sliding_piece(Piece) :-
    piece(Piece),
    member(Piece, [bishop, rook, queen]).

contents(Side,Piece,X,Y) :-
    side(Side),
    piece(Piece),
    square(X,Y).

move(FromX,FromY,ToX,ToY) :-
    square(FromX,FromY),
    square(ToX,ToY).

can_move(Piece, FromX, FromY, ToX, ToY) :-
    piece(Piece),
    square(FromX, FromY),
    square(ToX, ToY),
    DelX is ToX - FromX,
    DelY is ToY - FromY,
    allowed_del(Piece, DelX, DelY).

position(Pos) :- 
    % how to indicate list of contents/4 predicates?
    is_list(Pos).

allowed_del(knight, -1, 2).
allowed_del(knight, 1, 2).
allowed_del(knight, -2, 1).
allowed_del(knight, 2, 1).
allowed_del(knight, -2, -1).
allowed_del(knight, 2, -1).
allowed_del(knight, -1, -2).
allowed_del(knight, 1, -2).

allowed_del(bishop, -1, 1). allowed_del(bishop, 1, 1).
allowed_del(bishop, -2, 2). allowed_del(bishop, 2, 2).
allowed_del(bishop, -3, 3). allowed_del(bishop, 3, 3).
allowed_del(bishop, -4, 4). allowed_del(bishop, 4, 4).
allowed_del(bishop, -5, 5). allowed_del(bishop, 5, 5).
allowed_del(bishop, -6, 6). allowed_del(bishop, 6, 6).
allowed_del(bishop, -7, 7). allowed_del(bishop, 7, 7).

allowed_del(bishop, -1, -1). allowed_del(bishop, 1, -1).
allowed_del(bishop, -2, -2). allowed_del(bishop, 2, -2).
allowed_del(bishop, -3, -3). allowed_del(bishop, 3, -3).
allowed_del(bishop, -4, -4). allowed_del(bishop, 4, -4).
allowed_del(bishop, -5, -5). allowed_del(bishop, 5, -5).
allowed_del(bishop, -6, -6). allowed_del(bishop, 6, -6).
allowed_del(bishop, -7, -7). allowed_del(bishop, 7, -7).

allowed_del(king, -1, 0).
allowed_del(king, -1, 1).
allowed_del(king, 0, 1).
allowed_del(king, 1, 1).
allowed_del(king, 1, 0).
allowed_del(king, 1, -1).
allowed_del(king, 0, -1).
allowed_del(king, -1, -1).

allowed_del(rook, 0, 1). allowed_del(rook, 0, -1).
allowed_del(rook, 0, 2). allowed_del(rook, 0, -2).
allowed_del(rook, 0, 3). allowed_del(rook, 0, -3).
allowed_del(rook, 0, 4). allowed_del(rook, 0, -4).
allowed_del(rook, 0, 5). allowed_del(rook, 0, -5).
allowed_del(rook, 0, 6). allowed_del(rook, 0, -6).
allowed_del(rook, 0, 7). allowed_del(rook, 0, -7).

allowed_del(rook, 1, 0). allowed_del(rook, -1, 0).
allowed_del(rook, 2, 0). allowed_del(rook, -2, 0).
allowed_del(rook, 3, 0). allowed_del(rook, -3, 0).
allowed_del(rook, 4, 0). allowed_del(rook, -4, 0).
allowed_del(rook, 5, 0). allowed_del(rook, -5, 0).
allowed_del(rook, 6, 0). allowed_del(rook, -6, 0).
allowed_del(rook, 7, 0). allowed_del(rook, -7, 0).

allowed_del(queen, -1, 1). allowed_del(queen, 0, 1). allowed_del(queen, 1, 1).
allowed_del(queen, -2, 2). allowed_del(queen, 0, 2). allowed_del(queen, 2, 2).
allowed_del(queen, -3, 3). allowed_del(queen, 0, 3). allowed_del(queen, 3, 3).
allowed_del(queen, -4, 4). allowed_del(queen, 0, 4). allowed_del(queen, 4, 4).
allowed_del(queen, -5, 5). allowed_del(queen, 0, 5). allowed_del(queen, 5, 5).
allowed_del(queen, -6, 6). allowed_del(queen, 0, 6). allowed_del(queen, 6, 6).
allowed_del(queen, -7, 7). allowed_del(queen, 0, 7). allowed_del(queen, 7, 7).

allowed_del(queen, -1, 0).                           allowed_del(queen, 1, 0).  
allowed_del(queen, -2, 0).                           allowed_del(queen, 2, 0).  
allowed_del(queen, -3, 0).                           allowed_del(queen, 3, 0).  
allowed_del(queen, -4, 0).                           allowed_del(queen, 4, 0).  
allowed_del(queen, -5, 0).                           allowed_del(queen, 5, 0).  
allowed_del(queen, -6, 0).                           allowed_del(queen, 6, 0).  
allowed_del(queen, -7, 0).                           allowed_del(queen, 7, 0).  

allowed_del(queen, -1, -1). allowed_del(queen, 0, -1). allowed_del(queen, 1, -1).
allowed_del(queen, -2, -2). allowed_del(queen, 0, -2). allowed_del(queen, 2, -2).
allowed_del(queen, -3, -3). allowed_del(queen, 0, -3). allowed_del(queen, 3, -3).
allowed_del(queen, -4, -4). allowed_del(queen, 0, -4). allowed_del(queen, 4, -4).
allowed_del(queen, -5, -5). allowed_del(queen, 0, -5). allowed_del(queen, 5, -5).
allowed_del(queen, -6, -6). allowed_del(queen, 0, -6). allowed_del(queen, 6, -6).
allowed_del(queen, -7, -7). allowed_del(queen, 0, -7). allowed_del(queen, 7, -7).

to_coords(a1, 1, 1).
to_coords(a2, 1, 2).
to_coords(a3, 1, 3).
to_coords(a4, 1, 4).
to_coords(a5, 1, 5).
to_coords(a6, 1, 6).
to_coords(a7, 1, 7).
to_coords(a8, 1, 8).
to_coords(b1, 2, 1).
to_coords(b2, 2, 2).
to_coords(b3, 2, 3).
to_coords(b4, 2, 4).
to_coords(b5, 2, 5).
to_coords(b6, 2, 6).
to_coords(b7, 2, 7).
to_coords(b8, 2, 8).
to_coords(c1, 3, 1).
to_coords(c2, 3, 2).
to_coords(c3, 3, 3).
to_coords(c4, 3, 4).
to_coords(c5, 3, 5).
to_coords(c6, 3, 6).
to_coords(c7, 3, 7).
to_coords(c8, 3, 8).
to_coords(d1, 4, 1).
to_coords(d2, 4, 2).
to_coords(d3, 4, 3).
to_coords(d4, 4, 4).
to_coords(d5, 4, 5).
to_coords(d6, 4, 6).
to_coords(d7, 4, 7).
to_coords(d8, 4, 8).
to_coords(e1, 5, 1).
to_coords(e2, 5, 2).
to_coords(e3, 5, 3).
to_coords(e4, 5, 4).
to_coords(e5, 5, 5).
to_coords(e6, 5, 6).
to_coords(e7, 5, 7).
to_coords(e8, 5, 8).
to_coords(f1, 6, 1).
to_coords(f2, 6, 2).
to_coords(f3, 6, 3).
to_coords(f4, 6, 4).
to_coords(f5, 6, 5).
to_coords(f6, 6, 6).
to_coords(f7, 6, 7).
to_coords(f8, 6, 8).
to_coords(g1, 7, 1).
to_coords(g2, 7, 2).
to_coords(g3, 7, 3).
to_coords(g4, 7, 4).
to_coords(g5, 7, 5).
to_coords(g6, 7, 6).
to_coords(g7, 7, 7).
to_coords(g8, 7, 8).
to_coords(h1, 8, 1).
to_coords(h2, 8, 2).
to_coords(h3, 8, 3).
to_coords(h4, 8, 4).
to_coords(h5, 8, 5).
to_coords(h6, 8, 6).
to_coords(h7, 8, 7).
to_coords(h8, 8, 8).

sq(a1).
sq(a2).
sq(a3).
sq(a4).
sq(a5).
sq(a6).
sq(a7).
sq(a8).
sq(b1).
sq(b2).
sq(b3).
sq(b4).
sq(b5).
sq(b6).
sq(b7).
sq(b8).
sq(c1).
sq(c2).
sq(c3).
sq(c4).
sq(c5).
sq(c6).
sq(c7).
sq(c8).
sq(d1).
sq(d2).
sq(d3).
sq(d4).
sq(d5).
sq(d6).
sq(d7).
sq(d8).
sq(e1).
sq(e2).
sq(e3).
sq(e4).
sq(e5).
sq(e6).
sq(e7).
sq(e8).
sq(f1).
sq(f2).
sq(f3).
sq(f4).
sq(f5).
sq(f6).
sq(f7).
sq(f8).
sq(g1).
sq(g2).
sq(g3).
sq(g4).
sq(g5).
sq(g6).
sq(g7).
sq(g8).
sq(h1).
sq(h2).
sq(h3).
sq(h4).
sq(h5).
sq(h6).
sq(h7).
sq(h8).

attacks(From,To,Pos) :-
    position(Pos),
    sq(From),
    sq(To),
    to_coords(From, FromX, FromY),
    to_coords(To, ToX, ToY),
    member(contents(Side,Piece,FromX,FromY), Pos),
    member(contents(OtherSide,OtherPiece,ToX,ToY), Pos),
    other_side(Side, OtherSide),
    piece(Piece),
    piece(OtherPiece),
    can_move(Piece, FromX, FromY, ToX, ToY).

different_pos(S1, S2) :-
    sq(S1),
    sq(S2),
    to_coords(S1, X1, Y1),
    to_coords(S2, X2, Y2),
    square(X1, Y1),
    square(X2, Y2),
    ( 
        X1 =\= X2 -> true ;
        Y1 =\= Y2 -> true ;
        false
    ).
different_pos(S1, S2) :- different_pos(S2, S1).

piece_at(S, Pos, Side, Piece) :-
    sq(S),
    position(Pos),
    side(Side),
    piece(Piece),
    to_coords(S, X, Y),
    member(contents(Side, Piece, X, Y), Pos).

fork(Pos, From, To) :-
    make_move(From, To, Pos, NewPos),
    attacks(To, S1, NewPos),
    attacks(To, S2, NewPos),
    different_pos(S1, S2).

behind(Front, Middle, Back, Pos) :-
    sq(Front),
    sq(Middle),
    sq(Back),
    position(Pos),
    attacks(Front, Middle, Pos),
    attacks(Front, Back, Pos),
    piece_at(Front, Pos, _, Piece),
    sliding_piece(Piece).

pin(Pos, From, To) :-
    make_move(From, To, Pos, NewPos),
    behind(To, Middle, Back, NewPos),
    piece_at(To, NewPos, SameSide, _),
    piece_at(Middle, NewPos, OppSide, _),
    piece_at(Back, NewPos, OppSide, _),
    different_pos(Middle, Back),
    other_side(SameSide, OppSide).

% TODO: design a "state" property

% legal move is one where piece of move color exists at move location
% TODO: turn this into an actual legal_move property calculator?
% if I have this working correctly, I don't need to pass in all the legal moves in the target relation
legal_move(FromX,FromY,ToX,ToY,Pos) :-
    square(FromX, FromY),
    square(ToX, ToY),
    position(Pos),
    member(contents(_,Piece,FromX,FromY),Pos), % piece to be moved exists
    can_move(Piece,FromX,FromY,ToX,ToY). % move for the piece is theoretically permitted (if board was empty)
    
make_move(From, To, Pos, NewPos) :-
    \+ ground(NewPos),
    sq(From),
    sq(To),
    position(Pos),
    position(NewPos),
    to_coords(From, FromX, FromY),
    to_coords(To, ToX, ToY),
    legal_move(FromX,FromY,ToX,ToY,Pos),
    member(contents(Side,Piece,FromX,FromY),Pos),
    delete(Pos, contents(Side,Piece,FromX,FromY), TmpPos),
    append(TmpPos, [contents(Side, Piece, ToX, ToY)], TmpNewUnsortedPos),
    (
        ground(NewPos) ->
        sort(TmpNewUnsortedPos, NewSortedPos),
        sort(NewPos, NewSortedPos)
    ;   sort(TmpNewUnsortedPos, NewPos)
    ).

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%