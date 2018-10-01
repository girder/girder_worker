import click
import pkg_resources as pr
from click.core import Command, Argument, Option
from girder_worker.entrypoint import get_extensions, get_extension_tasks, import_all_includes
from stevedore import driver
from girder_worker_utils.decorators import (
    GWFuncDesc,
    Arg,
    KWArg)

GWRUN_ENTRYPOINT_GROUP = 'gwrun_output_handlers'

def _cast_to_command(f):
    if isinstance(f, Command):
        return f

    description = GWFuncDesc.get_description(f)
    if description is not None:
        for arg in reversed(description.arguments):
            if isinstance(arg, KWArg):
                if not hasattr(arg, 'cli_args'):
                    cli_args = ('-{}'.format(arg.name), )
                else:
                    cli_args = arg.cli_args

                if not hasattr(arg, 'cli_opts'):
                    cli_opts = {}
                else:
                    cli_opts = arg.cli_opts

                click.option(*cli_args, **cli_opts)(f)
            elif isinstance(arg, Arg):
                if not hasattr(arg, 'cli_args'):
                    cli_args = (arg.name, )
                else:
                    cli_args = arg.cli_args

                if not hasattr(arg, 'cli_opts'):
                    cli_opts = {}
                else:
                    cli_opts = arg.cli_opts

                click.argument(*cli_args, **cli_opts)(f)

            else:
                pass
    return click.decorators.command()(f)


def _iterate_tasks():
    import_all_includes()
    for extension in get_extensions():
        if extension not in ('core', 'docker'):
            for task in get_extension_tasks(extension).values():
                yield task



class GWCommand(click.MultiCommand):
    def list_commands(self, ctx):
        return [_cast_to_command(task).name for task in _iterate_tasks()]

    def get_command(self, ctx, name):
        for task in _iterate_tasks():
            if task.description().func_name == name:
                return _cast_to_command(task)

    def __call__(self, *args, **kwargs):
        return self.main(*args, **kwargs)



@click.group(cls=GWCommand, invoke_without_command=True)
@click.option('-o', '--output',
              type=click.Choice([ep.name for ep in pr.iter_entry_points(GWRUN_ENTRYPOINT_GROUP)]),
              default='stdout')
@click.pass_context
def main(ctx, output):
    pass


@main.resultcallback()
def process_output(processors, output):
    for ep in pr.iter_entry_points(GWRUN_ENTRYPOINT_GROUP):
        if ep.name == output:
            _handler = ep.load()
            return _handler(processors)

    # Throw warning here?
    return processors


if __name__ == '__main__':
    main() #noqa
