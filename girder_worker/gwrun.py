import click

from .entrypoint import get_extensions, get_extension_tasks, import_all_includes


def _iterate_tasks():
    import_all_includes()
    for extension in get_extensions():
        if extension not in ('core', 'docker'):
            for task in get_extension_tasks(extension).values():
                yield task.main.name, task.main


class GWCommand(click.MultiCommand):
    def list_commands(self, ctx):
        for name, task in _iterate_tasks():
            yield name

    def get_command(self, ctx, name):
        for name_, task in _iterate_tasks():
            if name_ == name:
                return task


@click.command(cls=GWCommand)
def main():
    pass


if __name__ == '__main__':
    main()
