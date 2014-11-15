import json
import logging
from threading import Thread
import time

from flask import Flask, request, Response
from httpbin.helpers import get_dict, status_code
from twisted.internet import protocol, reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

logging.basicConfig()
logger = logging.getLogger("hamms")

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
                             'Content-Length: 3\r\n\r\n' + 'a'*100)
        self.transport.loseConnection()

class SendDataPastContentLengthFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return SendDataPastContentLengthServer()


BASE_PORT = 5500

reactor.listenTCP(BASE_PORT+1, ListenForeverFactory())
reactor.listenTCP(BASE_PORT+2, EmptyStringTerminateImmediatelyFactory())
reactor.listenTCP(BASE_PORT+3, EmptyStringTerminateOnReceiveFactory())
reactor.listenTCP(BASE_PORT+4, MalformedStringTerminateImmediatelyFactory())
reactor.listenTCP(BASE_PORT+5, MalformedStringTerminateOnReceiveFactory())
reactor.listenTCP(BASE_PORT+6, FiveSecondByteResponseFactory())
reactor.listenTCP(BASE_PORT+7, ThirtySecondByteResponseFactory())
reactor.listenTCP(BASE_PORT+10, SendDataPastContentLengthFactory())

sleep_app = Flask(__name__)
status_app = Flask(__name__)

@sleep_app.route("/")
def sleep():
    n = request.values.get('sleep')
    time.sleep(float(n))
    hdrs = get_dict('headers')
    return Response(response=json.dumps(hdrs), status=200,
                    headers={'Content-Type': 'application/json'})

@status_app.route("/")
def status():
    n = request.values.get('status')
    return status_code(int(n))

sleep_resource = WSGIResource(reactor, reactor.getThreadPool(), sleep_app)
sleep_site = Site(sleep_resource)
reactor.listenTCP(BASE_PORT+8, sleep_site)

status_resource = WSGIResource(reactor, reactor.getThreadPool(), status_app)
status_site = Site(status_resource)
reactor.listenTCP(BASE_PORT+9, status_site)

logger.info("Listening...")
if __name__ == "__main__":
    reactor.run()
