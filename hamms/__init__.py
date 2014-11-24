import json
import logging
from email import message_from_string
import random
from StringIO import StringIO
from threading import Thread
import time
import urlparse

from flask import Flask, request, Response, g
from httpbin.helpers import get_dict, status_code
from twisted.internet import protocol, reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from werkzeug.routing import Rule
from werkzeug.http import parse_accept_header

from .morse import morsedict

logger = logging.getLogger("hamms")
logger.setLevel(logging.INFO)
# XXX: also update version in setup.py
__version__ = '1.3'
SERVER_HEADER = 'Hamms/{version}'.format(version=__version__)

BASE_PORT = 5500

class HammsSite(Site):
    def getResourceFor(self, request):
        request.setHeader('Server', SERVER_HEADER)
        return Site.getResourceFor(self, request)

class HammsServer(object):
    """ Start the hamms server in a thread.

    Usage::

        hs = HammsServer()
        hs.start(beginning_port=5500)
        # When you are done working with hamms
        hs.stop()

    :param int beginning_port: Hamms will start servers on all ports from
        beginning_port to beginning_port + 14.
    """

    def start(self, beginning_port=BASE_PORT):
        self.beginning_port = beginning_port
        self.retry_cache = {}

        listen(reactor, base_port=self.beginning_port, retry_cache=self.retry_cache)

        if not reactor.running:
            self.t = Thread(target=reactor.run, args=(False,))
            self.t.daemon = True
            self.t.start()

    def stop(self):
        reactor.stop()

def listen(_reactor, base_port=BASE_PORT, retry_cache=None):
    # in likelihood there is no benefit to passing in the reactor as only one of
    # them can ever run at a time.
    retry_cache = retry_cache or {}
    retries_app = create_retries_app(retry_cache)

    sleep_resource = WSGIResource(reactor, reactor.getThreadPool(), sleep_app)
    sleep_site = HammsSite(sleep_resource)

    status_resource = WSGIResource(reactor, reactor.getThreadPool(), status_app)
    status_site = HammsSite(status_resource)

    large_header_resource = WSGIResource(reactor, reactor.getThreadPool(),
                                         large_header_app)
    large_header_site = HammsSite(large_header_resource)

    retries_resource = WSGIResource(reactor, reactor.getThreadPool(), retries_app)
    retries_site = HammsSite(retries_resource)

    unparseable_resource = WSGIResource(reactor, reactor.getThreadPool(),
                                        unparseable_app)
    unparseable_site = HammsSite(unparseable_resource)

    toolong_content_resource = WSGIResource(reactor, reactor.getThreadPool(),
                                        toolong_content_app)
    toolong_content_site = HammsSite(toolong_content_resource)

    _reactor.listenTCP(base_port + ListenForeverServer.PORT, ListenForeverFactory())
    _reactor.listenTCP(base_port + EmptyStringTerminateImmediatelyServer.PORT,
                      EmptyStringTerminateImmediatelyFactory())
    _reactor.listenTCP(base_port + EmptyStringTerminateOnReceiveServer.PORT,
                      EmptyStringTerminateOnReceiveFactory())
    _reactor.listenTCP(base_port + MalformedStringTerminateImmediatelyServer.PORT,
                      MalformedStringTerminateImmediatelyFactory())
    _reactor.listenTCP(base_port + MalformedStringTerminateOnReceiveServer.PORT,
                      MalformedStringTerminateOnReceiveFactory())
    _reactor.listenTCP(base_port + FiveSecondByteResponseServer.PORT,
                      FiveSecondByteResponseFactory())
    _reactor.listenTCP(base_port + ThirtySecondByteResponseServer.PORT,
                      ThirtySecondByteResponseFactory())
    _reactor.listenTCP(base_port + sleep_app.PORT, sleep_site)
    _reactor.listenTCP(base_port + status_app.PORT, status_site)
    _reactor.listenTCP(base_port + SendDataPastContentLengthServer.PORT,
                      SendDataPastContentLengthFactory())
    _reactor.listenTCP(base_port + large_header_app.PORT, large_header_site)
    _reactor.listenTCP(base_port + retries_app.PORT, retries_site)
    _reactor.listenTCP(base_port + DropRandomRequestsServer.PORT,
                       DropRandomRequestsFactory())
    _reactor.listenTCP(base_port + unparseable_app.PORT, unparseable_site)
    _reactor.listenTCP(base_port + IncompleteResponseServer.PORT,
                       IncompleteResponseFactory())
    _reactor.listenTCP(base_port + toolong_content_app.PORT, toolong_content_site)


def get_remote_host(transport):
    try:
        peer = transport.getPeer()
        return peer.host
    except Exception:
        return "<ipaddr>"

def get_port(transport):
    try:
        return transport.getHost().port
    except Exception:
        return "<port>"

def get_header(header_name, data):
    try:
        rline, raw_headers = data.split('\r\n', 1)
        headers = message_from_string(raw_headers)
        return headers.get(header_name, "")
    except Exception:
        return ""

def _log_t(transport, data, status=None):
    ipaddr = get_remote_host(transport)
    port = get_port(transport)
    ua = get_header('user-agent', data)
    return _log(ipaddr, port, data, status=status, ua=ua)

def _log(ipaddr, port, data, status=None, ua=""):
    try:
        topline = data.split('\r\n')[0]
        return "{ipaddr} {port} \"{topline}\" {status} \"{ua}\"".format(
            ipaddr=ipaddr, port=port, topline=topline, ua=ua, status=status or "-")
    except Exception:
        logger.exception("caught exception while formatting log")
        return "<data received>"

class ListenForeverServer(protocol.Protocol):

    PORT = 1

    def dataReceived(self, data):
        logger.info(_log_t(self.transport, data))


class ListenForeverFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return ListenForeverServer()


class EmptyStringTerminateImmediatelyServer(protocol.Protocol):
    PORT = 2

    def dataReceived(self, data):
        logger.info(_log_t(self.transport, data))

    def connectionMade(self):
        self.transport.write('')
        self.transport.loseConnection()


class EmptyStringTerminateImmediatelyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return EmptyStringTerminateImmediatelyServer()


class EmptyStringTerminateOnReceiveServer(protocol.Protocol):

    PORT = 3

    def dataReceived(self, data):
        logger.info(_log_t(self.transport, data))
        self.transport.write('')
        self.transport.loseConnection()


class EmptyStringTerminateOnReceiveFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return EmptyStringTerminateOnReceiveServer()


class MalformedStringTerminateImmediatelyServer(protocol.Protocol):

    PORT = 4

    def dataReceived(self, data):
        logger.info(_log_t(self.transport, data))

    def connectionMade(self):
        self.transport.write('foo bar')
        self.transport.loseConnection()


class MalformedStringTerminateImmediatelyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return MalformedStringTerminateImmediatelyServer()


class MalformedStringTerminateOnReceiveServer(protocol.Protocol):

    PORT = 5

    def dataReceived(self, data):
        logger.info(_log_t(self.transport, data))
        self.transport.write('foo bar')
        self.transport.loseConnection()


class MalformedStringTerminateOnReceiveFactory(protocol.Factory):

    def buildProtocol(self, addr):
        return MalformedStringTerminateOnReceiveServer()


empty_response = ('HTTP/1.1 204 No Content\r\n'
                  'Server: {hdr}\r\n\r\n'.format(hdr=SERVER_HEADER))

class FiveSecondByteResponseServer(protocol.Protocol):

    PORT = 6

    def _send_byte(self, byte):
        self.transport.write(byte)

    def dataReceived(self, data):
        try:
            timer = 5
            for byte in empty_response:
                reactor.callLater(timer, self._send_byte, byte)
                timer += 5
            reactor.callLater(timer, self.transport.loseConnection)
            logger.info(_log_t(self.transport, data, status=204))
        except Exception:
            logger.info(_log_t(self.transport, data))


class FiveSecondByteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return FiveSecondByteResponseServer()


class ThirtySecondByteResponseServer(protocol.Protocol):

    PORT = 7

    def _send_byte(self, byte):
        self.transport.write(byte)

    def dataReceived(self, data):
        try:
            timer = 30
            for byte in empty_response:
                reactor.callLater(timer, self._send_byte, byte)
                timer += 30
            reactor.callLater(timer, self.transport.loseConnection)
            logger.info(_log_t(self.transport, data, status=204))
        except Exception:
            logger.info(_log_t(self.transport, data))


class ThirtySecondByteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return ThirtySecondByteResponseServer()


class SendDataPastContentLengthServer(protocol.Protocol):

    PORT = 10

    def dataReceived(self, data):
        logger.info(_log_t(self.transport, data, status=200))

    def connectionMade(self):
        self.transport.write('HTTP/1.1 200 OK\r\n'
                             'Server: {server}\r\n'
                             'Content-Type: text/plain\r\n'
                             'Content-Length: 3\r\n'
                             'Connection: keep-alive\r\n'
                             '\r\n{body}'.format(server=SERVER_HEADER,
                                                 body='a'*1024*1024))
        self.transport.loseConnection()

class SendDataPastContentLengthFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return SendDataPastContentLengthServer()

def success_response(content_type, response):
    return ('HTTP/1.1 200 OK\r\n'
            'Server: {server}\r\n'
            'Content-Type: {ctype}\r\n\r\n'
            '{response}'.format(ctype=content_type, server=SERVER_HEADER,
                                response=response))

class DropRandomRequestsServer(protocol.Protocol):

    PORT = 13

    def dataReceived(self, data):
        body = data.split('\r\n')
        try:
            method, url, http_vsn = body[0].split(' ')
        except Exception:
            # we got weird data, just fail
            logger.info(_log_t(self.transport, data))
            self.transport.loseConnection()

        o = urlparse.urlparse(url)
        query = urlparse.parse_qs(o.query)
        if 'failrate' in query:
            failrate = query['failrate'].pop()
        else:
            failrate = 0.05
        if random.random() >= float(failrate):
            logger.info(_log_t(self.transport, data, status=200))
            self.transport.write(
                success_response('application/json', '{"success": true}'))
        else:
            logger.info(_log_t(self.transport, data))
        self.transport.loseConnection()

class DropRandomRequestsFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return DropRandomRequestsServer()



def write_incomplete_response(transport, content_type, body):
    transport.write('Content-Type: {ctype}\r\n'.format(ctype=content_type))
    transport.write('Content-Length: {length}\r\n'.format(
        length=len(body)+2000))
    transport.write('\r\n{body}'.format(body=body))
    transport.loseConnection()

INCOMPLETE_JSON = '{"message": "the json body is incomplete.", "key": {"nested_message": "blah blah blah'
INCOMPLETE_XML = '<?xml version="1.0" ?><response><status type="http">200 foo'
INCOMPLETE_PLAIN = 'incomplete document respo'
INCOMPLETE_HTML = '<!doctype html><html><head><title>incomplete'

class IncompleteResponseServer(protocol.Protocol):
    PORT = 16
    def dataReceived(self, data):
        accept_header_value = get_header('Accept', data)
        accept_cls = parse_accept_header(accept_header_value)
        self.transport.write('HTTP/1.1 200 OK\r\n')
        if 'text/html' == accept_cls.best:
            write_incomplete_response(self.transport, 'text/html',
                                      INCOMPLETE_HTML)
        elif 'text/plain' == accept_cls.best:
            write_incomplete_response(self.transport, 'text/plain',
                                      INCOMPLETE_PLAIN)
        elif 'text/xml' == accept_cls.best:
            write_incomplete_response(self.transport, 'text/xml',
                                      INCOMPLETE_XML)
        else:
            write_incomplete_response(self.transport, 'application/json',
                                      INCOMPLETE_JSON)


class IncompleteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return IncompleteResponseServer()


sleep_app = Flask(__name__)
sleep_app.PORT = 8
status_app = Flask(__name__)
status_app.PORT = 9
large_header_app = Flask(__name__)
large_header_app.PORT = 11
unparseable_app = Flask(__name__)
unparseable_app.PORT = 14
toolong_content_app = Flask(__name__)
toolong_content_app.PORT = 15

def create_retries_app(cache):
    retries_app = Flask(__name__)
    retries_app.PORT = 12
    retries_app.cache = cache

    # we want the retries app to listen on all methods
    retries_app.url_map.add(Rule('/', endpoint='index'))
    @retries_app.endpoint("index")
    def check_retries():
        json_hdr = {'Content-Type': 'application/json'}
        key = request.args.get('key', 'default')
        tries = request.args.get('tries', 3)
        try:
            tries = int(tries)
        except Exception:
            return Response(status=400, headers=json_hdr, response=json.dumps({
                'error': 'Please pass an integer number of tries',
                'key': key,
                'success': False,
            }))

        if key in retries_app.cache:
            retries_app.cache[key] -= 1
        else:
            retries_app.cache[key] = int(tries) - 1

        if retries_app.cache[key] <= 0:
            data = {
                'key': key,
                'tries_remaining': retries_app.cache[key],
                'success': True
            }
            return Response(response=json.dumps(data), status=200,
                            headers=json_hdr)
        else:
            msg = 'The server had an error. Try again {retry_times} more {time_p}'
            time_p = 'time' if retries_app.cache[key] == 1 else 'times'
            content = {
                'error': msg.format(retry_times=retries_app.cache[key], time_p=time_p),
                'tries_remaining': retries_app.cache[key],
                'key': key,
                'success': False,
            }
            return Response(response=json.dumps(content), status=500,
                            headers=json_hdr)

    @retries_app.route("/counters", methods=['POST'])
    def reset():
        key = request.values.get('key', 'default')
        tries = request.values.get('tries', 3)
        try:
            tries = int(tries)
        except Exception:
            return Response(status=400, headers=json_hdr, response=json.dumps({
                'error': 'Please pass an integer number of tries',
                'key': key,
                'success': False,
            }))

        retries_app.cache[key] = tries

        content = {
            'key': key,
            'tries_remaining': tries,
            'success': True,
        }
        return Response(response=json.dumps(content), status=200,
                        headers={'Content-Type': 'application/json'})

    @retries_app.route("/counters", methods=['GET'])
    def counter():
        content = {'counters': retries_app.cache, 'success': True}
        return Response(response=json.dumps(content), status=200,
                        headers={'Content-Type': 'application/json'})

    @retries_app.after_request
    def retries_header(resp):
        _log_flask(resp.status_code)
        resp.headers['Server'] = 'hamms'
        return resp

    return retries_app

@sleep_app.route("/")
def sleep():
    n = request.values.get('sleep', 5)
    time.sleep(float(n))
    hdrs = get_dict('headers')
    return Response(response=json.dumps(hdrs), status=200,
                    headers={'Content-Type': 'application/json'})

@status_app.route("/")
def status():
    n = request.values.get('status', 200)
    return status_code(int(n))

@large_header_app.route("/")
def large_header():
    n = request.values.get('size', 63*1024)
    req_headers = get_dict('headers')
    resp_headers = {
        'Content-Type': 'application/json',
        'Cookie': 'a'*int(n)
    }
    return Response(response=json.dumps(req_headers), status=200,
                    headers=resp_headers)

@unparseable_app.route("/")
def unparseable():

    def _morse():
        hdr = {'Content-Type': 'text/morse'}
        message = " STOP ".join([
            "DEAREST ANN",
            "TIMES ARE HARD",
            "MY TREADMILL DESK DOESNT RECLINE ALL THE WAY",
            "THE KITCHEN HASNT HAD SOYLENT FOR TWO WHOLE DAYS",
            "HOW IS ANYONE SUPPOSED TO PROGRAM IN THESE CONDITIONS",
            "PLEASE SEND HELP",
        ]) + " STOP"
        morse_message = StringIO()
        for i, letter in enumerate(message):
            morse_message.write(morsedict[letter])
        return Response(response=morse_message.getvalue(), headers=hdr)

    if 'text/morse' not in request.accept_mimetypes:
        return _morse()

    elif not request.accept_mimetypes.accept_json:
        hdr = {'Content-Type': 'application/json'}
        resp = {
            'status': 200,
            'message': 'This is a JSON response. You did not ask for JSON data.',
        }
        return Response(response=json.dumps(resp), headers=hdr)

    elif not request.accept_mimetypes.accept_html:
        hdr = {'Content-Type': 'text/html'}
        return Response(response="<!doctype html><html><head><title>Your API is Broken</title></head><body>This should be JSON.</body></html>", headers=hdr)

    elif 'text/csv' not in request.accept_mimetypes:
        hdr = {'Content-Type': 'text/csv'}
        return Response(response="message,status\nThis is a CSV response that your code almost certainly can't parse", headers=hdr)

    else:
        # */* or similar, return morse.
        return _morse()

@toolong_content_app.route("/")
def toolong():
    r = Response()
    r.automatically_set_content_length = False
    r.headers['Content-Length'] = 2300
    if (request.accept_mimetypes.best == 'application/json' or
        request.accept_mimetypes.best == '*/*'):
        r.headers['Content-Type'] = 'application/json'
        r.set_data(INCOMPLETE_JSON)
    elif request.accept_mimetypes.best == 'text/html':
        r.headers['Content-Type'] = 'text/html'
        r.set_data(INCOMPLETE_HTML)
    elif request.accept_mimetypes.best == 'text/plain':
        r.headers['Content-Type'] = 'text/plain'
        r.set_data(INCOMPLETE_PLAIN)
    elif (request.accept_mimetypes.best == 'text/xml' or
          request.accept_mimetypes.best == 'application/xml'):
        r.headers['Content-Type'] = 'text/xml'
        r.set_data(INCOMPLETE_XML)
    else:
        r.headers['Content-Type'] = 'application/json'
        r.set_data(INCOMPLETE_JSON)
    return r

def _get_port_from_url(url):
    urlo = urlparse.urlparse(url)
    try:
        host, port = urlo.netloc.split(':')
        return port
    except Exception:
        return "<port>"

def _log_flask(status):
    port = _get_port_from_url(request.url)
    url_line = "{method} {url} HTTP/1.0".format(
        method=request.method.upper(), url=request.full_path)
    ua = request.headers.get('user-agent', '')
    logger.info(_log(request.remote_addr, port, url_line, status, ua=ua))

@sleep_app.after_request
def log_sleep(resp):
    _log_flask(resp.status_code)
    return resp

@status_app.after_request
def log_status(resp):
    _log_flask(resp.status_code)
    return resp

@large_header_app.after_request
def log_large_header(resp):
    _log_flask(resp.status_code)
    return resp

def main(port=BASE_PORT):
    logging.basicConfig()
    logger.info("Listening...")
    listen(reactor, port)
    reactor.run()


if __name__ == "__main__":
    main()
