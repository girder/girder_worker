import click

from .entrypoint import get_extensions, get_extension_tasks, import_all_includes


def _get_task_command(extension, name):
    import_all_includes()
    for task in get_extension_tasks(extension).values():
        if name == task.main.name:
            return task.main


class GWCommand(click.MultiCommand):
    def list_commands(self, ctx):
        import_all_includes()
        for extension in get_extensions():
            if extension not in ('core', 'docker'):
                yield extension

    def get_command(self, ctx, name):
        if name not in self.list_commands(ctx):
            return None
        return GWExtensionCommand(name)


class GWExtensionCommand(click.MultiCommand):
    def __init__(self, extension):
        self._extension = extension
        super(GWExtensionCommand, self).__init__()

    def list_commands(self, ctx):
        import_all_includes()
        for task in get_extension_tasks(self._extension).values():
            yield task.main.name

    def get_command(self, ctx, name):
        import_all_includes()
        if name not in self.list_commands(ctx):
            return None

        for task in get_extension_tasks(self._extension).values():
            if name == task.main.name:
                return task.main


@click.command(cls=GWCommand)
def main():
    pass


if __name__ == '__main__':
    main()
