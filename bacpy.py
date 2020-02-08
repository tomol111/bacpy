"Terminal implementation of 'Bulls and Cows' game"

__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


import random
import re
from collections import Counter
from terminaltables import SingleTable


DIFFICULTIES = {
    'easy': {
        'possible_digits': '123456',
        'digits_range': '1-6',
        'number_size': 3,
    },
    'normal': {
        'possible_digits': '123456789',
        'digits_range': '1-9',
        'number_size': 4,
    },
    'hard': {
        'possible_digits': '123456789ABCDEF',
        'digits_range': '1-9,A-F',
        'number_size': 5,
    },
}

class IOManager:
    """Handle all I/O interface with user by static methods"""

    io_type = 'terminal'

    @staticmethod
    def difficulty_menu_selection():
        """Printing options table and taking from user difficulty option."""
        # creating difficulty table
        options_dict = dict(zip(range(1, len(DIFFICULTIES)+1), DIFFICULTIES))
        table_data = [['key', 'difficulty', 'size', 'digits']]
        for key, dif in options_dict.items():
            table_data.append([
                str(key),
                dif,
                DIFFICULTIES[dif]['number_size'],
                DIFFICULTIES[dif]['digits_range']
            ])
        selection_table = SingleTable(table_data)
        selection_table.title = 'Difficulty selection'
        selection_table.justify_columns = {
            0: 'left', 1: 'left', 2: 'center', 3: 'center'
        }
        selection_table.inner_column_border = False
        print(selection_table.table)

        # taking input
        while True:
            input_ = input('Enter key: ').strip()
            if not input_.isdigit():
                print(
                    'Input is not a digit!\n',
                    end='',
                )
                continue
            input_ = int(input_)
            if input_ not in options_dict:
                print(
                    'Valid key!\n',
                    end='')
                continue
            break
        return options_dict[input_]

    @staticmethod
    def wrong_characters_in_number_message(wrong_chars, wrong_input, **game_kwa):
        wrong_chars = ', '.join(map(lambda x: "'"+x+"'", wrong_chars))
        print(
            'Found wrong characters: {wrong_chars}\n'
            '"{digits_range}" only available.\n'\
                .format(
                    wrong_chars=wrong_chars,
                    wrong_input=wrong_input,
                    **game_kwa,
            ),
            end='',
        )

    @staticmethod
    def wrong_length_of_number_message(wrong_input, **game_kwa):
        print(
            "Number should have {number_size} digits. "\
            "You entered {length}.\n"\
                .format(
                    length=len(wrong_input),
                    wrong_input=wrong_input,
                    **game_kwa,
            ),
            end='',
        )

    @staticmethod
    def repeated_digits_in_number_message(repeated_digits):
        repeated_digits = ', '.join(
            map(lambda x: "'"+x+"'", repeated_digits)
        )
        print(
            "Number can`t have repeated digits. {} repeated.\n"\
                .format(repeated_digits),
            end='',
        )

    @staticmethod
    def empty_input_message():
        print(
            'Enter number!\n',
            end='',
        )

    @staticmethod
    def take_number(**game_kwa):
        return input("[{steps}] ".format(**game_kwa))

    @staticmethod
    def special_input_hint_message():
        print(
            '%q[uit]    - quit game\n'
            '%r[estart] - restart game\n',
            end='',
        )

    @staticmethod
    def game_score_message(**game_kwa):
        print(
            "\nYou guessed in {steps} steps.\n\n"\
                .format(**game_kwa),
            end='',
        )


    @staticmethod
    def bulls_and_cows_message(bullscows, **game_kwa):
        print(
            "bulls: {bulls:>2}, cows: {cows:>2}\n"\
                .format(**bullscows, **game_kwa),
            end='',
        )

    @staticmethod
    def initing_round(**game_kwa):
        print(
            '\n'
            '===== Starting round =====\n'
            '\n'
            '  Difficulty:  {difficulty:>9}\n'
            '  Number size: {number_size:>9}\n'
            '  Digits range:{digits_range:>9}\n'
            '\n'
            '  --- Enter numbers ---\n'\
                .format(**game_kwa),
            end=''
        )

    @staticmethod
    def ending_round(**game_kwa):
        print(
            '======= Round ended ======\n'\
                .format(**game_kwa),
            end='',
        )

    @staticmethod
    def ask_if_continue_playing(**game_kwa):
        while True:
            input_ = input(
                'Do you want to continue? [y/n]: '\
                    .format(**game_kwa)
            )
            input_ = input_.strip()
            if len(input_) == 0:
                print(
                    'Enter key!\n',
                    end='',
                )
                continue
            if re.match(input_, 'yes', flags=re.I):
                return True
            elif re.match(input_, 'no', flags=re.I):
                return False
            else:
                print(
                    'Valid key!\n'.format(input_=input_),
                    end='',
                )

class Game:
    """Game class"""

    def __init__(self):
        self.difficulty = None
        self.number_size = None
        self.possible_digits = None
        self.digits_range = None
        self.number = None
        self.steps = None


    def draw_number(self):
        """Draw number digits from self.possible_digits."""
        self.number = ''.join(
            random.sample(self.possible_digits, self.number_size)
        )


    def set_difficulty(self, difficulty=None):
        """Setting game difficulty.

        Ask user if not given directly.
        """
        # ask for difficulty if not given directly
        if difficulty is None:
            self.difficulty = IOManager.difficulty_menu_selection()
        else:
            self.difficulty = difficulty

        # setting difficulty
        mode = DIFFICULTIES[self.difficulty]
        self.number_size = mode['number_size']
        self.possible_digits = mode['possible_digits']
        self.digits_range = mode['digits_range']


    def comput_bullscows(self, guess):
        """Return bulls and cows for given string comparing to self."""
        bulls, cows = 0, 0

        for i in range(self.number_size):
            if re.match(guess[i], self.number[i], flags=re.I):
                bulls += 1
            elif re.search(guess[i], self.number, flags=re.I):
                cows += 1

        return {'bulls': bulls, 'cows': cows}


    def is_syntax_corect(self, other):
        """Check if given string have correct syntax and can be compared to self."""

        # check if number have wrong characters
        wrong_chars = []
        for i in other:
            if not re.search(i, self.possible_digits, re.I):
                if i not in wrong_chars:
                    wrong_chars.append(i)
        if wrong_chars:
            IOManager.wrong_characters_in_number_message(
                wrong_chars,
                other,
                **self.__dict__,
            )
            return False

        # check length
        if len(other) != self.number_size:
            IOManager.wrong_length_of_number_message(
                other,
                **self.__dict__
            )
            return False

        # check that digits don`t repeat
        counter = Counter(other)
        repeated_digits = [i for i in counter.keys() if counter[i] > 1]
        if repeated_digits:
            IOManager.repeated_digits_in_number_message(repeated_digits)
            return False

        # finally number is correct
        return True

    def round(self):
        """Round method.

        Handle inserting answers, taking special commands, viewing results.

        RETURN:
            'quit' - if player inserted '%quit'
            'restart' - if player inserted '%restart'
            'end' - if game ended successfully
        """
        IOManager.initing_round(**self.__dict__)
        while True: # round loop
            input_ = IOManager.take_number(**self.__dict__)
            input_ = input_.strip()

            if not input_:
                IOManager.empty_input_message()
                continue

            # detect special input
            if len(input_) > 1:
                if re.match(input_, '%quit', flags=re.I):
                    IOManager.ending_round(**self.__dict__)
                    return 'quit'
                if re.match(input_, '%restart', flags=re.I):
                    IOManager.ending_round(**self.__dict__)
                    return 'restart'
            if re.match('%', input_, flags=re.I):
                IOManager.special_input_hint_message()
                continue

            if not self.is_syntax_corect(input_):
                continue

            bullscows = self.comput_bullscows(input_)
            if bullscows['bulls'] == self.number_size:
                IOManager.game_score_message(**self.__dict__)
                IOManager.ending_round(**self.__dict__)
                return 'end'

            IOManager.bulls_and_cows_message(bullscows, **self.__dict__)

            self.steps += 1


    def play(self):
        """Starts game.

        Handle multi-round game, setting difficulty, drawing number.
        """
        if self.difficulty is None:
            self.set_difficulty()

        while True: # game loop
            self.draw_number()
            print(self.number) # TESTING PRINT
            self.steps = 1
            return_ = self.round()
            if return_ == 'end':
                if IOManager.ask_if_continue_playing(**self.__dict__):
                    continue
                else:
                    return
            elif return_ == 'restart':
                pass
            else:
                return


if __name__ == '__main__':
    # Run game
    Game().play()
