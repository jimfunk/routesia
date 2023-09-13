"""
hosteria/cli/ansi.py - ANSI codes
"""


class ANSI:
    reset = "\x1b[0m"
    bold = "\x1b[1m"
    underline = "\x1b[4m"
    reverse = "\x1b[7m"
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    magenta = "\x1b[35m"
    cyan = "\x1b[36m"
    white = "\x1b[37m"
    bright_black = "\x1b[30;1m"
    bright_red = "\x1b[31;1m"
    bright_green = "\x1b[32;1m"
    bright_yellow = "\x1b[33;1m"
    bright_blue = "\x1b[34;1m"
    bright_magenta = "\x1b[35;1m"
    bright_cyan = "\x1b[36;1m"
    bright_white = "\x1b[37;1m"
    background_black = "\x1b[40m"
    background_red = "\x1b[41m"
    background_green = "\x1b[42m"
    background_yellow = "\x1b[43m"
    background_blue = "\x1b[44m"
    background_magenta = "\x1b[45m"
    background_cyan = "\x1b[46m"
    background_white = "\x1b[47m"
    background_bright_black = "\x1b[40;1m"
    background_bright_red = "\x1b[41;1m"
    background_bright_green = "\x1b[42;1m"
    background_bright_yellow = "\x1b[43;1m"
    background_bright_blue = "\x1b[44;1m"
    background_bright_magenta = "\x1b[45;1m"
    background_bright_cyan = "\x1b[46;1m"
    background_bright_white = "\x1b[47;1m"
    clear_right = "\x1b[0K"
    clear_left = "\x1b[1K"
    clear_line = "\x1b[2K"
    clear_up = "\x1b[1J"
    clear_down = "\x1b[0J"
    clear_screen = "\x1b[2J"
    save_cursor = "\x1b[s"
    restore_cursor = "\x1b[u"
    bell = "\x07"

    def up(self, n=1):
        return f"\x1b[{n}A"

    def down(self, n=1):
        return f"\x1b[{n}B"

    def right(self, n=1):
        return f"\x1b[{n}C"

    def left(self, n=1):
        return f"\x1b[{n}D"

    def line_down(self, n=1):
        """
        Down ``n`` lines and reset cursor to the leftmost position
        """
        return "\x1b[{n}E"

    def line_up(self, n=1):
        """
        Up ``n`` lines and reset cursor to the leftmost position
        """
        return "\x1b[{n}F"

    def column(self, x):
        """
        Set column to ``x``
        """
        return "\x1b[{x}G"

    def position(self, x, y):
        """
        Set position to column ``x`` and line ``y``
        """
        return "\x1b[{x};{y}H"


ansi = ANSI()
