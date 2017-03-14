import core
from girder_worker.utils import JobStatus
from .app import app


def _cleanup(*args, **kwargs):
    core.events.trigger('cleanup')


@app.task(name='girder_worker.run', bind=True, after_return=_cleanup)
def run(_celery_task, *pargs, **kwargs):
    kwargs['_job_manager'] = _celery_task.job_manager \
        if hasattr(_celery_task, 'job_manager') else None

    kwargs['status'] = JobStatus.RUNNING

    return core.run(*pargs, **kwargs)


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
