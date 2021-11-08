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
	

Installation
-----------

This project is not published on PyPI. To install BacPy you need to use GitHub repository. Using pip it can be done with one command:
```
pip install git+https://github.com/tomol111/bacpy@master
```
It will install version from master branch. For more information about installing package directly from github see [PIP Documentation: VCS Support](https://pip.pypa.io/en/stable/topics/vcs-support/)


Dependencies
------------
* Python 3.8+
* prompt\_toolkit
* tabulate


Gallery
------

<img src="https://user-images.githubusercontent.com/47284321/140725476-ea4b9968-be4e-4fdb-84da-a8cd07118e48.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725478-19ec4769-912b-4335-bf6a-949b4754c169.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725483-2f2a4d04-6303-4311-9fc4-3fe67e6c4421.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725486-a208fe32-0a01-434a-9823-5b71e290cad9.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725488-5ebaec09-1145-4b4f-8d10-6cfc7590d3bc.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725490-58608f3c-4b5b-40f8-861e-b4bb4fd3e4df.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725493-4184ccc2-eddc-42e5-a647-793ac7e0c842.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725494-eb89990e-f043-4433-af83-f4673bc93df7.png" width="45%"></img>
<img src="https://user-images.githubusercontent.com/47284321/140725498-5ba2b891-cf4e-4212-b3da-6a9c4684be8a.png" width="45%"></img> 
