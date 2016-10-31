"""
This module contains the worker events framework. Listeners should subscribe
to events by calling, e.g.

    ``girder_worker.events.bind('event.name', 'my.handler', handler_function)``

And events should be published like so:

    ``e = girder_worker.events.trigger('event.name', info)``

The variable ``e`` would be the event that was created, which includes any
responses that were added by subscribers to the event.
"""

_mapping = {}


class Event(object):
    """
    An Event object is created when an event is triggered. It is passed to
    each of the listeners of the event, which have a chance to add information
    to the event, and also optionally stop the event from being further
    propagated to other listeners, and also optionally instruct the caller that
    it should not execute its default behavior.
    """

    def __init__(self, name, info):
        self.name = name
        self.info = info
        self.propagate = True
        self.default_prevented = False
        self.responses = []

    def prevent_default(self):
        self.default_prevented = True
        return self

    def stop_propagation(self):
        self.propagate = False
        return self

    def add_response(self, response):
        self.responses.append(response)
        return self


def bind(event_name, handler_name, handler):
    global _mapping
    if event_name not in _mapping:
        _mapping[event_name] = []

    _mapping[event_name].append({
        'name': handler_name,
        'handler': handler
    })


def unbind(event_name, handler_name):
    global _mapping
    if event_name not in _mapping:
        return

    for handler in _mapping[event_name]:
        if handler['name'] == handler_name:
            _mapping[event_name].remove(handler)
            break


def trigger(event_name, info=None):
    global _mapping
    e = Event(event_name, info)
    for handler in _mapping.get(event_name, ()):
        handler['handler'](e)

        if e.propagate is False:
            break

    return e
