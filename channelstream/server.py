import uuid, sys

from twisted.python import log
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

from autobahn.twisted.resource import WebSocketResource, \
    WSGIRootResource
from wsgi_app import make_app
from ws_protocol import BroadcastServerFactory, BroadcastServerProtocol


def run_server(config):
    if config['debug']:
        log.startLogging(sys.stdout)
        debug = True
    else:
        debug = False

    if debug:
        log.startLogging(sys.stdout)

    ServerFactory = BroadcastServerFactory
    factory = ServerFactory(
        "ws://%s:%s" % (config['host'], config['port']),
        debug=debug,
        debugCodePaths=debug)

    factory.protocol = BroadcastServerProtocol
    wsResource = WebSocketResource(factory)
    ## create a Twisted Web WSGI resource for our Pyramid server
    app = make_app(config, factory)
    wsgiResource = WSGIResource(reactor, reactor.getThreadPool(), app)
    ## create a root resource serving everything via WSGI/, but
    ## the path "/listen" served by our WebSocket stuff
    rootResource = WSGIRootResource(wsgiResource, {'listen': wsResource})
    ## create a Twisted Web Site and run everything
    ##
    site = Site(rootResource)

    reactor.listenTCP(config['port'], site, interface=config['host'])
    reactor.run()
