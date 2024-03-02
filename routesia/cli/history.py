"""
hosteria/cli/history.py - Command history
"""
import os
import tempfile

HISTORY_FILE = os.path.expanduser("~/.local/routesia/rcl_history")


class HistoryCursor:
    def __init__(self, history: "History"):
        self.history = history
        if self.history.items:
            # The last item is a virtual empty string that is not in the items
            self.end_position = len(self.history.items)
            self.position = self.end_position
        else:
            self.position = None

    def previous(self):
        if self.position is not None:
            if self.position > 0:
                self.position -= 1
            return self.history.items[self.position]
        return ""

    def next(self):
        if self.position is not None:
            if self.position < self.end_position:
                self.position += 1
            if self.position == self.end_position:
                return ""
            return self.history.items[self.position]
        return ""


class History:
    def __init__(
        self,
        size: int = 16384,
        filename: str = HISTORY_FILE,
    ):
        self.size = size
        self.filename = filename

        self.items = []

        self.load()

    def load(self):
        if os.path.isfile(self.filename):
            with open(self.filename, "r") as f:
                self.items = f.read().split("\n")
                for line in f.readlines():
                    self.items.append(line.rstrip())

    def save(self):
        dirname = os.path.dirname(self.filename)
        if not os.path.isdir(dirname):
            os.makedirs(dirname, mode=0o0755)
        tmp = tempfile.mktemp(dir=dirname)
        with open(tmp, "w") as f:
            f.write("\n".join(self.items))
        os.rename(tmp, self.filename)

    def add(self, command: str):
        command = command.strip()

        # Don't insert blank commands
        if not command:
            return

        # Don't insert adjacent duplicates
        if self.items and self.items[-1] == command:
            return

        self.items.append(command)
        while len(self.items) > self.size:
            self.items.pop(0)

    def get_cursor(self):
        return HistoryCursor(self)
