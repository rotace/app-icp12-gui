PYTHON=/home/yasu/anaconda3/bin/python

all:

run:all
	sudo ${PYTHON} main.py

clean:
	rm -rf *.pyc *.ini
