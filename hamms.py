import json
import logging
import random
from threading import Thread
import time
import urlparse

from flask import Flask, request, Response
from httpbin.helpers import get_dict, status_code
from twisted.internet import protocol, reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

logging.basicConfig()
logger = logging.getLogger("hamms")
logger.setLevel(logging.INFO)

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

class ListenForeverServer(protocol.Protocol):
    pass


class ListenForeverFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return ListenForeverServer()


class EmptyStringTerminateImmediatelyServer(protocol.Protocol):
    def connectionMade(self):
        self.transport.write('')
        self.transport.loseConnection()


class EmptyStringTerminateImmediatelyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return EmptyStringTerminateImmediatelyServer()


class EmptyStringTerminateOnReceiveServer(protocol.Protocol):
    def dataReceived(self, data):
        self.transport.write('')
        self.transport.loseConnection()


class EmptyStringTerminateOnReceiveFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return EmptyStringTerminateOnReceiveServer()


class MalformedStringTerminateImmediatelyServer(protocol.Protocol):
    def connectionMade(self):
        self.transport.write('foo bar')
        self.transport.loseConnection()


class MalformedStringTerminateImmediatelyFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return MalformedStringTerminateImmediatelyServer()


class MalformedStringTerminateOnReceiveServer(protocol.Protocol):
    def dataReceived(self, data):
        self.transport.write('foo bar')
        self.transport.loseConnection()


class MalformedStringTerminateOnReceiveFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return MalformedStringTerminateOnReceiveServer()


empty_response = 'HTTP/1.1 204 No Content\r\n\r\n'

# XXX combine these two servers.
class FiveSecondByteResponseServer(protocol.Protocol):

    def _send_byte(self, byte):
        self.transport.write(byte)

    def dataReceived(self, data):
        timer = 5
        for byte in empty_response:
            reactor.callLater(timer, self._send_byte, byte)
            timer += 5
        reactor.callLater(timer, self.transport.loseConnection)


class FiveSecondByteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return FiveSecondByteResponseServer()


class ThirtySecondByteResponseServer(protocol.Protocol):

    def _send_byte(self, byte):
        self.transport.write(byte)

    def dataReceived(self, data):
        timer = 30
        for byte in empty_response:
            reactor.callLater(timer, self._send_byte, byte)
            timer += 30
        reactor.callLater(timer, self.transport.loseConnection)


class ThirtySecondByteResponseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return ThirtySecondByteResponseServer()


class SendDataPastContentLengthServer(protocol.Protocol):
    def connectionMade(self):
        self.transport.write('HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n'
                             'Content-Length: 3\r\n\r\n' + 'a'*1024*1024)
        self.transport.loseConnection()

class SendDataPastContentLengthFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return SendDataPastContentLengthServer()

def success_response(content_type, response):
    return ('HTTP/1.1 200 OK\r\n'
            'Content-Type: {ctype}\r\n\r\n'
            '{response}'.format(ctype=content_type, response=response))

class DropRandomRequestsServer(protocol.Protocol):
    def dataReceived(self, data):
        body = data.split('\r\n')
        method, url, http_vsn = body[0].split(' ')
        o = urlparse.urlparse(url)
        query = urlparse.parse_qs(o.query)
        if 'failrate' in query:
            failrate = query['failrate'].pop()
        else:
            failrate = 0.05
        if random.random() >= failrate:
            self.transport.write(
                success_response('application/json', '{"success": true}'))
        self.transport.loseConnection()

class DropRandomRequestsFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return DropRandomRequestsServer()


sleep_app = Flask(__name__)
status_app = Flask(__name__)
large_header_app = Flask(__name__)

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

sleep_resource = WSGIResource(reactor, reactor.getThreadPool(), sleep_app)
sleep_site = Site(sleep_resource)

status_resource = WSGIResource(reactor, reactor.getThreadPool(), status_app)
status_site = Site(status_resource)

large_header_resource = WSGIResource(reactor, reactor.getThreadPool(),
                                     large_header_app)
large_header_site = Site(large_header_resource)

BASE_PORT = 5500

reactor.listenTCP(BASE_PORT+1, ListenForeverFactory())
reactor.listenTCP(BASE_PORT+2, EmptyStringTerminateImmediatelyFactory())
reactor.listenTCP(BASE_PORT+3, EmptyStringTerminateOnReceiveFactory())
reactor.listenTCP(BASE_PORT+4, MalformedStringTerminateImmediatelyFactory())
reactor.listenTCP(BASE_PORT+5, MalformedStringTerminateOnReceiveFactory())
reactor.listenTCP(BASE_PORT+6, FiveSecondByteResponseFactory())
reactor.listenTCP(BASE_PORT+7, ThirtySecondByteResponseFactory())
reactor.listenTCP(BASE_PORT+8, sleep_site)
reactor.listenTCP(BASE_PORT+9, status_site)
reactor.listenTCP(BASE_PORT+10, SendDataPastContentLengthFactory())
reactor.listenTCP(BASE_PORT+11, large_header_site)
reactor.listenTCP(BASE_PORT+12, SendDataPastContentLengthFactory())
reactor.listenTCP(BASE_PORT+13, DropRandomRequestsFactory())

logger.info("Listening...")
if __name__ == "__main__":
    reactor.run()
