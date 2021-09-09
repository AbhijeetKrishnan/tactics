# Interpretable Chess Tactics

1. Download Lichess games database for [2013 -
   January](https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.bz2) from
   the [lichess.org open database](https://database.lichess.org/)
2. Unzip using `bzip2 -dk lichess_db_standard_rated_2013-01.pgn.bz2` and move into `data/` (create
   folder if necessary)
3. Generate `requirements.txt` using `pip freeze > requirements.txt`
4. Download the latest x64 Stockfish binary for Linux from the [Stockfish Downloads page]
   (https://stockfishchess.org/files/stockfish_14_linux_x64.zip) and move the binary named
   `stockfish_14_x64` into the `bin/` folder (create folder if necessary)
5. Give execution permissions to the Stockfish binary using `chmod +x stockfish_14_x64`
6. Run the Jupyter notebook
