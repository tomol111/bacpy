"Implementation of 'Bulls and Cows' game"

__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


import re
from terminaltables import SingleTable

from core import GameCore, RestartGame, QuitGame, CancelOperation



class GameCli(GameCore):
    """Completed game class with CLI."""

    io_type = 'cli'

    def difficulty_selection(self):
        """Printing options table and taking from user difficulty option."""
        # Preparing table_data
        options_dict = dict(enumerate(self.DIFFICULTIES, start=1))
        table_data = [['key', 'difficulty', 'size', 'digits']]
        for key, dif in options_dict.items():
            table_data.append([
                str(key),
                dif,
                self.DIFFICULTIES[dif]['number_size'],
                self.DIFFICULTIES[dif]['digits_range']
            ])
        table_data.append(['0', 'CANCEL', '-', '-'])

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
            if (not input_.isdigit()
                    or int(input_) not in options_dict
                    and input == '0'):
                print('  Valid key!\n', end='')
                continue
            break
        if input_ == '0':
            raise CancelOperation

        return options_dict[int(input_)]

    def wrong_characters_in_number_message(self, wrong_chars, wrong_input):
        wrong_chars = ', '.join(map(lambda x: "'"+x+"'", wrong_chars))
        print(
            '  Wrong characters: {wrong_chars}.'
            ' Correct are: "{digits_range}".\n'\
                .format(
                    wrong_chars=wrong_chars,
                    wrong_input=wrong_input,
                    **self.__dict__,
            ),
            end='',
        )

    def wrong_length_of_number_message(self, length):
        print(
            "  You entered {length} digits. {number_size} is correct.\n"\
                .format(
                    length=length,
                    **self.__dict__,
            ),
            end='',
        )

    def repeated_digits_in_number_message(self, repeated_digits):
        repeated_digits = ', '.join(
            map(lambda x: "'"+x+"'", repeated_digits)
        )
        print(
            "  Number can't have repeated digits. {} repeated.\n"\
                .format(repeated_digits),
            end='',
        )


    def take_number(self):
        while True:
            input_ = input("[{steps}] ".format(**self.__dict__)).strip()

            # Detect special input
            if len(input_) > 1:
                if re.match(input_, '!quit', flags=re.I):
                    raise QuitGame
                if re.match(input_, '!restart', flags=re.I):
                    raise RestartGame
            if re.match('!', input_, flags=re.I):
                self.special_input_hint_message()
                continue

            if not input_:
                print('  Enter number!\n', end='')
                continue

            # Remove whitespace characters and check number syntax
            input_ = re.sub(re.compile(r'\s+'), '', input_)
            if not self.is_number_syntax_corect(input_):
                continue

            return input_

    def special_input_hint_message(self):
        print(
            '  !q[uit]    - quit game\n'
            '  !r[estart] - restart game\n',
            end='',
        )

    def game_score_message(self):
        print(
            "\nYou guessed in {steps} steps.\n\n"\
                .format(**self.__dict__),
            end='',
        )


    def bulls_and_cows_message(self, bullscows):
        print(
            "  bulls: {bulls:>2}, cows: {cows:>2}\n"\
                .format(**bullscows, **self.__dict__),
            end='',
        )

    def initing_round(self):
        print(
            '\n'
            '===== Starting round =====\n'
            '\n'
            '  Difficulty:  {difficulty:>9}\n'
            '  Number size: {number_size:>9}\n'
            '  Digits range:{digits_range:>9}\n'
            '\n'
            ' ---- Enter numbers ----\n'
            '\n'\
                .format(**self.__dict__),
            end=''
        )

    def ending_round(self):
        print(
            '======= Round ended ======\n'\
                .format(**self.__dict__),
            end='',
        )

    def ask_if_continue_playing(self):
        while True:
            input_ = input(
                'Do you want to continue? [Y/n]: '\
                    .format(**self.__dict__)
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
                    '  Valid key!\n'.format(input_=input_),
                    end='',
                )


if __name__ == '__main__':
    # Run game
    GameCli().play()
