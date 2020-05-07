"""This file defines CLI for game"""

import re
from terminaltables import SingleTable

from core import GameCore
from events import RestartGame, QuitGame, CancelOperation



class GameCLI(GameCore):
    """Completed game class with CLI."""

    io_type = 'CLI'

    def difficulty_selection(self):
        """Printing options table and taking from user difficulty option."""
        # Preparing table_data
        options_dict = dict(enumerate(self.DIFFICULTIES, start=1))
        table_data = [['key', 'difficulty', 'size', 'digits']] # Header row
        for key, dif in options_dict.items(): # Difficultes row
            table_data.append([
                str(key),
                dif,
                self.DIFFICULTIES[dif]['num_size'],
                self.DIFFICULTIES[dif]['digs_range']
            ])
        table_data.append(['0', 'CANCEL', '-', '-']) # Cancel row

        # Creating difficulty table
        selection_table = SingleTable(table_data)
        selection_table.title = 'Difficulty selection'
        selection_table.justify_columns = {
            0: 'left', 1: 'left', 2: 'center', 3: 'center'
        }
        selection_table.inner_column_border = False

        print(selection_table.table)

        # Taking input
        while True:
            input_ = input('Enter key: ').strip()
            if not input_.isdigit() or (
                    int(input_) not in options_dict and input_ != '0'):
                print('  Invalid key!')
                continue
            break
        if input_ == '0':
            raise CancelOperation

        return options_dict[int(input_)]

    def wrong_characters_in_number_message(self, wrong_chars, wrong_input):
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

    def wrong_length_of_number_message(self, length):
        print(
            "  You entered {length} digits. {num_size} is correct."\
                .format(length=length, **vars(self)
            )
        )

    def repeated_digits_in_number_message(self, rep_digs_list):
        rep_digs_str = ', '.join(
            map(lambda x: "'"+x+"'", rep_digs_list)
        )
        print(
            "  Number can't have repeated digits. {} repeated."\
                .format(rep_digs_str)
        )

    def take_number(self):
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
        print('\n'.join([
            '  !q[uit]    - quit game',
            '  !r[estart] - restart game'
        ]))

    def score_message(self):
        print(
            "\n *** You guessed in {steps} steps ***\n"\
                .format(**vars(self))
        )


    def bulls_and_cows_message(self, bullscows):
        print(
            "  bulls: {bulls:>2}, cows: {cows:>2}"\
                .format(**bullscows, **vars(self))
        )

    def start_game(self):
        print('\n'.join([
                '+================================+',
                '|--------- Game started ---------|',
                '+================================+',
                '',
        ]))

    def end_game(self):
        print('\n'.join([
                '+================================+',
                '|---------- Game ended ----------|',
                '+================================+',
        ]))

    def start_round(self):
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

    def end_round(self):
        print(
            '======= Round ended ======\n'\
                .format(**vars(self))
        )

    def ask_if_continue_playing(self):
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
