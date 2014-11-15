"""
Example of how to run the Hamms Server from running Python code instead of the
command line.
"""
from threading import Thread
import time

from twisted.internet import task

from hamms import reactor, HammsServer


if __name__ == "__main__":
    hs = HammsServer()
    hs.start()
    time.sleep(5)
    print "stopping"
    hs.stop()
