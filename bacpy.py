#!/usr/bin/env python3

# -*- coding: utf-8 -*-

"Terminal implementation of 'Bulls and Cows' game"

import random

__version__ = '0.1.0'
__author__ = 'Tomasz Olszewski'

class Number:

    mode = {
        'easy': {
            'digits': '123456',
            'digits_range': '1-6',
            'size': 3
        },
        'normal': {
            'digits': '123456789',
            'digits_range': '1-9',
            'size': 4
        },
        'hard': {
            'digits': '123456789ABCDEF',
            'digits_range': '1-9,A-F',
            'size': 5
        }
    }

    def __init__(self, difficulty):
        self.difficulty = difficulty
        self.size = self.mode[difficulty]['size']
        self.digits= self.mode[difficulty]['digits']
        self.digits_range = self.mode[difficulty]['digits_range']
        self.number = ''.join(
            random.sample(self.digits, self.size)
        )

    def __repr__(self):
        return self.number

# Testing Number class
#for dificulty in Number.mode:
#    num = Number(dificulty)
#    print(f'{dificulty}: {num}')
