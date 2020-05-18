"""This file defines CLI for game"""

import re
import subprocess
import sys

from core import AbstractGame, AbstractRound, \
        QuitGame, RestartGame, CancelOperation


class CLITools:
    """Basic class for CLI."""

    io_type = 'CLI'

    def _ask_ok(self, prompt, default=True):
        """Yes-No input."""
        while True:
            try:
                input_ = re.escape(input(prompt).strip())
            except EOFError:
                print() # Print lost new line character
                raise CancelOperation
            except KeyboardInterrupt:
                print() # Print lost new line character
                continue

            if not input_:
                return default
            elif re.match(input_, 'yes', flags=re.I):
                return True
            elif re.match(input_, 'no', flags=re.I):
                return False

    def pager(self, string, program='less', args=None):
        """Use pager to show text."""
        if params is None:
            params=[]
        with subprocess.Popen([program, *params],
                stdin=subprocess.PIPE, stdout=sys.stdout) as pager:
            pager.stdin.write(str.encode(string))
            pager.stdin.close()
            pager.wait()


class Round(AbstractRound, CLITools):
    """Completed round class with CLI."""

    def _start_round(self):
        """Print round starting message"""
        print('\n'.join([
            '',
            '===== Starting round =====',
            '',
           f'  Difficulty:  {self._difficulty:>9}',
           f'  Number size: {self._num_size:>9}',
           f'  Digits range:{self._digs_range:>9}',
            '',
        ]))

    def _end_round(self):
        """Print round ending message"""
        print('======= Round ended ======\n')

    def _wrong_chars_in_num_output(self, wrong_chars, wrong_input):
        """Print wrong characters in number message"""
        wrong_chars = ', '.join(map(lambda x: "'"+x+"'", wrong_chars))
        print(
            f'  Wrong characters: {wrong_chars}.'
            f' Correct are: "{self._digs_range}".'
        )

    def _wrong_num_len_output(self, length):
        """Print wrong length of number message"""
        print(f"  You entered {length} digits but {self._num_size} is expected.")

    def _rep_digs_in_num_output(self, rep_digs, wrong_input):
        """Print repeated digits in number message"""
        rep_digs_str = ', '.join(
            map(lambda x: "'"+x+"'", rep_digs)
        )
        print(f"  Number can't have repeated digits. {rep_digs_str} repeated.")

    def _number_input(self):
        """Take number from user.

        Supports special input."""
        while True:
            try:
                input_ = input(f"[{self._steps}] ").strip()
            except EOFError:
                print() # Print lost new line character
                try:
                    if self._ask_ok(
                            'Do you really want to quit? [Y/n]: '):
                        raise QuitGame
                    else:
                        continue
                except CancelOperation:
                    raise QuitGame
                continue
            except KeyboardInterrupt:
                print() # Print lost new line character
                continue

            if not input_:
                continue

            # Detect special input
            if input_.startswith('!'):
                if len(input_) > 1:
                    command = input_[1:]
                    if re.match(command, 'quit'):
                        raise QuitGame
                    elif re.match(command, 'restart'):
                        raise RestartGame
                    elif re.match(command, 'help'):
                        self.show_help()
                        continue
                    else:
                        self.special_input_hint_output()
                        continue
                else:
                    self.special_input_hint_output()
                    continue

            input_ = re.sub(r'\s+', '', input_)
            if not self.is_number_valid(input_):
                continue

            return input_

    def special_input_hint_output(self):
        """Print hint for special inputs message"""
        print('\n'.join([
            '  !q[uit]    - quit game',
            '  !r[estart] - restart game'
        ]))

    def show_help(self):
        """Show message about game and rules."""
        self.pager('\n'.join([
            '# HELP ',
            '',
            'BacPy is "Bulls and Cows" game implementation.',
            '',
            'Rules are:',
            '   * You have to guess number of witch digits do not repeat.',
            '   * Enter your guess and program will return numbers of',
            '     bulls (amount of digits that are correct and have',
            '     correct position) and cows (amount of correct digits',
            '     but with wrong position).',
            '   * Try to find correct number with fewest amount of',
            '     attempts.']),
            args=['-C'] # Prevent from showing text on bottom of the screen
        )

    def _score_output(self):
        """Print score message"""
        print(f"\n *** You guessed in {self._steps} steps ***\n")


    def _bulls_and_cows_output(self, bulls, cows):
        """Print bulls and cows message"""
        print(f"  bulls: {bulls:>2}, cows: {cows:>2}")


class Game(AbstractGame, CLITools):
    """Completed game class with CLI."""

    def __init__(self, Round=Round, difficulty=None):
        super().__init__(Round, difficulty)

    def difficulty_input(self):
        """Printing options table and taking from user difficulty option."""
        # Preparing table_data
        options_dict = dict(enumerate(self.DIFFICULTIES, start=1))
        top_table = (
                '------ Difficulty selection ------',
                '                                  ',
                '  key  difficulty   size  digits  ',
        )
        inner_row_template = \
                ' {key:>2})    {difficulty:<11} {size:^4}  {digits:^6} '
        bottom_table = ('',)
        selection_end = \
                '----------------------------------'
        inner_rows = (
                inner_row_template.format(
                    key=key,
                    difficulty=difficulty.name,
                    size=difficulty.num_size,
                    digits=difficulty.digs_range
                ) for key, difficulty in options_dict.items()
        )

        table = '\n'.join([*top_table, *inner_rows, *bottom_table])
        print(table)

        # Taking input
        while True:
            try:
                input_ = input('Enter key: ').strip()
            except EOFError:
                print() # Print lost new line character
                print(selection_end)
                raise CancelOperation
            except KeyboardInterrupt:
                print() # Print lost new line character
                continue

            if not input_.isdigit() or int(input_) not in options_dict:
                continue
            else:
                break

        print(selection_end)

        return options_dict[int(input_)]

    def _start_game(self):
        """Print game starting message"""
        print('\n'.join([
                '==================================',
                '---------- Game started ----------',
                '==================================',
                '',
        ]))

    def _end_game(self):
        """Print game ending message"""
        print('\n'.join([
                '==================================',
                '----------- Game ended -----------',
                '==================================',
        ]))

    def _ask_if_continue_playing(self):
        """Ask user if he want to continue playing"""
        return self._ask_ok('Do you want to continue? [Y/n]: ')
