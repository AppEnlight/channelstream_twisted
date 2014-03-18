from twisted.internet import reactor
import logging

from autobahn.twisted.websocket import WebSocketServerFactory, \
    WebSocketServerProtocol
from  autobahn.websocket.http import HttpException

import simplejson as json
from datetime import datetime, timedelta

log = logging.getLogger(__name__)


class BroadcastServerProtocol(WebSocketServerProtocol):
    def onOpen(self):
        self.factory.register(self)
        self.tick()


    def onConnect(self, request):
        self.conn_id = request.params.get('conn_id')[0]
        if self.conn_id not in self.factory.connections:
            raise HttpException(401, 'Unauthorized')

    def onMessage(self, payload, isBinary):
        now = datetime.utcnow()
        if self.conn_id in self.factory.connections:
            connection = self.factory.connections[self.conn_id]
            connection.last_active = now
            user = self.factory.users.get(connection.user_name)
            if user:
                user.last_active = now

    def connectionLost(self, reason):
        WebSocketServerProtocol.connectionLost(self, reason)
        self.factory.unregister(self)

    def tick(self):
        self.sendMessage('[]')
        reactor.callLater(5, self.tick)


class BroadcastServerFactory(WebSocketServerFactory):
    """
    Simple broadcast server broadcasting any message it receives to all
    currently connected clients.
    """

    def __init__(self, url, debug=False, debugCodePaths=False):
        WebSocketServerFactory.__init__(self, url, debug=debug,
                                        debugCodePaths=debugCodePaths)
        self.users = {}
        self.connections = {}
        self.channels = {}
        self.total_messages = 0
        self.total_unique_messages = 0
        self.started_on = datetime.utcnow()

        reactor.callLater(5, self.gc_conns)
        reactor.callLater(60, self.gc_users)

    def gc_users(self):
        threshold = datetime.utcnow() - timedelta(days=1)
        for user in self.users.values():
            if user.last_active < threshold:
                self.users.pop(user.user_name)

    def gc_conns(self):
        start_time = datetime.utcnow()
        threshold = start_time - timedelta(seconds=5)
        collected_conns = []
        # collect every ref in chanels
        for channel in self.channels.itervalues():
            for k, conns in channel.connections.items():
                for conn in conns:
                    if conn.last_active < threshold:
                        channel.connections[k].remove(conn)
                        collected_conns.append(conn)
                if not channel.connections[k]:
                    del channel.connections[k]
        # remove old conns from users and conn dict
        for conn in collected_conns:
            if conn.user_name in self.users:
                if conn in self.users[conn.user_name].connections:
                    self.users[conn.user_name].connections.remove(conn)
            if conn.id in self.connections:
                del self.connections[conn.id]
        log.info('cleanup time %s' % (datetime.utcnow() - start_time))

        reactor.callLater(5, self.gc_conns)

    def register(self, client):
        if client.conn_id in self.connections:
            self.connections[client.conn_id].socket = client
            print("registered client {}".format(client.peer))
        else:
            raise HttpException(403, 'Not Found')

    def unregister(self, client):
        if client.conn_id in self.connections:
            connection = self.connections[client.conn_id]

            if connection.user_name in self.users:
                # remove conn id instance from user
                self.users[connection.user_name].connections.remove(connection)
            # remove from channel
            for channel in self.channels.itervalues():
                if connection.user_name in channel.connections:
                    channel.connections[connection.user_name].remove(connection)
            # remove from conections
            del self.connections[client.conn_id]
            print("unregistered client {}".format(client.peer))