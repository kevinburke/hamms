import logging

from twisted.internet import protocol, reactor

logging.basicConfig()
logger = logging.getLogger("hamms")
logger.error("hello")

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

reactor.listenTCP(5501, ListenForeverFactory())
reactor.listenTCP(5502, EmptyStringTerminateImmediatelyFactory())
reactor.listenTCP(5503, EmptyStringTerminateOnReceiveFactory())
reactor.run()
