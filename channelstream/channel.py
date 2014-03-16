from twisted.python import log
import datetime
import logging

log = logging.getLogger(__name__)


class Channel(object):
    """ Represents one of our chat channels - has some config options """

    def __init__(self, name, long_name=None):
        self.name = name
        self.long_name = long_name
        self.last_active = datetime.datetime.utcnow()
        self.connections = {}
        self.presence = False
        self.salvagable = False
        self.store_history = False
        self.history_size = 10
        self.history = []
        log.info('%s created' % self)

    def add_connection(self, connection):
        if not connection.user_name in self.connections:
            self.connections[connection.user_name] = []
        if connection not in self.connections[connection.user_name]:
            self.connections[connection.user_name].append(connection)

    def add_message(self, message, factory, pm_users=None, exclude_user=None):
        if not pm_users:
            pm_users = []
        factory.total_unique_messages += 1
        self.last_active = datetime.datetime.utcnow()
        if self.store_history:
            self.history.append(message)
            self.history = self.history[(self.history_size) * -1:]
        message.update({'channel': self.name})
        # message everyone subscribed except excluded
        total_sent = 0
        for u, conns in self.connections.iteritems():
            if u != exclude_user:
                for connection in conns:
                    if not pm_users or connection.user in pm_users:
                        connection.add_message(message)
                        total_sent += 1
        return total_sent

    def __repr__(self):
        return '<Channel: %s, connections:%s>' % (
            self.name, len(self.connections))
