import json
import logging
import random
from threading import Thread
import time
import urlparse

from flask import Flask, request, Response, g
from httpbin.helpers import get_dict, status_code
from twisted.internet import protocol, reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource
from werkzeug.routing import Rule


logger = logging.getLogger("hamms")
logger.setLevel(logging.INFO)
__version__ = '1.0'
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

    reactor.listenTCP(base_port + ListenForeverServer.PORT, ListenForeverFactory())
    reactor.listenTCP(base_port + EmptyStringTerminateImmediatelyServer.PORT,
                      EmptyStringTerminateImmediatelyFactory())
    reactor.listenTCP(base_port + EmptyStringTerminateOnReceiveServer.PORT,
                      EmptyStringTerminateOnReceiveFactory())
    reactor.listenTCP(base_port + MalformedStringTerminateImmediatelyServer.PORT,
                      MalformedStringTerminateImmediatelyFactory())
    reactor.listenTCP(base_port + MalformedStringTerminateOnReceiveServer.PORT,
                      MalformedStringTerminateOnReceiveFactory())
    reactor.listenTCP(base_port + FiveSecondByteResponseServer.PORT,
                      FiveSecondByteResponseFactory())
    reactor.listenTCP(base_port + ThirtySecondByteResponseServer.PORT,
                      ThirtySecondByteResponseFactory())
    reactor.listenTCP(base_port + sleep_app.PORT, sleep_site)
    reactor.listenTCP(base_port + status_app.PORT, status_site)
    reactor.listenTCP(base_port + SendDataPastContentLengthServer.PORT,
                      SendDataPastContentLengthFactory())
    reactor.listenTCP(base_port + large_header_app.PORT, large_header_site)
    reactor.listenTCP(base_port + retries_app.PORT, retries_site)
    reactor.listenTCP(base_port + DropRandomRequestsServer.PORT, DropRandomRequestsFactory())


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

def _log_t(transport, data, status=None):
    ipaddr = get_remote_host(transport)
    port = get_port(transport)
    return _log(ipaddr, port, data, status)

def _log(ipaddr, port, data, status=None):
    try:
        # XXX find user agent
        topline = data.split('\r\n')[0]
        return "{ipaddr} {port} \"{topline}\" {status}".format(
            ipaddr=ipaddr, port=port, topline=topline, status=status or "-")
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


sleep_app = Flask(__name__)
sleep_app.PORT = 8
status_app = Flask(__name__)
status_app.PORT = 9
large_header_app = Flask(__name__)
large_header_app.PORT = 11

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


COUNTER = 0

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
    logger.info(_log(request.remote_addr, port, url_line, status))

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
