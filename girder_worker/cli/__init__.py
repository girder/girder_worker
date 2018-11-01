from girder_worker_utils.decorators import GWFuncDesc
from girder_worker.cli.arguments import (
    VarsArgCli,
    KwargsArgCli,
    PositionalArgCli,
    KeywordArgCli)

GWFuncDesc.VarsArgCls = VarsArgCli
GWFuncDesc.KwargsArgCls = KwargsArgCli
GWFuncDesc.PositionalArgCls = PositionalArgCli
GWFuncDesc.KeywordArgCls = KeywordArgCli
