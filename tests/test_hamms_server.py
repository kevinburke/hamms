try:
    from httplib import BadStatusLine
except ImportError:
    from http.client import BadStatusLine

from nose.tools import assert_equal, assert_raises, assert_is_instance
import requests

from hamms import HammsServer, reactor

hs = HammsServer()

def test_custom_port():
    """ Should be able to specify a custom port to listen on """
    try:
        # XXX port find_unused_port method and use it
        port=14100
        hs.start(beginning_port=port)
        r = requests.get('http://127.0.0.1:{port}'.format(port=port+9))
        assert_equal(r.status_code, 200)

        with assert_raises(requests.exceptions.ConnectionError) as cm:
            r = requests.get('http://127.0.0.1:{port}'.format(port=port+3))
        assert_is_instance(cm.exception.message[1], BadStatusLine)

    finally:
        # We can't stop the reactor in case other test files are going to run.
        # hs.stop()
        pass
