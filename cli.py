"""This file defines CLI for game"""

import re

from core import MetaGame
from events import RestartGame, QuitGame, CancelOperation


class Game(MetaGame):
    """Completed game class with CLI."""

    io_type = 'CLI'

    def difficulty_selection(self):
        """Printing options table and taking from user difficulty option."""
        # Preparing table_data
        options_dict = dict(enumerate(self.DIFFICULTIES, start=1))
        top_table = (
                '-Difficulty selection-------------',
                '  key  difficulty  size  digits  ',
                '                                  ')
        rows_template = \
                '  {key:>2})   {difficulty:<10}  {size:^4}  {digits:^6}'
        bottom_table = (
                '   0)   CANCEL       -      -     ',
                '')
        inner_rows = [
                rows_template.format(
                    key=key,
                    difficulty=difficulty,
                    size=self.DIFFICULTIES[difficulty]['num_size'],
                    digits=self.DIFFICULTIES[difficulty]['digs_range']
                ) for key, difficulty in options_dict.items()
        ]

        table = '\n'.join([*top_table, *inner_rows, *bottom_table])
        print(table)

        # Taking input
        while True:
            input_ = input('Enter key: ').strip()
            if not input_.isdigit() or (
                    int(input_) not in options_dict and input_ != '0'):
                print('  Invalid key!')
                continue
            break
        print('----------------------------------')
        if input_ == '0':
            raise CancelOperation

        return options_dict[int(input_)]

    def _wrong_characters_in_number_message(self, wrong_chars, wrong_input):
        """Print wrong characters in number message"""
        wrong_chars = ', '.join(map(lambda x: "'"+x+"'", wrong_chars))
        print(
            '  Wrong characters: {wrong_chars}.'
            ' Correct are: "{digs_range}".'\
                .format(
                    wrong_chars=wrong_chars,
                    wrong_input=wrong_input,
                    **vars(self),
            )
        )

    def _wrong_length_of_number_message(self, length):
        """Print wrong length of number message"""
        print(
            "  You entered {length} digits but {num_size} is expected."\
                .format(length=length, **vars(self)
            )
        )

    def _repeated_digits_in_number_message(self, rep_digs_list):
        """Print repeated digits in number message"""
        rep_digs_str = ', '.join(
            map(lambda x: "'"+x+"'", rep_digs_list)
        )
        print(
            "  Number can't have repeated digits. {} repeated."\
                .format(rep_digs_str)
        )

    def _take_number(self):
        """Take number from user.

        Supports special input."""
        while True:
            input_ = input("[{steps}] ".format(**vars(self))).strip()

            if not input_:
                continue

            # Detect special input
            if input_.startswith('!'):
                if len(input_) > 1:
                    if re.match(input_[1:], 'quit'):
                        raise QuitGame
                    if re.match(input_[1:], 'restart'):
                        raise RestartGame
                self.special_input_hint_message()
                continue

            # Remove whitespace characters and check number syntax
            input_ = re.sub(r'\s+', '', input_)
            if not self.is_number_valid(input_):
                continue

            return input_

    def special_input_hint_message(self):
        """Print hint por special inputs message"""
        print('\n'.join([
            '  !q[uit]    - quit game',
            '  !r[estart] - restart game'
        ]))

    def _score_message(self):
        """Print score message"""
        print(
            "\n *** You guessed in {steps} steps ***\n"\
                .format(**vars(self))
        )


    def _bulls_and_cows_message(self, bullscows):
        """Print bolls and cows message"""
        print(
            "  bulls: {bulls:>2}, cows: {cows:>2}"\
                .format(**bullscows, **vars(self))
        )

    def _start_game(self):
        """Print game starting message"""
        print('\n'.join([
                '+================================+',
                '|--------- Game started ---------|',
                '+================================+',
                '',
        ]))

    def _end_game(self):
        """Print game ending message"""
        print('\n'.join([
                '+================================+',
                '|---------- Game ended ----------|',
                '+================================+',
        ]))

    def _start_round(self):
        """Print round starting message"""
        print('\n'.join([
            '',
            '===== Starting round =====',
            '',
            '  Difficulty:  {difficulty:>9}',
            '  Number size: {num_size:>9}',
            '  Digits range:{digs_range:>9}',
            '',
            ' ---- Enter numbers ----',
            ''])\
                .format(**vars(self))
        )

    def _end_round(self):
        """Print round ending message"""
        print(
            '======= Round ended ======\n'\
                .format(**vars(self))
        )

    def _ask_if_continue_playing(self):
        """Ask user if he want to continue plaing"""
        while True:
            input_ = input(
                'Do you want to continue? [Y/n]: '\
                    .format(**vars(self))
            )
            input_ = input_.strip()
            if not input_:
                return True
            if re.match(input_, 'yes', flags=re.I):
                return True
            elif re.match(input_, 'no', flags=re.I):
                return False
            else:
                print(
                    '  Invalid key!'.format(input_=input_)
                )
