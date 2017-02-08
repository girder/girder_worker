import core
from .utils import JobManager, JobStatus
from .app import app


@app.task(name='girder_worker.run', bind=True)
def run(task, *pargs, **kwargs):
    retval = 0

    with task.job_manager as jm:
        kwargs['_job_manager'] = jm
        kwargs['status'] = JobStatus.RUNNING
        retval = core.run(*pargs, **kwargs)
        return retval


@app.task(name='girder_worker.convert')
def convert(*pargs, **kwargs):
    return core.convert(*pargs, **kwargs)


@app.task(name='girder_worker.validators')
def validators(*pargs, **kwargs):
    _type, _format = pargs
    nodes = []

    for (node, data) in core.format.conv_graph.nodes(data=True):
        if ((_type is None) or (_type == node.type)) and \
           ((_format is None) or (_format == node.format)):
            nodes.append({'type': node.type,
                          'format': node.format,
                          'validator': data})

    return nodes
