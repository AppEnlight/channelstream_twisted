import datetime
from channelstream.ext_json import json

class Connection(object):
    """ Represents a browser connection"""
    def __init__(self, user_name, conn_id):
        self.user_name = user_name  # hold user id/name of connection
        self.last_active = datetime.datetime.utcnow()
        self.socket = None
        self.id = conn_id

    def __repr__(self):
        return '<Connection: id:%s, owner:%s>' % (self.id, self.user_name)

    def add_message(self, message=None):
        if self.socket:
            self.last_active = datetime.datetime.utcnow()
            if message:
                self.socket.sendMessage(json.dumps([message]))
            else:
                self.socket.sendMessage(json.dumps([]))

    def mark_for_gc(self):
        # set last active time for connection 1 hour in past for GC
        self.last_active -= datetime.timedelta(minutes=60)