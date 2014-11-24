from nose.tools import assert_equal

from hamms import get_header

req = "\r\n".join(["GET / HTTP/1.0",
                   "User-Agent: my-user-agent",
                   "Accept: */*", "\r\n"])

noreq = "\r\n".join(["GET / HTTP/1.0",
                     "Accept: */*", "\r\n"])

def test_user_agent():
    assert_equal("my-user-agent", get_header("user-agent", req))
    assert_equal("", get_header("user-agent", noreq))
