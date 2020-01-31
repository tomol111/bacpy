"Terminal implementation of 'Bulls and Cows' game"

__version__ = '0.1'
__author__ = 'Tomasz Olszewski'


import random
import re
from collections import Counter
from terminaltables import SingleTable
import numpy as pd


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
        'possible_digits': '123456789AaBbCcDdEeFf',
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
        self.number = ''.join(
            random.sample(self.possible_digits, self.number_size)
        )


    def set_difficulty(self, difficulty=None):
        """Setting game difficulty

        ask user if not given directly
        """
        # ask for difficulty if not given directly
        if difficulty == None:
            # creating options table
            options_dict = dict(zip(range(1,len(MODES)+1), MODES))
            table_data = [['key', 'difficulty', 'size', 'digits']]
            for key, difficulty in options_dict.items():
                table_data.append([
                   str(key),
                    difficulty,
                    MODES[difficulty]['number_size'],
                    MODES[difficulty]['digits_range']
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
        """Return bulls and cows for given string comparing to self"""
        bulls, cows = 0, 0

        for i in range(self.number_size):
            if guess[i] == self.number[i]:
                bulls += 1
            elif guess[i] in self.number:
                cows += 1

        return {'bulls': bulls, 'cows': cows}


    def is_syntax_corect(self, other):
        """Check if given string have correct syntax and can be compared to self"""

        # check if number have wrong characters
        list_ = []
        for i in other:
            if i not in self.possible_digits and i not in list_:
                list_.append(i)
        if list_:    # check if list is not empty
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
                "Number should have {number_size} digits."\
                "You entered {len_}\n."\
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
        """Handle inserting answers and taking special commands

        '%quit'
        '%restart'
        """
        while True: # round loop
            input_ = input("[{steps}] ".format(**self.__dict__))
            input_ = input_.strip()

            # detect special input
            if re.match('^%q(u(it?)?)?$', input_, flags=re.I):
                return 'quit'
            if re.match('^%r(e(s(t(a(rt?)?)?)?)?)?$', input_, flags=re.I):
                return 'restart'
            if re.match('^%', input_, flags=re.I):
                print(
                    '%q[uit]    - quit\n'
                    '%r[estart] - restart\n',
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
        if self.difficulty == None:
            self.set_difficulty()

        while True: # game loop
            self.draw_number()
            self.steps = 1
            print(
                '\n'
                '====== Game started =====\n'
                '\n'
                '  Difficulty:  {difficulty:>7}\n'
                '  Number size: {number_size:>7}\n'
                '  Digits range:{digits_range:>7}\n'
                '\n'
                ' v--- Enter numbers ---v\n'\
                    .format(**self.__dict__),
                end=''
            )
            return_ = self.round()
            if return_ == 'end':
                while True:
                    input_ = input('Do you want to continue? [y/n]: ')
                    input_ = input_.strip()
                    if re.match('^y(es?)?$', input_, flags=re.I):
                        break
                    elif re.match('^no?$', input_, flags=re.I):
                        return
                    else:
                        print('Valid key!\n'.format(input_=input_), end='')
            elif return_ == 'restart':
                pass
            else:
                return

# Run game
game = Game()
game.play()
