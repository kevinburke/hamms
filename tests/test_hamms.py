import errno
try:
    from httplib import BadStatusLine, LineTooLong
except ImportError:
    from http.client import BadStatusLine, LineTooLong

import requests
from nose.tools import assert_raises, assert_equal, assert_is_instance

from hamms import HammsServer, BASE_PORT

hs = HammsServer()

def setup():
    hs.start()

def test_5500():
    with assert_raises(requests.ConnectionError) as cm:
        requests.get('http://127.0.0.1:{port}'.format(port=BASE_PORT))
    assert_equal(cm.exception.message[1].errno, errno.ECONNREFUSED)

def test_5501():
    with assert_raises(requests.exceptions.ReadTimeout) as cm:
        url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+1)
        requests.get(url, timeout=0.001)

def test_5502():
    with assert_raises(requests.exceptions.ConnectionError) as cm:
        url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+2)
        requests.get(url)
    assert_is_instance(cm.exception.message[1], BadStatusLine)

def test_5503():
    with assert_raises(requests.exceptions.ConnectionError) as cm:
        url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+3)
        requests.get(url)
    assert_is_instance(cm.exception.message[1], BadStatusLine)

def test_5504():
    url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+4)
    r = requests.get(url)
    assert_equal(r.status_code, 200)
    assert_equal(r.content, "foo bar")
    # XXX: any requests > 2.4.3 will raise BadStatusLine here.
    # with assert_raises(requests.exceptions.ConnectionError) as cm:
    # assert_is_instance(cm.exception.message[1], BadStatusLine)

def test_5505():
    url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+4)
    r = requests.get(url)
    assert_equal(r.status_code, 200)
    assert_equal(r.content, "foo bar")
    # XXX: any requests > 2.4.3 will raise BadStatusLine here.
    # with assert_raises(requests.exceptions.ConnectionError) as cm:
    # assert_is_instance(cm.exception.message[1], BadStatusLine)

def test_5506():
    with assert_raises(requests.exceptions.ReadTimeout) as cm:
        # Would need to wait 5 seconds to assert anything about this.
        url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+6)
        requests.get(url, timeout=0.001)

def test_5507():
    # Would need to wait a few minutes to assert anything useful about this.
    # I'm sure Twisted has methods for advancing time, will have to read about
    # them later.
    with assert_raises(requests.exceptions.ReadTimeout) as cm:
        url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+7)
        requests.get(url, timeout=0.001)

def test_5508():
    with assert_raises(requests.exceptions.ReadTimeout) as cm:
        url = 'http://127.0.0.1:{port}?sleep=0.002'.format(port=BASE_PORT+8)
        requests.get(url, timeout=0.001)

    url = 'http://127.0.0.1:{port}?sleep=0.001'.format(port=BASE_PORT+8)
    r = requests.get(url, timeout=0.01)
    assert_equal(r.status_code, 200)

def test_5509():
    url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+9)
    r = requests.get(url)
    assert_equal(r.status_code, 200)

    url = 'http://127.0.0.1:{port}?status=418'.format(port=BASE_PORT+9)
    r = requests.get(url)
    assert_equal(r.status_code, 418)

    url = 'http://127.0.0.1:{port}?status=503'.format(port=BASE_PORT+9)
    r = requests.get(url)
    assert_equal(r.status_code, 503)

def test_5510():
    # Would need to wait 5 seconds to assert anything about this.
    url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+10)
    s = requests.Session()
    a = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1)
    s.mount('http://', a)
    r = s.get(url)
    assert_equal(r.content, 'aaa')
    assert_equal(r.headers['Content-Length'], '3')

    r = s.get(url)
    assert_equal(r.content, 'aaa')
    assert_equal(r.headers['Content-Length'], '3')

def test_5511():
    # Would need to wait 5 seconds to assert anything about this.
    with assert_raises(requests.ConnectionError) as cm:
        url = 'http://127.0.0.1:{port}?size={size}'.format(port=BASE_PORT+11,
                                                           size=1024*64)
        r = requests.get(url)
    assert_is_instance(cm.exception.message[1], LineTooLong)

    url = 'http://127.0.0.1:{port}'.format(port=BASE_PORT+11)
    r = requests.get(url)
    assert_equal(len(r.headers['Cookie']), 1024*63)

def test_5512():
    url = 'http://127.0.0.1:{port}?key=hamms-test'.format(port=BASE_PORT+12)
    r = requests.get(url)
    assert_equal(r.status_code, 500)
    d = r.json()
    assert_equal(d['counter'], 1)

    r = requests.get(url)
    assert_equal(r.status_code, 500)
    d = r.json()
    assert_equal(d['counter'], 2)

    otherkey_url = 'http://127.0.0.1:{port}?key=other-key'.format(port=BASE_PORT+12)
    r = requests.get(otherkey_url)
    assert_equal(r.status_code, 500)
    d = r.json()
    assert_equal(d['counter'], 1)

    url = 'http://127.0.0.1:{port}?key=hamms-test'.format(port=BASE_PORT+12)
    r = requests.get(url)
    assert_equal(r.status_code, 200)

def test_5513():
    with assert_raises(requests.exceptions.ConnectionError) as cm:
        url = 'http://127.0.0.1:{port}?failrate=1'.format(port=BASE_PORT+13)
        r = requests.get(url)
    assert_is_instance(cm.exception.message[1], BadStatusLine)

    success_url = 'http://127.0.0.1:{port}?failrate=0'.format(port=BASE_PORT+13)
    r = requests.get(success_url)

def teardown():
    hs.stop()
