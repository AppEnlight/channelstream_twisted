from pyramid.config import Configurator
from pyramid.renderers import JSON
import datetime
from channelstream.ext_json import json

def datetime_adapter(obj, request):
    return obj.isoformat()

def make_app(server_config, factory):
    config = Configurator()
    json_renderer = JSON(serializer=json.dumps)
    json_renderer.add_adapter(datetime.datetime, datetime_adapter)
    config.add_renderer('json', json_renderer)
    config.add_static_view('static', path='channelstream:static/')
    config.include('pyramid_jinja2')
    config.include('wsgi_views')
    config.scan('wsgi_views')

    config.registry.ws_factory = factory
    config.registry.server_config = server_config
    app = config.make_wsgi_app()
    return app