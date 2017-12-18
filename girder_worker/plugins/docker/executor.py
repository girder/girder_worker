import os
import re

from girder_worker.core import TaskSpecValidationError, utils
from girder_worker.core.io import make_stream_fetch_adapter, make_stream_push_adapter
from girder_worker.docker.tasks import _docker_run
from girder_worker.docker.transforms import (
    ContainerStdOut,
    ContainerStdErr
)
from girder_worker.docker.transforms.girder import ProgressPipe
from girder_worker.docker.io import (
    NamedPipeReader,
    NamedPipeWriter,
    FDWriteStreamConnector,
    NamedPipe,
    FDReadStreamConnector
)


DATA_VOLUME = '/mnt/girder_worker/data'

_inputRe = re.compile(r'\$input\{([^}]+)\}')
_outputRe = re.compile(r'\$output\{([^}]+)\}')
_flagRe = re.compile(r'\$flag\{([^}]+)\}')


def _transform_path(inputs, taskInputs, inputId, tmpDir):
    """
    If the input specified by inputId is a filepath target, we transform it to
    its absolute path within the Docker container (underneath the data mount).
    """
    for ti in taskInputs.itervalues():
        tiId = ti['id'] if 'id' in ti else ti['name']
        if tiId == inputId:
            if (ti.get('target') == 'filepath' and
                    inputs[inputId]['script_data'].startswith(tmpDir.rstrip(os.sep) + os.sep)):
                rel = os.path.relpath(inputs[inputId]['script_data'], tmpDir)
                return os.path.join(DATA_VOLUME, rel)
            else:
                return inputs[inputId]['script_data']

    raise Exception('No task input found with id = ' + inputId)


def _expand_args(args, inputs, taskInputs, outputs, tmpDir):
    """
    Expands arguments to the container execution if they reference input or output
    data. For example, if an input has id=foo, then a container arg of the form
    ``$input{foo}`` would be expanded to the runtime value of that input. If that
    input is a filepath target, the file path will be transformed into the
    location that it will be available inside the running container.

    Output file paths can be referenced using ``$output{foo}``. That will expand
    to use the "name" field of the corresponding output binding for this task invocation.
    TODO(zach) add example of task output and corresponding output binding. This
    expansion will use the absolute path format with DATA_VOLUME as the base path.
    """
    newArgs = []

    for arg in args:
        skip = False
        for inputId in _inputRe.findall(arg):
            if inputId in inputs:
                transformed = _transform_path(
                    inputs, taskInputs, inputId, tmpDir)
                arg = arg.replace('$input{%s}' % inputId, str(transformed))
            elif inputId == '_tempdir':
                arg = arg.replace('$input{_tempdir}', DATA_VOLUME)
            else:
                raise Exception('Could not expand token: $input{%s}.' % inputId)
        for inputId in _flagRe.findall(arg):
            if inputId in inputs and inputs[inputId]['script_data']:
                val = taskInputs[inputId].get('arg', inputId)
            else:
                val = ''
            arg = arg.replace('$flag{%s}' % inputId, val)
            if not arg:
                skip = True
        for outputId in _outputRe.findall(arg):
            if outputId in outputs and 'name' in outputs[outputId]:
                arg = arg.replace(
                    '$output{%s}' % outputId, os.path.join(DATA_VOLUME, outputs[outputId]['name']))
            else:
                raise Exception('Could not expand token: $output{%s}.' % outputId)
        if not skip:
            newArgs.append(arg)

    return newArgs


def validate_task_outputs(task_outputs):
    """
    This is called prior to fetching inputs to make sure the output specs are
    valid. Outputs in docker mode can result in side effects, so it's best to
    make sure the specs are valid prior to fetching.
    """
    for name, spec in task_outputs.iteritems():
        if spec.get('target') == 'filepath':
            path = spec.get('path', name)
            if path.startswith('/') and not path.startswith(DATA_VOLUME + '/'):
                raise TaskSpecValidationError(
                    'Docker filepath output paths must either start with '
                    '"%s/" or be specified relative to that directory.' %
                    DATA_VOLUME)
        elif name not in ('_stdout', '_stderr'):
            raise TaskSpecValidationError(
                'Docker outputs must be either "_stdout", "_stderr", or '
                'filepath-target outputs.')


def _setup_streams(task_inputs, inputs, task_outputs, outputs, tempdir, job_mgr, progress_pipe):
    """
    Returns a 2 tuple of input and output pipe mappings. The first element is
    a dict mapping input file descriptors to the corresponding stream adapters,
    the second is a dict mapping output file descriptors to the corresponding
    stream adapters. This also handles the special cases of STDIN, STDOUT, and
    STDERR mappings, and in the case of non-streaming standard IO pipes, will
    create default bindings for those as well.
    """
    stream_connectors = []

    def stream_pipe_path(id, spec, bindings):
        """
        Helper to check for a  valid streaming IO specs. If the
        given spec is not a streaming spec, returns None. If it is, returns the
        path.
        """
        if spec.get('stream') and id in bindings and spec.get('target') == 'filepath':
            path = spec.get('path', id)
            if path.startswith('/'):
                raise Exception('Streaming filepaths must be relative.')
            path = os.path.join(tempdir, path)
            return path

        return None

    # handle stream inputs
    for id, spec in task_inputs.iteritems():

        path = stream_pipe_path(id, spec, inputs)
        # We have a streaming input
        if path is not None:
            writer = NamedPipeWriter(NamedPipe(path))
            connector = FDWriteStreamConnector(make_stream_fetch_adapter(inputs[id]), writer)
            stream_connectors.append(connector)
            # Don't open from this side, must be opened for reading first!

    # handle stream outputs
    for id, spec in task_outputs.iteritems():
        path = stream_pipe_path(id, spec, outputs)
        if path is not None:
            reader = NamedPipeReader(NamedPipe(path))
            connector = FDReadStreamConnector(reader, make_stream_push_adapter(outputs[id]))
            stream_connectors.append(connector)

    # handle special stream output for job progress
    if progress_pipe and job_mgr:
        progress_pipe = ProgressPipe(os.path.join(tempdir, '.girder_progress'))
        stream_connectors.append(progress_pipe.open())

    return stream_connectors


def _setup_std_streams(task_outputs, outputs):
    def push_adapter(id):
        adapter = None
        if id in task_outputs and id in outputs:
            if task_outputs[id].get('stream'):
                adapter = make_stream_push_adapter(outputs[id])
            else:
                adapter = utils.AccumulateDictAdapter(outputs[id], 'script_data')

        return adapter

    return (push_adapter('_stdout'), push_adapter('_stderr'))


def add_input_volumes(inputs, volumes):
    """
    For any filepath input that has a direct_path property AND a script_data
    property that matches, add a read-only volume to the docker volumes record
    to give access to that path.

    :param inputs: the spec inputs.
    :param volumes: the docker volumes dictionary to modify.
    """
    for input in inputs.itervalues():
        if 'direct_path' in input and input.get('script_data') == input['direct_path']:
            volume = input.get('script_data')
            if volume not in volumes:
                volumes[volume] = {
                    'bind': volume,
                    'mode': 'ro'
                }


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    image = task['docker_image']
    celery_task = kwargs.get('_celery_task')
    pull_image = task.get('pull_image', True)
    progress_pipe = task.get('progress_pipe', False)
    remove_container = kwargs.get('_rm_container', False)
    # Allow run args to overridden
    extra_run_kwargs = task.get('docker_run_args', {})
    tempdir = kwargs.get('_tempdir')
    job_mgr = kwargs.get('_job_manager')
    args = _expand_args(task.get('container_args', []), inputs, task_inputs, outputs, tempdir)

    stream_connectors = _setup_streams(
        task_inputs, inputs, task_outputs, outputs, tempdir, job_mgr, progress_pipe)

    stdout_fetch_adapter, stderr_fetch_adapter = _setup_std_streams(task_outputs, outputs)

    # Connect up stdout and strerr ContainerStdOut() and ContainerStdErr() will be
    # replaced with the real streams when the container is started.
    if stdout_fetch_adapter is not None:
        stream_connectors.append(FDReadStreamConnector(ContainerStdOut(), stdout_fetch_adapter))
    if stderr_fetch_adapter is not None:
        stream_connectors.append(FDReadStreamConnector(ContainerStdErr(), stderr_fetch_adapter))

    entrypoint = None
    if 'entrypoint' in task:
        if isinstance(task['entrypoint'], (list, tuple)):
            entrypoint = task['entrypoint']
        else:
            entrypoint = [task['entrypoint']]

    volumes = {
        tempdir: {
            'bind': DATA_VOLUME,
            'mode': 'rw'
        }
    }
    add_input_volumes(inputs, volumes)

    _docker_run(celery_task, image, pull_image=pull_image, entrypoint=entrypoint,
                container_args=args, volumes=volumes, remove_container=remove_container,
                stream_connectors=stream_connectors, **extra_run_kwargs)

    for name, spec in task_outputs.iteritems():
        if spec.get('target') == 'filepath' and not spec.get('stream'):
            path = spec.get('path', '$output{%s}' % name)
            for outputId in _outputRe.findall(path):
                if outputId in outputs and 'name' in outputs[outputId]:
                    path = path.replace('$output{%s}' % outputId, outputs[outputId]['name'])
                elif 'path' in spec:
                    raise Exception('Could not expand token: $output{%s}.' % outputId)
                else:
                    path = name

            if not path.startswith('/'):
                # Assume relative paths are relative to the data volume
                path = os.path.join(DATA_VOLUME, path)

            # Convert data volume refs to the temp dir on the host
            path = path.replace(DATA_VOLUME, tempdir, 1)
            if not os.path.exists(path):
                raise Exception('Output filepath %s does not exist.' % path)
            outputs[name]['script_data'] = path
