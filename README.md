BacPy v0.3
==========
Implementation of Bulls and Cows in Python3 - Creating just for learn git, English and programing :smile:

Game rules
----------
> # HELP
>
> BacPy is "Bulls and Cows" game implementation.
>
> Rules are:
>  * You have to guess number of witch digits do not repeat.
>  * Enter your guess and program will return numbers of
>	   bulls (amount of digits that are correct and have
>	   correct position) and cows (amount of correct digits
>	   but with wrong position).
>  * Try to find correct number with fewest amount of
>	   attempts.
>
> Special commands:
>		You can type '!h commands' to show available commands.

Read more [here](https://en.wikipedia.org/wiki/Bulls_and_Cows)

Features
--------
* Terminal interface
* Linux support
* 3 types of difficulty
	- easy: 3-size number, 1-6 digits range
	- normal: 4-size number, 1-9 digits range
	- hard: 5-size number, 1-9,A-F digits range
* Special commands to communicate with game while playing

Dependencies
------------
* Python 3.8+
* prompt\_toolkit
* tabulate
