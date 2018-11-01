import click
from girder_worker_utils.decorators import (
    VarsArg,
    KwargsArg,
    PositionalArg,
    KeywordArg)

# TODO Implement MVP
class VarsArgCli(VarsArg):
    click_type = click.argument

    def decorate(self, f):
        pass

    def get_args(self):
        return []

    def get_opts(self):
        return {}


# TODO Implement MVP
class KwargsArgCli(KwargsArg):
    click_type = click.argument

    def decorate(self, f):
        pass

    def get_args(self):
        return []

    def get_opts(self):
        return {}


class PositionalArgCli(PositionalArg):

    def decorate(self, f):
        click.argument(*self.get_args(), **self.get_opts())(f)

    def get_args(self):
        if not hasattr(self, 'cli_args'):
            cli_args = (self.name, )
        else:
            cli_args = self.cli_args

        return cli_args

    def get_opts(self):
        if not hasattr(self, 'cli_opts'):
            cli_opts = {}
        else:
            cli_opts = self.cli_opts

        return cli_opts


class KeywordArgCli(KeywordArg):
    def decorate(self, f):
        click.option(*self.get_args(), **self.get_opts())(f)

    def get_opts(self):
        if not hasattr(self, 'cli_opts'):
            cli_opts = {}
        else:
            cli_opts = self.cli_opts

        return cli_opts

    def get_args(self):
        if not hasattr(self, 'cli_args'):
            cli_args = ('-{}'.format(self.name), )
        else:
            cli_args = self.cli_args

        return cli_args
