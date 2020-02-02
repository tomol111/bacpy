"Terminal implementation of 'Bulls and Cows' game"

__version__ = '0.1'
__author__ = 'Tomasz Olszewski'


import random
import re
from collections import Counter
from terminaltables import SingleTable


MODES = {
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
            # creating options table
            options_dict = dict(zip(range(1, len(MODES)+1), MODES))
            table_data = [['key', 'difficulty', 'size', 'digits']]
            for key, dif in options_dict.items():
                table_data.append([
                    str(key),
                    difficulty,
                    MODES[dif]['number_size'],
                    MODES[dif]['digits_range']
                ])
            selection_table = SingleTable(table_data)
            selection_table.title = 'Difficulty selection'
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

            difficulty = options_dict[input_]

        # setting difficulty
        self.difficulty = difficulty
        mode = MODES[difficulty]
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
        list_ = []
        for i in other:
            if i not in self.possible_digits and i not in list_:
                list_.append(i)
        if list_:
            wrong_chars = ', '.join(map(lambda x: "'"+x+"'", list_))
            print(
                'Found wrong characters: {wrong_chars}\n'
                '"{digits_range}" only available.\n'\
                    .format(wrong_chars=wrong_chars, **self.__dict__),
                end='',
            )
            return False

        # check length
        if len(other) != self.number_size:
            print(
                "Number should have {number_size} digits. "\
                "You entered {len_}.\n"\
                    .format(len_=len(other), **self.__dict__),
                end='',
            )
            return False

        # check that digits don`t repeat
        counter = Counter(other)
        list_ = [i for i in counter.keys() if counter[i] > 1]
        if list_:
            rep_digs = ', '.join(map(lambda x: "'"+x+"'", list_))
            print(
                "Number can`t have repeated digits. {} repeated."\
                    .format(rep_digs),
                end='',
            )
            return False

        # finally number is correct
        return True

    def round(self):
        """Handle inserting answers and taking special commands.

        RETURN:
            'quit' - if player inserted '%quit'
            'restart' - if player inserted '%restart'
            'end' - if game ended successfully
        """
        while True: # round loop
            input_ = input("[{steps}] ".format(**self.__dict__))
            input_ = input_.strip()

            # detect special input
            if re.match(input_, '%quit', flags=re.I):
                return 'quit'
            if re.match(input_, '%restart', flags=re.I):
                return 'restart'
            if re.match('%', input_, flags=re.I):
                print(
                    '%q[uit]    - quit game\n'
                    '%r[estart] - restart game\n',
                    end='',
                )
                continue

            if not self.is_syntax_corect(input_):
                continue

            bulscows = self.comput_bullscows(input_)
            if bulscows['bulls'] == self.number_size:
                print(
                    "You guessed it in {steps} steps.\n\n"\
                        .format(**self.__dict__),
                    end='',
                )
                return 'end'

            print(
                "bulls: {bulls:>2}, cows: {cows:>2}\n"\
                    .format(**bulscows, **self.__dict__),
                end='',
            )

            self.steps += 1


    def play(self):
        """Start playing game

        Handle multi-round game, setting difficulty, drawing number,
        printing start-game and end-game message.
        """
        if self.difficulty is None:
            self.set_difficulty()

        while True: # game loop
            self.draw_number()
            print(self.number) # TESTING PRINT
            self.steps = 1
            print(
                '\n'
                '====== Game started =====\n'
                '\n'
                '  Difficulty:  {difficulty:>8}\n'
                '  Number size: {number_size:>8}\n'
                '  Digits range:{digits_range:>8}\n'
                '\n'
                ' v--- Enter numbers ---v\n'\
                    .format(**self.__dict__),
                end=''
            )
            return_ = self.round()
            if return_ == 'end':
                print(
                    '======= Game ended ======\n'\
                        .format(**self.__dict__),
                    end='',
                )
                while True:
                    input_ = input(
                        'Do you want to continue? [y/n]: '\
                            .format(**self.__dict__)
                    )
                    input_ = input_.strip()
                    if re.match(input_, 'yes', flags=re.I):
                        break
                    elif re.match(input_, 'no', flags=re.I):
                        return
                    else:
                        print(
                            'Valid key!\n'.format(input_=input_),
                            end='',
                        )
            elif return_ == 'restart':
                pass
            else:
                return


if __name__ == '__main__':
    # Run game
    Game().play()
