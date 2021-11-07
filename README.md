BacPy
=====

Implementation of Bulls and Cows in Python3 - Creating just for learn git, English and programing :smile:

Game rules
----------

* You have to guess number of witch digits do not repeat.
* Enter your guess and program will return numbers of
  bulls (amount of digits that are correct and have
  correct position) and cows (amount of correct digits
  but with wrong position).
* Try to find correct number with fewest amount of
  attempts.

Read more about Bulls and Cows [here](https://en.wikipedia.org/wiki/Bulls_and_Cows).


Features
--------

* __3 types of number parameters__
	- easy: 3-size number, 1-6 digits range
	- normal: 4-size number, 1-9 digits range
	- hard: 5-size number, 1-9,A-F digits range

* __Saving best scores into ranking__ 
	
	For now it uses `.rankings` directory placed in current working directory.
	
* __Special commands__ 

	Type `!help` to get basic information or `!help commands` to get information about available commands.


Dependencies
------------
* Python 3.8+
* prompt\_toolkit
* tabulate
