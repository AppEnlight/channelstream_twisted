import logging
from datetime import datetime

from pyramid.view import view_config
from pyramid.httpexceptions import HTTPUnauthorized
from pyramid.security import forget
from channelstream.user import User
from channelstream.connection import Connection
from channelstream.channel import Channel


log = logging.getLogger(__name__)


class ServerViews(object):
    def __init__(self, request):
        self.request = request

    @view_config(route_name='action', match_param='action=connect',
                 renderer='json', permission='access')
    def connect(self):
        """return the id of connected users - will be secured with password string
        for webapp to internally call the server - we combine conn string with user id,
        and we tell which channels the user is allowed to subscribe to"""
        user_name = self.request.json_body.get('user')
        def_status = self.request.registry.server_config['status_codes'][
            'online']
        user_status = int(self.request.json_body.get('status', def_status))
        conn_id = self.request.json_body.get('conn_id')
        subscribe_to_channels = self.request.json_body.get('channels')
        if user_name is None:
            self.request.response.status = 400
            return {'error': "No username specified"}
        if not subscribe_to_channels:
            self.request.response.status = 400
            return {'error': "No channels specified"}

        # everything is ok so lets add new connection to channel and connection list
        ws_factory = self.request.registry.ws_factory
        if not user_name in ws_factory.users:
            user = User(user_name, def_status)
            ws_factory.users[user_name] = user
        else:
            user = ws_factory.users[user_name]
        connection = Connection(user_name, conn_id)
        if not connection.id in ws_factory.connections:
            ws_factory.connections[connection.id] = connection
        user.add_connection(connection)
        for channel_name in subscribe_to_channels:
            # user gets assigned to a channel
            if channel_name not in ws_factory.channels:
                channel = Channel(channel_name)
                ws_factory.channels[channel_name] = channel
            ws_factory.channels[channel_name].add_connection(connection)
        log.info('connecting %s with uuid %s' % (user_name, connection.id))
        return {'conn_id': connection.id, 'status': user.status}

    @view_config(route_name='action', match_param='action=subscribe',
                 renderer='json', permission='access')
    def subscribe(self, *args):
        """ call this to subscribe specific connection to new channels """
        ws_factory = self.request.registry.ws_factory
        conn_id = self.request.json_body.get('conn_id',
                                             self.request.GET.get('conn_id'))
        connection = ws_factory.connections.get(conn_id)
        subscribe_to_channels = self.request.json_body.get('channels')
        if not connection:
            self.request.response.status = 403
            return {'error': "Unknown connection"}
        if not subscribe_to_channels:
            self.request.response.status = 400
            return {'error': "No channels specified"}
        # everything is ok so lets add new connection to channel and connection list
        # lets lock it just in case
        # find the right user
        user = ws_factory.users.get(connection.user_name)
        subscribed_channels = []
        if user:
            for channel_name in subscribe_to_channels:
                if channel_name not in ws_factory.channels:
                    channel = Channel(channel_name)
                    ws_factory.channels[channel_name] = channel
                ws_factory.channels[channel_name].add_connection(connection)
        for channel in ws_factory.channels.itervalues():
            if user.user_name in channel.connections:
                subscribed_channels.append(channel.name)
        return subscribed_channels

    @view_config(route_name='action', match_param='action=user_status',
                 renderer='json', permission='access')
    def user_status(self):
        """ set the status of specific user """
        ws_factory = self.request.registry.ws_factory
        user_name = self.request.json_body.get('user')
        def_status = self.request.registry.server_config['status_codes'][
            'online']
        user_status = int(self.request.json_body.get('status', def_status))
        if not user_name:
            self.request.response.status = 400
            return {'error': "No username specified"}

        user_inst = ws_factory.users.get(user_name)
        if user_inst:
            user_inst.status = user_status
            # mark active
            user_inst.last_active = datetime.utcnow()
        return {}

    @view_config(route_name='action', match_param='action=message',
                 renderer='json', permission='access')
    def message(self):
        ws_factory = self.request.registry.ws_factory
        msg = self.request.json_body
        if msg.get('timestamp'):
            # if present lets use timestamp provided in the message
            if '.' in msg['timestamp']:
                timestmp = datetime.strptime(msg['timestamp'],
                                             '%Y-%m-%dT%H:%M:%S.%f')
            else:
                timestmp = datetime.strptime(msg['timestamp'],
                                             '%Y-%m-%dT%H:%M:%S')
        else:
            timestmp = datetime.utcnow()
        message = {'user': msg.get('user'),
                   'message': msg['message'],
                   'type': 'message',
                   'timestamp': timestmp
        }
        pm_users = msg.get('pm_users', [])
        total_sent = 0
        if msg.get('channel'):
            channel_inst = ws_factory.channels.get(msg['channel'])
            if channel_inst:
                total_sent += channel_inst.add_message(message,
                                                       pm_users=pm_users,
                                                       factory=ws_factory
                )
        elif pm_users:
            # if pm then iterate over all users and notify about new message hiyoo!!
            for user_name in pm_users:
                user_inst = ws_factory.users.get(user_name)
                if user_inst:
                    total_sent += user_inst.add_message(message)
        ws_factory.total_messages += total_sent

    @view_config(route_name='action', match_param='action=channel_config',
                 renderer='json', permission='access')
    def channel_config(self):
        """ call this to subscribe specific connection to new channels """
        ws_factory = self.request.registry.ws_factory
        channel_data = self.request.json_body
        if not channel_data:
            self.request.response.status = 400
            return {'error': "No channels specified"}

        json_data = []
        for channel_name, config in channel_data:
            if not channel_inst:
                channel = Channel(channel_name)
                ws_factory.channels[channel_name] = channel
            channel_inst = ws_factory.channels[channel_name]
            for k, v in config.iteritems():
                setattr(channel_inst, k, v)
            json_data.append({'name': channel_inst.name,
                              'long_name': channel_inst.long_name,
                              'presence': channel_inst.presence,
                              'salvagable': channel_inst.salvagable,
                              'store_history': channel_inst.store_history,
                              'history_size': channel_inst.history_size
            })
        return json_data

    @view_config(context='channelstream.wsgi_views.wsgi_security:RequestBasicChannenge')
    def admin_challenge(self):
        response = HTTPUnauthorized()
        response.headers.update(forget(self.request))
        return response

    @view_config(route_name='admin',
                 renderer='templates/admin.jinja2', permission='access')
    def admin(self):
        ws_factory = self.request.registry.ws_factory
        uptime = datetime.utcnow() - ws_factory.started_on
        total_unique_messages = ws_factory.total_unique_messages
        total_messages = ws_factory.total_messages
        remembered_user_count = len(
            [user for user in ws_factory.users.iteritems()])
        unique_user_count = len(
            [user for user in ws_factory.users.itervalues() if
             user.connections])
        total_connections = sum(
            [len(user.connections) for user in ws_factory.users.itervalues()])
        return {
            "remembered_user_count": remembered_user_count,
            "unique_user_count": unique_user_count,
            "total_connections": total_connections,
            "total_messages": total_messages,
            "total_unique_messages": total_unique_messages,
            "channels": ws_factory.channels,
            "users": ws_factory.users, "uptime": uptime
        }


    @view_config(route_name='action', match_param='action=info',
                 renderer='json', permission='access')
    def info(self):
        ws_factory = self.request.registry.ws_factory
        start_time = datetime.now()

        json_data = {"channels": {}, "unique_users": len(ws_factory.users)}

        # select everything for empty list
        if not self.request.body or not self.request.json_body.get('channels'):
            req_channels = ws_factory.channels.keys()
        else:
            req_channels = self.request.json_body['channels']
        # return requested channel info
        for channel_inst in [chan for chan in ws_factory.channels.values() if
                             chan.name in req_channels]:

            json_data["channels"][channel_inst.name] = {}
            json_data["channels"][channel_inst.name]['total_users'] = len(
                channel_inst.connections)
            json_data["channels"][channel_inst.name]['total_connections'] = sum(
                [len(conns) for conns in channel_inst.connections.values()])
            json_data["channels"][channel_inst.name]['users'] = []
            for user_name in channel_inst.connections.keys():
                user_inst = ws_factory.users.get(user_name)
                udata = {'user': user_inst.user_name,
                         'status': user_inst.status,
                         "connections": [conn.id for conn in
                                         channel_inst.connections[user_name]]}
                json_data["channels"][channel_inst.name]['users'].append(udata)
            json_data["channels"][channel_inst.name][
                'last_active'] = channel_inst.last_active
        log.info('info time: %s' % (datetime.now() - start_time))
        return json_data