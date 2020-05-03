"Implementation of 'Bulls and Cows' game"

__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


import re
from terminaltables import SingleTable

from core import GameCore


class GameCli(GameCore):
    """Completed game class with CLI."""

    io_type = 'cli'

    def difficulty_selection(self):
        """Printing options table and taking from user difficulty option."""
        # Creating difficulty table
        options_dict = dict(zip(range(1, len(self.DIFFICULTIES)+1),
                self.DIFFICULTIES))
        table_data = [['key', 'difficulty', 'size', 'digits']]
        for key, dif in options_dict.items():
            table_data.append([
                str(key),
                dif,
                self.DIFFICULTIES[dif]['number_size'],
                self.DIFFICULTIES[dif]['digits_range']
            ])
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
            if not input_.isdigit():
                print(
                    '  Input is not a digit!\n',
                    end='',
                )
                continue
            input_ = int(input_)
            if input_ not in options_dict:
                print(
                    '  Valid key!\n',
                    end='')
                continue
            break
        return options_dict[input_]

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

    def empty_input_message(self):
        print(
            '  Enter number!\n',
            end='',
        )

    def take_number(self):
        return input("[{steps}] ".format(**self.__dict__))

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
