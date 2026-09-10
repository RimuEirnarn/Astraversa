from sys import path
from os.path import realpath

path.insert(0, realpath(__file__+'/../../'))

from astraversa.win.etwhandler import test_etw as main

if __name__ == '__main__':
    main()