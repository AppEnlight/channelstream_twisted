__author__ = 'ergo'
import logging
import optparse
import ConfigParser

from channelstream.server import run_server


def cli_start():
    config = {
        'secret': '',
        'admin_secret': '',
        'gc_conns_after': 30,
        'gc_channels_after': 3600 * 72,
        'wake_connections_after': 5,
        'allow_posting_from': [],
        'port': 8000,
        'external_port':None,
        'host': '0.0.0.0',
        'debug': False,
        'status_codes': {
            "offline": 0,
            "online": 1,
            "away": 2,
            "hidden": 3,
            "busy": 4,
        }
    }

    parser = optparse.OptionParser()
    parser.add_option("-i", "--ini", dest="ini",
                      help="config file location",
                      default=None)
    parser.add_option("-s", "--secret", dest="secret",
                      help="secret used to secure your requests",
                      default='secret')
    parser.add_option("-a", "--admin_secret", dest="admin_secret",
                      help="secret used to secure your admin_panel",
                      default='admin_secret')
    parser.add_option("-o", "--o", dest="host",
                      help="host ip on which the server listens to",
                      default='0.0.0.0')
    parser.add_option("-p", "--port", dest="port",
                      help="port on which the server listens to",
                      default=8000)
    parser.add_option("-e", "--external_port", dest="external_port",
                      help="external proxy port",
                      default=None)
    parser.add_option("-d", "--debug", dest="debug",
                      help="debug",
                      default=0)
    parser.add_option("-x", "--allowed_post_ip", dest="allow_posting_from",
                      help="comma separated list of ip's that can post to server",
                      default="127.0.0.1"
    )
    (options, args) = parser.parse_args()
    if options.ini:
        parser = ConfigParser.ConfigParser()
        parser.read(options.ini)
        try:
            config['debug'] = parser.getboolean('channelstream', 'debug')
        except ConfigParser.NoOptionError as e:
            pass
        try:
            config['port'] = parser.getint('channelstream', 'port')
        except ConfigParser.NoOptionError as e:
            pass
        try:
            config['external_port'] = parser.getint('channelstream', 'external_port')
        except ConfigParser.NoOptionError as e:
            pass
        try:
            config['host'] = parser.get('channelstream', 'host')
        except ConfigParser.NoOptionError as e:
            pass
        try:
            config['secret'] = parser.get('channelstream', 'secret')
        except ConfigParser.NoOptionError as e:
            pass
        try:
            config['admin_secret'] = parser.get('channelstream', 'admin_secret')
        except ConfigParser.NoOptionError as e:
            pass
        try:
            ips = [ip.strip() for ip in parser.get('channelstream',
                                               'allow_posting_from').split(',')]
            config['allow_posting_from'].extend(ips)
        except ConfigParser.NoOptionError as e:
            pass
        try:
            config['demo_app_url'] = parser.get('channelstream', 'demo_app_url')
        except ConfigParser.NoOptionError as e:
            pass

    else:
        config['debug'] = int(options.debug)
        config['port'] = int(options.port)
        if options.external_port:
            config['external_port'] = int(options.external_port)
        config['host'] = options.host
        config['secret'] = options.secret
        config['admin_secret'] = options.admin_secret
        config['allow_posting_from'].extend(
            [ip.strip() for ip in options.allow_posting_from.split(',')])
    run_server(config)
