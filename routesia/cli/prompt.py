"""
hosteria/cli/prompt.py - Prompt implementation
"""

import sys

from routesia.cli.ansi import ansi
from routesia.cli.completion import Completion
from routesia.cli.history import History, HistoryCursor


class CompletionSelector:
    """
    Represents a completion selector
    """
    def __init__(self, completions: list[str | Completion], fragment: str, max_visible=5):
        self.completions = []
        for completion in completions:
            if not isinstance(completion, Completion):
                value = str(completion)
                completion = Completion(value, value)
            self.completions.append(completion)

        self.max_visible = max_visible
        self.update_fragment(fragment)

    def update_fragment(self, fragment: str):
        self.fragment = fragment
        self.visible_completion_index = 0
        self.selected_completion_index = None
        self.matching_completions = [completion for completion in self.completions if completion.value.startswith(self.fragment)]
        self.height = max(self.max_visible, len(self.matching_completions))
        if self.matching_completions:
            self.width = max([len(completion.display) for completion in self.matching_completions])
        else:
            self.width = 0

    @property
    def selection(self) -> str:
        if self.selected_completion_index is not None:
            return self.matching_completions[self.selected_completion_index]

    def view(self) -> str:
        """
        Get selector view to be displayed

        Returns a string with the necessary ANSI codes to display under the
        current cursor and return it to the original position.
        """
        if not self.matching_completions:
            return ""

        if self.selected_completion_index is not None:
            selected_completion = self.matching_completions[self.selected_completion_index]
        else:
            selected_completion = None

        visible_completions = self.matching_completions[self.visible_completion_index:self.visible_completion_index + self.max_visible]

        scroll_up = self.visible_completion_index > 0
        scroll_down = (len(self.matching_completions) - self.visible_completion_index) > self.max_visible

        s = ansi.save_cursor + ansi.down(1) + ansi.left(len(self.fragment))
        for i, completion in enumerate(visible_completions):
            selected = completion == selected_completion
            if not selected:
                s += ansi.reverse
            if i == 0 and scroll_up:
                s += "+"
            elif i == self.max_visible - 1 and scroll_down:
                s += "+"
            else:
                s += " "
            s += completion.display + " " * (self.width - len(completion.display) + 1)
            s += ansi.reset + ansi.down(1) + ansi.left(self.width + 2)

        s += ansi.restore_cursor

        return s

    def next(self):
        """
        Select next completion
        """
        if not self.matching_completions:
            return
        if self.selected_completion_index is None:
            self.selected_completion_index = 0
        else:
            self.selected_completion_index += 1
            if self.selected_completion_index == len(self.matching_completions):
                self.selected_completion_index = 0
                self.visible_completion_index = 0
            elif self.selected_completion_index >= (self.visible_completion_index + self.max_visible):
                self.visible_completion_index += 1

    def previous(self):
        """
        Select previous completion
        """
        if not self.matching_completions:
            return
        if self.selected_completion_index is None:
            self.selected_completion_index = len(self.matching_completions) - 1
            self.visible_completion_index = max(len(self.matching_completions) - self.max_visible, 0)
        else:
            self.selected_completion_index -= 1
            if self.selected_completion_index == -1:
                self.selected_completion_index = len(self.matching_completions) - 1
                if len(self.matching_completions) > self.max_visible:
                    self.visible_completion_index = max(len(self.matching_completions) - self.max_visible, 0)
            elif self.selected_completion_index < self.visible_completion_index:
                self.visible_completion_index -= 1


class Fragment:
    """
    Represents a fragment within a prompt input
    """
    def __init__(self, value, start, end):
        self.value = value
        self.start = start
        self.end = end


class Prompt:
    """
    Represents the contents of a prompt, tracking position and providing
    editing operations
    """
    def __init__(
            self,
            stdout=sys.stdout,
            input="",
            prefix: str = "> ",
            history: History | None = None,
        ):
        self.stdout = stdout
        self.input = input
        self.prefix = prefix
        self.history: History | None = history
        self.history_cursor: HistoryCursor | None = history.get_cursor() if history else None

        self.position = len(self.input)
        self.selector: CompletionSelector = None
        self.current_fragment = None

        self.display_prompt()

    def display(self, s, flush=True):
        """
        Display contents of ``s`` to the output

        If ``flush`` is True, the output will be flushed.
        """
        self.stdout.write(s)
        if flush:
            self.flush()

    def display_message(self, msg):
        msg = str(msg).replace("\n", "\r\n")
        self.display(f"{msg}\r\n")

    def flush(self):
        self.stdout.flush()

    def insert(self, key):
        if key == " " and self.selector:
            if self.selector.selected_completion_index is not None:
                # Accept and insert a space after
                self.accept_completion()
            else:
                self.reject_completion()
        self.input = self.input[:self.position] + key + self.input[self.position:]
        self.position += 1
        self.display(key)
        if self.position < len(self.input):
            self.display(ansi.save_cursor + self.input[self.position:] + ansi.restore_cursor)
        self.update_selector_fragment()

    def delete_left(self):
        if self.position > 0:
            original_fragment = self.get_current_fragment()
            remaining = self.input[self.position:]
            self.input = self.input[:self.position-1] + remaining
            self.position -= 1
            self.display(ansi.left(1) + ansi.clear_right, False)
            if remaining:
                self.display(remaining + ansi.left(len(remaining)), False)
            self.flush()
            if self.position >= original_fragment.start:
                self.update_selector_fragment()
            else:
                self.reject_completion()

    def delete_right(self):
        if self.position < len(self.input):
            remaining = self.input[self.position+1:]
            self.input = self.input[:self.position] + remaining
            self.display(ansi.clear_right, False)
            if remaining:
                self.display(remaining + ansi.left(len(remaining)), False)
            self.flush()
            self.update_selector_fragment()

    def cursor_left(self):
        if self.position > 0:
            if self.selector and self.current_fragment.start == self.position:
                self.reject_completion()
            self.position -= 1
            self.display(ansi.left(1))

    def cursor_right(self):
        if self.position < len(self.input):
            if self.selector and self.current_fragment.end == self.position:
                self.reject_completion()
            self.position += 1
            self.display(ansi.right(1))

    def cursor_home(self):
        if self.position > 0:
            self.display(ansi.left(self.position))
            self.position = 0

    def cursor_end(self):
        distance = len(self.input) - self.position
        if distance:
            self.display(ansi.right(distance))
            self.position = len(self.input)

    def up(self):
        if self.selector:
            self.selector.previous()
            self.display(self.selector.view())
        elif self.history_cursor:
            self.replace_input(self.history_cursor.previous())

    def down(self):
        if self.selector:
            self.selector.next()
            self.display(self.selector.view())
        elif self.history_cursor:
            self.replace_input(self.history_cursor.next())

    def replace_input(self, input):
        """
        Replace input
        """
        if self.position:
            self.display(ansi.left(self.position))
        self.display(input)
        distance = len(self.input) - len(input)
        if distance > 0:
            self.display(ansi.save_cursor + " " * distance + ansi.restore_cursor)
        self.input = input
        self.position = len(input)

    def update_fragment(self, completion: Completion):
        fragment = self.get_current_fragment()
        remaining = self.input[fragment.end:]
        delta = fragment.start + len(completion.value) - self.position
        self.input = self.input[:fragment.start] + completion.value + self.input[fragment.end:]
        if fragment.start < self.position:
            self.display(ansi.left(self.position - fragment.start), False)
        self.position += delta
        self.display(completion.value, False)
        if remaining:
            self.display(remaining + ansi.left(len(remaining)))
        self.flush()

    def get_fragments_before_cursor(self) -> list[str]:
        """
        Return input fragments before the cursor position

        It will not include the current fragment.
        """
        fragment = self.get_current_fragment()
        return self.input[:fragment.start].split()

    def get_current_fragment(self) -> Fragment:
        """
        Return the fragment under or behind the cursor.
        """
        if not self.input or (
            (
                self.position == 0 or
                self.input[self.position - 1] == " "
            )
            and
            (
                len(self.input) == self.position or
                self.input[self.position] == " "
            )
        ):
            return Fragment("", self.position, self.position)

        if self.input[self.position - 1] == " ":
            start = self.position
            end = self.input[self.position:].find(" ")
        else:
            start = self.input[:self.position - 1].rfind(" ") + 1
            end = self.input[self.position - 1:].find(" ")
        if end == -1:
            end = len(self.input)
        else:
            end += self.position - 1
        return Fragment(self.input[start:end], start, end)

    def display_prompt(self):
        self.display(self.prefix + self.input, False)
        if len(self.input) > self.position:
            self.display(ansi.left(len(self.input) - self.position))
        self.flush()

    def complete_next(self):
        if self.selector:
            self.selector.next()
            self.display(self.selector.view())

    def complete_previous(self):
        if self.selector:
            self.selector.previous()
            self.display(self.selector.view())

    def accept_completion(self):
        if self.selector:
            self.update_fragment(self.selector.selection)
            self.selector = None
            self.display(ansi.save_cursor + ansi.right(len(self.input) - self.position) + ansi.clear_down + ansi.restore_cursor)

    def reject_completion(self):
        if self.selector:
            self.selector = None
            self.current_fragment = None
            self.display(ansi.save_cursor + ansi.right(len(self.input) - self.position) + ansi.clear_down + ansi.restore_cursor)

    async def complete(self, completion_callback):
        """
        Call on complete key

        The ``completion_callback``, which must be an async function, will be
        called and passed a list of strings representing the command before
        the cursor, not including the current word. The callback must return a
        list of available completions. The result will be cached temporarily
        to avoid calling it multiple times per argument.

        If a completion has not been started, it will be started and the
        results displayed. If a completion has already been started, the next
        completion will be selected but not finished unless there is an
        unambiguous result.
        """
        if self.selector:
            if len(self.selector.matching_completions) == 1:
                self.update_fragment(self.selector.matching_completions[0])
                self.selector = None
                self.display(ansi.clear_down)
            else:
                self.complete_next()
        else:
            completions = await completion_callback(self.get_fragments_before_cursor())
            selector = CompletionSelector(completions, self.get_current_fragment().value)
            if not selector.matching_completions:
                # Beep if there are no matching completions
                self.display(ansi.bell)
                return
            if len(selector.matching_completions) == 1:
                self.update_fragment(selector.matching_completions[0])
                return
            self.selector = selector
            self.current_fragment = self.get_current_fragment()

            # Make some space for the selector view. Only needed the first
            # time
            self.display("\r\n" * self.selector.height + ansi.up(self.selector.height), False)

            # Re-display the prompt
            self.display_prompt()

            # Display the view
            self.display(self.selector.view())

    def update_selector_fragment(self):
        if self.selector:
            self.display(ansi.save_cursor + ansi.right(len(self.input) - self.position) + ansi.clear_down + ansi.restore_cursor, False)
            self.current_fragment = self.get_current_fragment()
            self.selector.update_fragment(self.current_fragment.value)
            self.display(self.selector.view())

    async def enter(self) -> bool:
        """
        Call on enter key and return whether the command should be handled

        Normally, this will simply return True. This indicated the input
        should be handled.

        If a completion has been started, it will be accepted and the input
        will be updated accordingly. The input should not be handled.
        """
        if self.selector:
            if self.selector.selected_completion_index is not None:
                self.accept_completion()
                return False
            else:
                self.reject_completion()
        if self.history:
            self.history.add(self.input)
        return True
