"""Play Othello on a Launchpad X."""

import time

import mido

INPUT_PORT = "MIDIIN2 (LPX MIDI) 1"
OUTPUT_PORT = "LPX MIDI 1"
BOARD_SIZE = 8

PROGRAMMER_MODE = [0x00, 0x20, 0x29, 0x02, 0x0C, 0x0E, 0x01]

EMPTY_COLOR = (1, 1, 1)
PLAYER1_COLOR = (0, 0, 127)
PLAYER2_COLOR = (127, 32, 0)
VALID_MOVE_COLOR = (0, 20, 0)
INVALID_MOVE_COLOR = (127, 0, 0)


def xy_to_note(x: int, y: int) -> int:
    """Convert board coordinates to a Launchpad note number."""
    return (BOARD_SIZE - 1 - y) * 10 + 11 + x


def note_to_xy(note: int) -> tuple[int, int] | None:
    """Convert a Launchpad note number to board coordinates."""
    row, col = divmod(note, 10)
    if not (1 <= row <= BOARD_SIZE and 1 <= col <= BOARD_SIZE):
        return None
    return col - 1, BOARD_SIZE - row


class Othello:
    EMPTY = 0
    PLAYER1 = 1
    PLAYER2 = 2
    DIRECTIONS = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    )

    def __init__(self) -> None:
        self.board = [[self.EMPTY] * BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.board[3][3] = self.PLAYER2
        self.board[3][4] = self.PLAYER1
        self.board[4][3] = self.PLAYER1
        self.board[4][4] = self.PLAYER2
        self.current_player = self.PLAYER1

    @staticmethod
    def inside(x: int, y: int) -> bool:
        return 0 <= x < BOARD_SIZE and 0 <= y < BOARD_SIZE

    @staticmethod
    def opponent(player: int) -> int:
        return Othello.PLAYER2 if player == Othello.PLAYER1 else Othello.PLAYER1

    def flips_for(self, x: int, y: int, player: int) -> list[tuple[int, int]]:
        """Return all opponent pieces that a move would flip."""
        if not self.inside(x, y) or self.board[y][x] != self.EMPTY:
            return []

        opponent = self.opponent(player)
        flips = []
        for dx, dy in self.DIRECTIONS:
            line = []
            nx, ny = x + dx, y + dy
            while self.inside(nx, ny) and self.board[ny][nx] == opponent:
                line.append((nx, ny))
                nx += dx
                ny += dy
            if line and self.inside(nx, ny) and self.board[ny][nx] == player:
                flips.extend(line)
        return flips

    def can_put(self, x: int, y: int, player: int) -> bool:
        return bool(self.flips_for(x, y, player))

    def valid_moves(self, player: int) -> list[tuple[int, int]]:
        return [
            (x, y)
            for y in range(BOARD_SIZE)
            for x in range(BOARD_SIZE)
            if self.can_put(x, y, player)
        ]

    def put(self, x: int, y: int) -> bool:
        flips = self.flips_for(x, y, self.current_player)
        if not flips:
            return False
        self.board[y][x] = self.current_player
        for fx, fy in flips:
            self.board[fy][fx] = self.current_player
        return True

    def next_turn(self) -> bool:
        opponent = self.opponent(self.current_player)
        if self.valid_moves(opponent):
            self.current_player = opponent
            return True
        return bool(self.valid_moves(self.current_player))

    def count(self) -> tuple[int, int]:
        player1 = sum(row.count(self.PLAYER1) for row in self.board)
        player2 = sum(row.count(self.PLAYER2) for row in self.board)
        return player1, player2


def send_rgb(port: mido.ports.BaseOutput, note: int, rgb: tuple[int, int, int]) -> None:
    """Set a Launchpad pad's RGB color."""
    port.send(
        mido.Message(
            "sysex", data=[0x00, 0x20, 0x29, 0x02, 0x0C, 0x03, 0x03, note, *rgb]
        )
    )


def update_display(game: Othello, port: mido.ports.BaseOutput) -> None:
    valid_moves = set(game.valid_moves(game.current_player))
    colors = {
        game.PLAYER1: PLAYER1_COLOR,
        game.PLAYER2: PLAYER2_COLOR,
    }
    for y, row in enumerate(game.board):
        for x, cell in enumerate(row):
            color = colors.get(
                cell, VALID_MOVE_COLOR if (x, y) in valid_moves else EMPTY_COLOR
            )
            send_rgb(port, xy_to_note(x, y), color)


def flash_invalid(port: mido.ports.BaseOutput, note: int) -> None:
    """Flash an invalid pad briefly."""
    send_rgb(port, note, INVALID_MOVE_COLOR)
    time.sleep(1)


def handle_note(game: Othello, output_port: mido.ports.BaseOutput, note: int) -> None:
    position = note_to_xy(note)
    if position is None:
        return

    x, y = position
    if not game.put(x, y):
        flash_invalid(output_port, note)
        update_display(game, output_port)
        return

    game.next_turn()
    update_display(game, output_port)


def main() -> None:
    game = Othello()
    with (
        mido.open_input(INPUT_PORT) as input_port,
        mido.open_output(OUTPUT_PORT) as output_port,
    ):
        output_port.send(mido.Message("sysex", data=PROGRAMMER_MODE))
        time.sleep(0.1)
        update_display(game, output_port)

        try:
            while True:
                for message in input_port.iter_pending():
                    if message.type == "note_on" and message.velocity > 0:
                        handle_note(game, output_port, message.note)
                time.sleep(0.01)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
