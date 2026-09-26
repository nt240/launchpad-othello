import time

import mido


INPUT_PORT = "MIDIIN2 (LPX MIDI) 1"
OUTPUT_PORT = "LPX MIDI 1"

PROGRAMMER_MODE = [
    0x00, 0x20, 0x29,
    0x02, 0x0C,
    0x0E, 0x01,
]

# 色
EMPTY = (1, 1, 1)
BLACK = (0, 0, 127)       # 黒石 → 青
WHITE = (127, 127, 0)   # 白石 → 白
VALID = (0, 20, 0)        # 着手可能 → 緑
INVALID = (127, 0, 0)     # 置けない → 赤


def xy_to_note(x, y):
    return (7 - y) * 10 + 11 + x


def note_to_xy(note):
    row = note // 10
    col = note % 10

    if not (1 <= col <= 8):
        return None

    if not (1 <= row <= 8):
        return None

    x = col - 1
    y = 8 - row

    return x, y


class Othello:
    EMPTY = 0
    BLACK = 1
    WHITE = 2

    DIRECTIONS = [
        (-1, -1), (0, -1), (1, -1),
        (-1, 0),           (1, 0),
        (-1, 1),  (0, 1),  (1, 1),
    ]

    def __init__(self):
        self.board = [
            [self.EMPTY for _ in range(8)]
            for _ in range(8)
        ]

        self.board[3][3] = self.WHITE
        self.board[3][4] = self.BLACK
        self.board[4][3] = self.BLACK
        self.board[4][4] = self.WHITE

        self.current_player = self.BLACK

    def inside(self, x, y):
        return 0 <= x < 8 and 0 <= y < 8

    def can_put(self, x, y, player):
        if self.board[y][x] != self.EMPTY:
            return False

        opponent = (
            self.WHITE
            if player == self.BLACK
            else self.BLACK
        )

        for dx, dy in self.DIRECTIONS:
            nx = x + dx
            ny = y + dy
            found_opponent = False

            while self.inside(nx, ny):
                if self.board[ny][nx] == opponent:
                    found_opponent = True

                elif self.board[ny][nx] == player:
                    if found_opponent:
                        return True
                    break

                else:
                    break

                nx += dx
                ny += dy

        return False

    def valid_moves(self, player):
        moves = []

        for y in range(8):
            for x in range(8):
                if self.can_put(x, y, player):
                    moves.append((x, y))

        return moves

    def put(self, x, y):
        player = self.current_player

        if not self.can_put(x, y, player):
            return False

        opponent = (
            self.WHITE
            if player == self.BLACK
            else self.BLACK
        )

        self.board[y][x] = player

        for dx, dy in self.DIRECTIONS:
            to_flip = []

            nx = x + dx
            ny = y + dy

            while self.inside(nx, ny):
                if self.board[ny][nx] == opponent:
                    to_flip.append((nx, ny))

                elif self.board[ny][nx] == player:
                    for fx, fy in to_flip:
                        self.board[fy][fx] = player
                    break

                else:
                    break

                nx += dx
                ny += dy

        return True

    def next_turn(self):
        opponent = (
            self.WHITE
            if self.current_player == self.BLACK
            else self.BLACK
        )

        if self.valid_moves(opponent):
            self.current_player = opponent
            return True

        if self.valid_moves(self.current_player):
            print("パス")
            return True

        return False

    def count(self):
        black = sum(
            row.count(self.BLACK)
            for row in self.board
        )

        white = sum(
            row.count(self.WHITE)
            for row in self.board
        )

        return black, white

    def print_board(self):
        print()

        for row in self.board:
            print(
                " ".join(
                    "●" if cell == self.BLACK
                    else "○" if cell == self.WHITE
                    else "."
                    for cell in row
                )
            )

        black, white = self.count()

        player = (
            "黒"
            if self.current_player == self.BLACK
            else "白"
        )

        print(f"黒: {black}  白: {white}")
        print(f"手番: {player}")


def send_rgb(port, note, rgb):
    r, g, b = rgb

    message = [
        0x00, 0x20, 0x29,
        0x02, 0x0C,
        0x03,
        0x03,
        note,
        r, g, b,
    ]

    port.send(
        mido.Message(
            "sysex",
            data=message,
        )
    )


def update_display(game, port):
    valid = set(
        game.valid_moves(game.current_player)
    )

    for y in range(8):
        for x in range(8):
            note = xy_to_note(x, y)
            cell = game.board[y][x]

            if cell == game.BLACK:
                color = BLACK

            elif cell == game.WHITE:
                color = WHITE

            elif (x, y) in valid:
                color = VALID

            else:
                color = EMPTY

            send_rgb(port, note, color)


def flash_invalid(port, note):
    """置けない場所を赤くして1秒後に通常表示に戻す。"""
    send_rgb(port, note, INVALID)
    time.sleep(1)


def main():
    input_port = mido.open_input(INPUT_PORT)
    output_port = mido.open_output(OUTPUT_PORT)

    game = Othello()

    try:
        output_port.send(
            mido.Message(
                "sysex",
                data=PROGRAMMER_MODE,
            )
        )

        time.sleep(0.1)

        update_display(game, output_port)

        print("Launchpad X Othello")
        print("青 = 黒石")
        print("白 = 白石")
        print("緑 = 着手可能")
        print("赤 = 置けない場所")
        print("Ctrl+Cで終了")

        game.print_board()

        while True:
            for msg in input_port.iter_pending():

                if msg.type != "note_on":
                    continue

                if msg.velocity == 0:
                    continue

                position = note_to_xy(msg.note)

                if position is None:
                    continue

                x, y = position

                print(
                    f"入力: x={x}, y={y}, note={msg.note}"
                )

                # 着手成功
                if game.put(x, y):

                    game.print_board()

                    if not game.next_turn():
                        black, white = game.count()

                        print()
                        print("=== GAME OVER ===")
                        print(f"黒: {black}")
                        print(f"白: {white}")

                        if black > white:
                            print("黒の勝ち")
                        elif white > black:
                            print("白の勝ち")
                        else:
                            print("引き分け")

                    update_display(game, output_port)

                # 着手失敗
                else:
                    print("そこには置けません")

                    # 赤く光らせる
                    flash_invalid(output_port, msg.note)

                    # 元の盤面表示に戻す
                    update_display(game, output_port)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n終了します")

    finally:
        input_port.close()
        output_port.close()


if __name__ == "__main__":
    main()