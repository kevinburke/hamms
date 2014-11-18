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

BASE_PORT = 5500

class HammsServer(object):
    """ Start the hamms server in a thread.

    Usage::

        hs = HammsServer()
        hs.start()
        # When you are done working with hamms
        hs.stop()
    """

    def start(self):
        self.t = Thread(target=reactor.run, args=(False,))
        self.t.daemon = True
        self.t.start()

    def stop(self):
        reactor.stop()

def _ip(transport):
    try:
        peer = transport.getPeer()
        return peer.host
    except Exception:
        return "<ipaddr>"

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

    PORT = BASE_PORT+1

    def dataReceived(self, data):
        logger.info(_log(_ip(self.transport), self.PORT, data))


class ListenForeverFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return ListenForeverServer()


class EmptyStringTerminateImmediatelyServer(protocol.Protocol):
    PORT = BASE_PORT+2

    def dataReceived(self, data):
        logger.info(_log(_ip(self.transport), self.PORT, data))

    def connectionMade(self):
        self.transport.write('')
        self.transport.loseConnection()


class EmptyStringTerminateImmediatelyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return EmptyStringTerminateImmediatelyServer()


class EmptyStringTerminateOnReceiveServer(protocol.Protocol):

    PORT = BASE_PORT+3

    def dataReceived(self, data):
        logger.info(_log(_ip(self.transport), self.PORT, data))
        self.transport.write('')
        self.transport.loseConnection()


class EmptyStringTerminateOnReceiveFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return EmptyStringTerminateOnReceiveServer()


class MalformedStringTerminateImmediatelyServer(protocol.Protocol):

    PORT = BASE_PORT + 4

    def dataReceived(self, data):
        logger.info(_log(_ip(self.transport), self.PORT, data))

    def connectionMade(self):
        self.transport.write('foo bar')
        self.transport.loseConnection()


class MalformedStringTerminateImmediatelyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return MalformedStringTerminateImmediatelyServer()


class MalformedStringTerminateOnReceiveServer(protocol.Protocol):

    PORT = BASE_PORT+5

    def dataReceived(self, data):
        logger.info(_log(_ip(self.transport), self.PORT, data))
        self.transport.write('foo bar')
        self.transport.loseConnection()


class MalformedStringTerminateOnReceiveFactory(protocol.Factory):

    def buildProtocol(self, addr):
        return MalformedStringTerminateOnReceiveServer()


empty_response = 'HTTP/1.1 204 No Content\r\n\r\n'

# XXX combine these two servers.
class FiveSecondByteResponseServer(protocol.Protocol):

    PORT = BASE_PORT + 6

    def _send_byte(self, byte):
        self.transport.write(byte)

    def dataReceived(self, data):
        try:
            timer = 5
            for byte in empty_response:
                reactor.callLater(timer, self._send_byte, byte)
                timer += 5
            reactor.callLater(timer, self.transport.loseConnection)
            logger.info(_log(_ip(self.transport), self.PORT, data, status=204))
        except Exception:
            logger.info(_log(_ip(self.transport), self.PORT, data))


class FiveSecondByteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return FiveSecondByteResponseServer()


class ThirtySecondByteResponseServer(protocol.Protocol):

    PORT = BASE_PORT + 7

    def _send_byte(self, byte):
        self.transport.write(byte)

    def dataReceived(self, data):
        try:
            timer = 30
            for byte in empty_response:
                reactor.callLater(timer, self._send_byte, byte)
                timer += 30
            reactor.callLater(timer, self.transport.loseConnection)
            logger.info(_log(_ip(self.transport), self.PORT, data, status=204))
        except Exception:
            logger.info(_log(_ip(self.transport), self.PORT, data))


class ThirtySecondByteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return ThirtySecondByteResponseServer()


class SendDataPastContentLengthServer(protocol.Protocol):

    PORT = BASE_PORT + 10

    def dataReceived(self, data):
        logger.info(_log(_ip(self.transport), self.PORT, data, status=200))

    def connectionMade(self):
        self.transport.write('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n'
                             'Content-Length: 3\r\nConnection: keep-alive'
                             '\r\n\r\n' + 'a'*1024*1024)
        self.transport.loseConnection()

class SendDataPastContentLengthFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return SendDataPastContentLengthServer()

def success_response(content_type, response):
    return ('HTTP/1.1 200 OK\r\n'
            'Content-Type: {ctype}\r\n\r\n'
            '{response}'.format(ctype=content_type, response=response))

class DropRandomRequestsServer(protocol.Protocol):

    PORT = BASE_PORT + 13

    def dataReceived(self, data):
        body = data.split('\r\n')
        method, url, http_vsn = body[0].split(' ')
        o = urlparse.urlparse(url)
        query = urlparse.parse_qs(o.query)
        if 'failrate' in query:
            failrate = query['failrate'].pop()
        else:
            failrate = 0.05
        if random.random() >= float(failrate):
            logger.info(_log(_ip(self.transport), self.PORT, data, status=200))
            self.transport.write(
                success_response('application/json', '{"success": true}'))
        else:
            logger.info(_log(_ip(self.transport), self.PORT, data))
        self.transport.loseConnection()

class DropRandomRequestsFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return DropRandomRequestsServer()


sleep_app = Flask(__name__)
sleep_app.PORT = BASE_PORT + 8
status_app = Flask(__name__)
status_app.PORT = BASE_PORT + 9
large_header_app = Flask(__name__)
large_header_app.PORT = BASE_PORT + 11
retries_app = Flask(__name__)
retries_app.PORT = BASE_PORT + 12

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

# we want the retries app to listen on all methods
retries_app.url_map.add(Rule('/', endpoint='index'))
@retries_app.endpoint("index")
def serve_error_based_on_counter():
    global COUNTER
    COUNTER += 1
    if COUNTER % 3 == 0:
        req_headers = get_dict('headers')
        return Response(response=json.dumps(req_headers), status=200,
                        headers={'Content-Type': 'application/json'})
    else:
        retry_times = 3 - COUNTER % 3
        msg = 'The server had an error. Try again {retry_times} more {time_p}'
        time_p = 'time' if retry_times == 1 else 'times'
        content = {
            'error':msg.format(retry_times=retry_times, time_p=time_p),
            'counter': COUNTER,
            'status': 500,
        }
        return Response(response=json.dumps(content), status=500,
                        headers={'Content-Type': 'application/json'})

@retries_app.route("/counter", methods=['POST'])
def reset():
    global COUNTER
    COUNTER = 0
    content = {
        'counter': COUNTER,
        'status': 200
    }
    return Response(response=json.dumps(content), status=200,
                    headers={'Content-Type': 'application/json'})

@retries_app.route("/counter", methods=['GET'])
def counter():
    global COUNTER
    content = {
        'counter': COUNTER,
        'status': 200
    }
    return Response(response=json.dumps(content), status=200,
                    headers={'Content-Type': 'application/json'})

def _log_flask(port, status):
    logger.info(
        _log(request.remote_addr, port, "{method} {url} HTTP/1.1".format(
        method=request.method.upper(), url=request.full_path), status=status))

@sleep_app.after_request
def log_sleep(resp):
    _log_flask(sleep_app.PORT, resp.status_code)
    resp.headers['Server'] = 'hamms'
    return resp

@status_app.after_request
def log_status(resp):
    _log_flask(status_app.PORT, resp.status_code)
    resp.headers['Server'] = 'hamms'
    return resp

@large_header_app.after_request
def log_large_header(resp):
    _log_flask(large_header_app.PORT, resp.status_code)
    resp.headers['Server'] = 'hamms'
    return resp

@retries_app.after_request
def retries_header(resp):
    _log_flask(retries_app.PORT, resp.status_code)
    resp.headers['Server'] = 'hamms'
    return resp

sleep_resource = WSGIResource(reactor, reactor.getThreadPool(), sleep_app)
sleep_site = Site(sleep_resource)

status_resource = WSGIResource(reactor, reactor.getThreadPool(), status_app)
status_site = Site(status_resource)

large_header_resource = WSGIResource(reactor, reactor.getThreadPool(),
                                     large_header_app)
large_header_site = Site(large_header_resource)

retries_resource = WSGIResource(reactor, reactor.getThreadPool(), retries_app)
retries_site = Site(retries_resource)


reactor.listenTCP(ListenForeverServer.PORT, ListenForeverFactory())
reactor.listenTCP(EmptyStringTerminateImmediatelyServer.PORT,
                  EmptyStringTerminateImmediatelyFactory())
reactor.listenTCP(EmptyStringTerminateOnReceiveServer.PORT,
                  EmptyStringTerminateOnReceiveFactory())
reactor.listenTCP(MalformedStringTerminateImmediatelyServer.PORT,
                  MalformedStringTerminateImmediatelyFactory())
reactor.listenTCP(MalformedStringTerminateOnReceiveServer.PORT,
                  MalformedStringTerminateOnReceiveFactory())
reactor.listenTCP(FiveSecondByteResponseServer.PORT,
                  FiveSecondByteResponseFactory())
reactor.listenTCP(ThirtySecondByteResponseServer.PORT,
                  ThirtySecondByteResponseFactory())
reactor.listenTCP(sleep_app.PORT, sleep_site)
reactor.listenTCP(status_app.PORT, status_site)
reactor.listenTCP(SendDataPastContentLengthServer.PORT,
                  SendDataPastContentLengthFactory())
reactor.listenTCP(large_header_app.PORT, large_header_site)
reactor.listenTCP(retries_app.PORT, retries_site)
reactor.listenTCP(DropRandomRequestsServer.PORT, DropRandomRequestsFactory())


def main():
    logging.basicConfig()
    logger.info("Listening...")
    reactor.run()


if __name__ == "__main__":
    main()
