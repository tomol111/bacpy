"Implementation of 'Bulls and Cows' game"

__version__ = '0.2'
__author__ = 'Tomasz Olszewski'


from cli import GameCLI


if __name__ == '__main__':
    # Run game
    GameCLI().play()
