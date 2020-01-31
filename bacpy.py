#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"Terminal implementation of 'Bulls and Cows' game"

__version__ = '0.1'
__author__ = 'Tomasz Olszewski'

import random
import re
from collections import Counter
from consolemenu import SelectionMenu
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
        self.player = None
        self.steps = 1


    def draw_number(self):
        self.number = ''.join(
            random.sample(self.possible_digits, self.number_size)
        )


    def set_difficulty(self):
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
                print('Input is not a digit!')
                continue
            input_ = int(input_)
            if input_ not in options_dict:
                print('Valid key!')
                continue
            break

        # setting difficulty
        self.difficulty = options_dict[input_]
        mode = MODES[self.difficulty]
        self.number_size = mode['number_size']
        self.possible_digits = mode['possible_digits']
        self.digits_range = mode['digits_range']


    def comput_bullscows(self, guess):
        """Return bulls and cows for given string comparing to self"""
        bulls, cows = 0, 0

        for i in range(self.number_size):
            if guess[i] == self.number[i]:
                bulls += 1
            elif guess[j] in self.number:
                cows += 1

        return {'bulls': bulls, 'cows': cows}


    def is_syntax_corect(self, other):
        """Check if given string have correct syntax and can be compared to self"""

        # check if number have wrong characters
        list_ = []
        list_ = [i for i in other if i not in self.possible_digits if i not in list_]
        if list_:    # check if list is not empty
            wrong_chars = ', '.join(map(lambda x: '"'+x+'"', list_))
            return (f'Found wrong characters: {wrong_chars}\n'
                    f'"{self.digits_range}" only available.')

        # check length
        if len(other) != self.number_size:
            return f"Number should have {self.number_size} digits. You entered {len(other)}."

        # check that digits don`t repeat
        counter = Counter(other)
        list_ = [i for i in counter.keys() if counter[i] > 1]
        if list_:    # check if list is not empty
            rep_digs = ', '.join(map(lambda x: '"'+x+'"', list_))
            print(
                "Number can`t have repeated digits. {} repeated."\
                .format(rep_digs),
                end=''
            )
            return False

        # finally number is correct
        return True


    def play(self):
        if self.difficulty == None:
            self.set_difficulty()

        while True: # game loop
            self.draw_number()
            print(
                '====== Game started ======\n'
                '\n'
                '- Difficulty: {difficulty}\n'
                '- Number size: {number_size}\n'
                '- Digits range: {digits_range}\n'
                '\n'
                '<- Enter numbers ->\n'\
                .format(**self.__dict__),
                end=''
            )
            while True: # round loop
                input_ = input("[{}] ".format(self.steps)).strip()

                # detect special input
                if re.match('^%q(u(it?)?)?$', input_, flags=re.I):
                    return
                if re.match('^%r(e(s(t(a(rt?)?)?)?)?)?$', input_, flags=re.I):
                    self.steps = 1
                    break
                if re.match('^%', input_, flags=re.I):
                    print('%q[uit] - quit\n'
                          '%r[estart] - restart')
                    continue

                if not self.is_syntax_corect(input_):
                    continue

                bulscows = self.comput_bullscows(input_)
                if bulscows['bulls'] == self.number_size:
                    print(
                        "You guessed it in {self.steps} steps."\
                        .format(**self.__dict__),
                        end=''
                    )
                    _ = input('')
                    break
                else:
                    print("bulls: {bulls:>2}, cows: {cows:>2}".format(**bulscows))

                self.steps += 1


# Run game
game = Game()
game.play()
