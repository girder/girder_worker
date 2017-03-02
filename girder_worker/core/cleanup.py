from . import events


def main():
    events.trigger('cleanup')
