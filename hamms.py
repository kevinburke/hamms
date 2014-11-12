import json
import logging
import time

from flask import Flask, request, Response
from httpbin.helpers import get_dict
from twisted.internet import protocol, reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

logging.basicConfig()
logger = logging.getLogger("hamms")


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


reactor.listenTCP(5501, ListenForeverFactory())
reactor.listenTCP(5502, EmptyStringTerminateImmediatelyFactory())
reactor.listenTCP(5503, EmptyStringTerminateOnReceiveFactory())
reactor.listenTCP(5504, MalformedStringTerminateImmediatelyFactory())
reactor.listenTCP(5505, MalformedStringTerminateOnReceiveFactory())
reactor.listenTCP(5506, FiveSecondByteResponseFactory())
reactor.listenTCP(5507, ThirtySecondByteResponseFactory())

app = Flask(__name__)

@app.route("/sleep/<float:n>")
def hello(n):
    time.sleep(n)
    hdrs = get_dict('headers')
    r = Response(response=json.dumps(hdrs), status=200,
                 headers={'Content-Type': 'application/json'})
    return r

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
site = Site(resource)
reactor.listenTCP(5508, site)

print "Listening..."
reactor.run()

