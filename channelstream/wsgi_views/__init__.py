"""View handlers package.
"""
import logging


log = logging.getLogger(__name__)


def includeme(config):
    config.add_route('index', '/')
    config.add_route('demo', '/demo')
    config.add_route('admin', '/admin')
    config.add_route('action', '/{action}')
    config.add_route('section_action', '/{section}/{action}')