import datetime
import os
import shutil
import socket
import sys
import threading
import time
import subprocess
import drmaa

try:
    import docker
    from docker.errors import DockerException, APIError, InvalidVersion
    from girder_worker.docker import nvidia
    from requests.exceptions import ReadTimeout
except ImportError:
    # These imports will not be available on the girder side.
    pass
from girder_worker.app import app, Task
from girder_worker import logger
from girder_worker.docker import utils
from girder_worker.docker.stream_adapter import DockerStreamPushAdapter
from girder_worker.docker.io import (
    FileDescriptorReader,
    FDWriteStreamConnector,
    FDReadStreamConnector,
    FDStreamConnector,
    StdStreamWriter
)

from girder_worker.docker.transforms import (
    ContainerStdErr,
    ContainerStdOut,
    _TemporaryVolumeBase,
    TemporaryVolume
)
from girder_worker_utils import _walk_obj


BLACKLISTED_DOCKER_RUN_ARGS = ['tty', 'detach']



def _pull_image(image):
    """
    Pulls the specified Docker image onto this worker.
    """
    client = docker.from_env(version='auto')
    try:
        client.images.pull(image)
    except DockerException:
        logger.exception('Error pulling Docker image %s:' % image)
        raise


def _get_docker_network():
    try:
        ip = socket.gethostbyname(socket.gethostname())
        if 'DOCKER_CLIENT_TIMEOUT' in os.environ:
            timeout = int(os.environ['DOCKER_CLIENT_TIMEOUT'])
            client = docker.from_env(version='auto', timeout=timeout)
        else:
            client = docker.from_env(version='auto')
        for container in client.containers.list(all=True, filters={'status': 'running'}):
            for nw in container.attrs['NetworkSettings']['Networks'].values():
                if nw['IPAddress'] == ip:
                    return 'container:%s' % container.id
    except Exception:
        logger.exception('Failed to get docker network')


def _remove_stopped_container(client, name):
    if name is None:
        return
    for container in client.containers.list(all=True, filters={'name': name}):
        try:
            logger.info('Removing container %s ' % (name))
            container.remove()
        except Exception:
            pass


def _run_container(image, container_args,  **kwargs):
    # TODO we could allow configuration of non default socket
    if 'DOCKER_CLIENT_TIMEOUT' in os.environ:
        timeout = int(os.environ['DOCKER_CLIENT_TIMEOUT'])
        client = docker.from_env(version='auto', timeout=timeout)
    else:
        client = docker.from_env(version='auto')

    runtime = kwargs.pop('runtime', None)
    origRuntime = runtime
    if runtime is None and nvidia.is_nvidia_image(client.api, image):
        runtime = 'nvidia'

    container_args = [str(arg) for arg in container_args]

    if 'network' not in kwargs and 'network_mode' not in kwargs:
        docker_network = _get_docker_network()
        if docker_network:
            kwargs = kwargs.copy()
            kwargs['network'] = docker_network

    logger.info('Running container: image: %s args: %s runtime: %s kwargs: %s'
                % (image, container_args, runtime, kwargs))
    try:
        name = None
        try:
            if runtime == 'nvidia' and kwargs.get('device_requests') is None:
                # Docker < 19.03 required the runtime='nvidia' argument.
                # Newer versions require a device request for some number of
                # GPUs.  This should handle either version of the docker
                # daemon.
                try:
                    device_requests_kwargs = kwargs.copy()
                    device_requests_kwargs['device_requests'] = [
                        docker.types.DeviceRequest(count=-1, capabilities=[['gpu']])]
                    name = device_requests_kwargs.setdefault(
                        'name',
                        'girder_worker_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                    return client.containers.run(
                        image, container_args, **device_requests_kwargs)
                except (APIError, InvalidVersion):
                    _remove_stopped_container(client, name)
                    pass
            kwargs = kwargs.copy()
            name = kwargs.setdefault(
                'name',
                'girder_worker_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
            return client.containers.run(
                image, container_args, runtime=runtime, **kwargs)
        except APIError:
            _remove_stopped_container(client, name)
            if origRuntime is None and runtime is not None:
                kwargs = kwargs.copy()
                name = kwargs.setdefault(
                    'name',
                    'girder_worker_' + datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f'))
                return client.containers.run(image, container_args, **kwargs)
            else:
                raise
    except DockerException:
        logger.exception('Exception when running docker container')
        raise


class _SocketReader(FileDescriptorReader):
    """
    Used to mediate the difference between the python 2/3 implementation of docker-py
    with python 2 attach_socket(...) returns a socket like object, with python 3
    it returns an instance of SocketIO.
    """
    def __init__(self, socket):
        self._socket = socket

    def read(self, n):
        # socket
        if hasattr(self._socket, 'recv'):
            return self._socket.recv(n)

        # SocketIO
        return self._socket.read(n)

    def fileno(self):
        return self._socket.fileno()

    def close(self):
        self._socket.close()


def _run_select_loop(  # noqa: C901
        task, container, read_stream_connectors, write_stream_connectors):
    stdout = None
    stderr = None
    try:
        # attach to standard streams
        stdout = container.attach_socket(params={
            'stdout': True,
            'logs': True,
            'stream': True
        })

        stderr = container.attach_socket(params={
            'stderr': True,
            'logs': True,
            'stream': True
        })

        def exit_condition():
            container.reload()
            return container.status in {'exited', 'dead'} or task.canceled

        # Look for ContainerStdOut and ContainerStdErr instances that need
        # to be replace with the real container streams.
        stdout_connected = False
        for read_stream_connector in read_stream_connectors:
            if isinstance(read_stream_connector.input, ContainerStdOut):
                stdout_reader = _SocketReader(stdout)
                read_stream_connector.output = DockerStreamPushAdapter(read_stream_connector.output)
                read_stream_connector.input = stdout_reader
                stdout_connected = True
                break

        stderr_connected = False
        for read_stream_connector in read_stream_connectors:
            if isinstance(read_stream_connector.input, ContainerStdErr):
                stderr_reader = _SocketReader(stderr)
                read_stream_connector.output = DockerStreamPushAdapter(read_stream_connector.output)
                read_stream_connector.input = stderr_reader
                stderr_connected = True
                break

        # If not stdout and stderr connection has been provided just use
        # sys.stdXXX
        if not stdout_connected:
            stdout_reader = _SocketReader(stdout)
            connector = FDReadStreamConnector(
                stdout_reader,
                DockerStreamPushAdapter(StdStreamWriter(sys.stdout)))
            read_stream_connectors.append(connector)

        if not stderr_connected:
            stderr_reader = _SocketReader(stderr)
            connector = FDReadStreamConnector(
                stderr_reader,
                DockerStreamPushAdapter(StdStreamWriter(sys.stderr)))
            read_stream_connectors.append(connector)

        # Run select loop
        utils.select_loop(exit_condition=exit_condition,
                          readers=read_stream_connectors,
                          writers=write_stream_connectors)

        if task.canceled:
            try:
                msg = 'Asking to stop container: %s' % container.id
                logger.info(msg)
                container.stop()
            # Catch the ReadTimeout from requests and wait for container to
            # exit. See https://github.com/docker/docker-py/issues/1374 for
            # more details.
            except ReadTimeout:
                tries = 10
                while tries > 0:
                    container.reload()
                    if container.status == 'exited':
                        break

                if container.status != 'exited':
                    msg = 'Unable to stop container: %s' % container.id
                    logger.error(msg)
            except DockerException as dex:
                logger.error(dex)
                raise

        container.reload()
        exit_code = container.attrs['State']['ExitCode']
        if not task.canceled and exit_code != 0:
            raise DockerException('Non-zero exit code from docker container (%d).' % exit_code)
    finally:
        # Close our stdout and stderr sockets
        if stdout:
            stdout.close()
        if stderr:
            stderr.close()


def _handle_streaming_args(args):
    processed_args = []
    write_streams = []
    read_streams = []

    def _maybe_path(arg):
        if hasattr(arg, 'path'):
            return arg.path()

        # Don't pass anything
        return ''

    for arg in args:
        if isinstance(arg, FDStreamConnector):
            if isinstance(arg, FDWriteStreamConnector):
                write_streams.append(arg)
                arg = _maybe_path(arg.output)

            elif isinstance(arg, FDReadStreamConnector):
                read_streams.append(arg)
                arg = _maybe_path(arg.input)

        processed_args.append(arg)

    return (processed_args, read_streams, write_streams)


class _RequestDefaultTemporaryVolume(_TemporaryVolumeBase):
    def __init__(self):
        super().__init__(None, None)
        self._make_paths()

    def transform(self, **kwargs):
        self._transformed = True


class DockerTask(Task):

    def _maybe_transform_argument(self, arg):
        return super()._maybe_transform_argument(
            arg, task=self, _default_temp_volume=self.request._default_temp_volume)

    def _maybe_transform_result(self, idx, result):
        return super()._maybe_transform_result(
            idx, result, _default_temp_volume=self.request._default_temp_volume)

    def __call__(self, *args, **kwargs):
        default_temp_volume = _RequestDefaultTemporaryVolume()
        self.request._default_temp_volume = default_temp_volume

        volumes = kwargs.setdefault('volumes', {})
        # If we have a list of volumes, the user provide a list of Volume objects,
        # we need to transform them.
        temp_volumes = []
        if isinstance(volumes, list):
            # See if we have been passed any TemporaryVolume instances.
            for v in volumes:
                if isinstance(v, TemporaryVolume):
                    temp_volumes.append(v)

            # First call the transform method, this we replace default temp volumes
            # with the instance associated with this task create above. That is any
            # reference to TemporaryVolume.default
            _walk_obj(volumes, self._maybe_transform_argument)

            # Now convert them to JSON
            def _json(volume):
                return volume._repr_json_()

            volumes = _walk_obj(volumes, _json)
            # We then need to merge them into a single dict and it will be ready
            # for docker-py.
            volumes = {k: v for volume in volumes for k, v in volume.items()}
            kwargs['volumes'] = volumes

        volumes.update(default_temp_volume._repr_json_())

        super().__call__(*args, **kwargs)
        threading.Thread(
            target=self._cleanup_temp_volumes,
            args=(temp_volumes, default_temp_volume),
            daemon=True).start()

    def _cleanup_temp_volumes(self, temp_volumes, default_temp_volume):
        # Set the permission to allow cleanup of temp directories
        temp_volumes = [v for v in temp_volumes if os.path.exists(v.host_path)]
        to_chmod = temp_volumes[:]
        # If our default_temp_volume instance has been transformed then we
        # know it has been used and we have to clean it up.
        if default_temp_volume._transformed:
            to_chmod.append(default_temp_volume)
            temp_volumes.append(default_temp_volume)

        if len(to_chmod) > 0:
            utils.chmod_writable([v.host_path for v in to_chmod])

        for v in temp_volumes:
            shutil.rmtree(v.host_path)


            
        

def _docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
                volumes=None, remove_container=True, stream_connectors=None, **kwargs):
    volumes = volumes or {}
    stream_connectors = stream_connectors or []
    container_args = container_args or []

    if pull_image:
        logger.info('Pulling Docker image: %s', image)
        _pull_image(image)

    if entrypoint is not None and not isinstance(entrypoint, (list, tuple)):
        entrypoint = [entrypoint]

    run_kwargs = {
        'tty': False,
        'volumes': volumes,
        'detach': True
    }

    # Allow run args to be overridden,filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in kwargs.items() if k not in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    if entrypoint is not None:
        run_kwargs['entrypoint'] = entrypoint

    container_args, read_streams, write_streams = _handle_streaming_args(container_args)

    for connector in stream_connectors:
        if isinstance(connector, FDReadStreamConnector):
            read_streams.append(connector)
        elif isinstance(connector, FDWriteStreamConnector):
            write_streams.append(connector)
        else:
            raise TypeError(
                "Expected 'FDReadStreamConnector' or 'FDWriterStreamConnector', received '%s'"
                % type(connector))

    # We need to open any read streams before starting the container, so the
    # underling named pipes are opened for read.
    for stream in read_streams:
        stream.open()

    container = _run_container(image, container_args, **run_kwargs)
    try:
        _run_select_loop(task, container, read_streams, write_streams)
    finally:
        if container and remove_container:
            container.reload()
            # If the container is still running issue a warning
            if container.status == 'running':
                logger.warning('Container is still running, unable to remove.')
            else:
                container.remove()

    # return an array of None's equal to number of entries in the girder_result_hooks
    # header, in order to trigger processing of the container outputs.
    results = []
    if hasattr(task.request, 'girder_result_hooks'):
        results = (None,) * len(task.request.girder_result_hooks)
    return results

@app.task(base=DockerTask, bind=True)
def docker_run(task, image, pull_image=True, entrypoint=None, container_args=None,
               volumes=None, remove_container=True, **kwargs):
    """
    This task runs a docker container. For details on how to use this task, see the
    :ref:`docker-run` guide.

    :param task: The bound task reference.
    :type task: :py:class:`girder_worker.task.Task`
    :param image: The docker image identifier.
    :type image: str
    :param pull_image: Whether to explicitly pull the image prior to running the container.
    :type pull_image: bool
    :param entrypoint: Alternative entrypoint to use when running the container.
    :type entrypoint: str
    :param container_args: Arguments to pass to the container.
    :type container_args: list
    :param volumes: Volumes to expose to the container.
    :type volumes: dict
    :param remove_container: Whether to delete the container after the task is done.
    :type remove_container: bool
    :return: Fulfilled result hooks.
    :rtype: list
    """
    return _docker_run(
        task, image, pull_image, entrypoint, container_args, volumes,
        remove_container, **kwargs)


#Class for SingularityTask similar to DockerTask
class SingularityTask(Task):
    def _maybe_transform_argument(self, arg):
        return super()._maybe_transform_argument(
            arg, task=self, _default_temp_volume=self.request._default_temp_volume)
     
    def _maybe_transform_result(self, idx, result):
        return super()._maybe_transform_result(
            idx, result, _default_temp_volume=self.request._default_temp_volume)
    
    def __call__(self, *args, **kwargs):
        default_temp_volume = _RequestDefaultTemporaryVolume()
        self.request._default_temp_volume = default_temp_volume

        volumes = kwargs.setdefault('volumes', {})
        # If we have a list of volumes, the user provide a list of Volume objects,
        # we need to transform them.
        temp_volumes = []
        if isinstance(volumes, list):
            # See if we have been passed any TemporaryVolume instances.
            for v in volumes:
                if isinstance(v, TemporaryVolume):
                    temp_volumes.append(v)

            # First call the transform method, this we replace default temp volumes
            # with the instance associated with this task create above. That is any
            # reference to TemporaryVolume.default
            _walk_obj(volumes, self._maybe_transform_argument)

            # Now convert them to JSON
            def _json(volume):
                return volume._repr_json_()

            volumes = _walk_obj(volumes, _json)
            # We then need to merge them into a single dict and it will be ready
            # for docker-py.
            volumes = {k: v for volume in volumes for k, v in volume.items()}
            kwargs['volumes'] = volumes

        volumes.update(default_temp_volume._repr_json_())
        try:
            super().__call__(*args, **kwargs)
        finally:
            threading.Thread(
                target=self._cleanup_temp_volumes,
                args=(temp_volumes, default_temp_volume),
                daemon=False).start()

    def _cleanup_temp_volumes(self, temp_volumes, default_temp_volume):
        # Set the permission to allow cleanup of temp directories
        temp_volumes = [v for v in temp_volumes if os.path.exists(v.host_path)]
        if default_temp_volume._transformed:
            temp_volumes.append(default_temp_volume)
        
        # for v in temp_volumes:
        #     utils.remove_tmp_folder_apptainer(v.host_path)
        


def _run_singularity_container(container_args=None,**kwargs):
    image = kwargs['image']
    container_args = container_args or kwargs['container_args'] or []
    try:
        container_args = _process_container_args(container_args, kwargs)
    
        logger.info('Running container: image: %s args: %s kwargs: %s'
                    % (image, container_args, kwargs))
        
        slurm_run_command = _generate_slurm_script(container_args,kwargs)

        slurm_config = _get_slurm_config(kwargs)

        return [slurm_run_command,slurm_config]
    except Exception as e:
        logger.exception(e)
        raise Exception(e)

    
    

def singularity_run(task,**kwargs):
    volumes = kwargs.pop('volumes',{})
    container_args = kwargs.pop('container_args',[])
    stream_connectors = kwargs['stream_connectors'] or []
    image = kwargs.get('image') or ''
    entrypoint = None
    if not image:
        logger.exception(f"Image name cannot be empty")
        raise Exception(f"Image name cannot be empty")
    
    run_kwargs = {
        'tty': False,
        'volumes': volumes
    }

      # Allow run args to be overridden,filter out any we don't want to override
    extra_run_kwargs = {k: v for k, v in kwargs.items() if k not in BLACKLISTED_DOCKER_RUN_ARGS}
    run_kwargs.update(extra_run_kwargs)

    #Make entrypoint as pwd
    if entrypoint is not None:
        run_kwargs['entrypoint'] = entrypoint
    
    log_file_name = kwargs['log_file']
    
    container_args,read_streams,write_streams = _handle_streaming_args(container_args)
    #MODIFIED FOR SINGULARITY (CHANGE CODE OF SINGULARITY CONTAINER)
    slurm_run_command,slurm_config = _run_singularity_container(container_args,**run_kwargs)
    for connector in stream_connectors:
        if isinstance(connector, FDReadStreamConnector):
            read_streams.append(connector)
        elif isinstance(connector, FDWriteStreamConnector):
            write_streams.append(connector)
        else:
            raise TypeError(
                "Expected 'FDReadStreamConnector' or 'FDWriterStreamConnector', received '%s'"
                % type(connector))
    try:
        monitor_thread = _monitor_singularity_job(task,slurm_run_command,slurm_config,log_file_name)
        def singularity_exit_condition():
            '''
            This function is used to handle task cancellation and also enable exit condition to stop logging. 
            '''
            #Check if the cancel event is called and the jobId is set for the current job thread we are intending to cancel. 
            if task.canceled and monitor_thread.jobId:
                try:
                    returnCode = subprocess.call(utils.apptainer_cancel_cmd(monitor_thread.jobId))
                    if returnCode != 0:
                        raise Exception(f"Failed to Cancel job with jobID {monitor_thread.jobId}")
                except Exception as e:
                    logger.info(f'Error Occured {e}')
            return not monitor_thread.is_alive()
        utils.select_loop(exit_condition = singularity_exit_condition,
                          readers= read_streams,
                          writers = write_streams )
    finally:
        logger.info('DONE')
        utils.remove_tmp_folder_apptainer(container_args)

    results = []
    if hasattr(task.request,'girder_result_hooks'):
        results = (None,) * len(task.request.girder_result_hooks)
    return results
#This function is used to check whether we need to switch to singularity or not.
def use_singularity():
        '''
        #This needs to be uncommented. Only for testing purposes. 
        '''
    # runtime = os.environ.get('RUNTIME')
    # if runtime == 'SINGULARITY':
    #     return True
    # if runtime == 'DOCKER':
    #     return False
    # try:
    #     #Check whether we are connected to a docker socket.
    #     with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
    #         return s.connect_ex('/var/run/docker.sock') != 0
    # except socket.error:
        return True
    
def _generate_slurm_script(container_args,kwargs):
    container_args = container_args or []
    image = kwargs.pop('image',None)
    singularity_command = []
    if not image:
        raise Exception(' Issue with Slicer_Cli_Plugin_Image. Plugin Not available')
    SIF_DIRECTORY = os.getenv('SIF_IMAGE_PATH')
    image_full_path = os.path.join(SIF_DIRECTORY,image)
    #Code to check for allocating multiple gpus. 
    try:
        gpu_index = container_args.index('--gpu')
        gpus = int(container_args[gpu_index+1])
        nvidia.set_nvidia_params(kwargs,singularity_command,gpus)
    except ValueError as e:
        if kwargs['nvidia']:
            nvidia.set_nvidia_params(kwargs,singularity_command)
    try: 
        pwd = kwargs['pwd'] 
        if not pwd:
            raise Exception("PWD cannot be empty")
        singularity_command.append('--cleanenv')
        singularity_command.extend(['--home', os.getenv('TMPDIR','/tmp')])
        singularity_command.extend(['--pwd',pwd])
        singularity_command.append(image_full_path)
        singularity_command.extend(container_args)
    except Exception as e:
        logger.info(f"Error occured - {e}")
        raise Exception(f"Error Occured - {e}")
    logger.info(f"Singularity Command = {singularity_command}")
    return singularity_command

def _monitor_singularity_job(task,slurm_run_command,slurm_config,log_file_name):
    """Create a drmaa session and monitor the job accordingly"""
    decodestatus = {drmaa.JobState.UNDETERMINED: 'process status cannot be determined',
                        drmaa.JobState.QUEUED_ACTIVE: 'job is queued and active',
                        drmaa.JobState.SYSTEM_ON_HOLD: 'job is queued and in system hold',
                        drmaa.JobState.USER_ON_HOLD: 'job is queued and in user hold',
                        drmaa.JobState.USER_SYSTEM_ON_HOLD: 'job is queued and in user and system hold',
                        drmaa.JobState.RUNNING: 'job is running',
                        drmaa.JobState.SYSTEM_SUSPENDED: 'job is system suspended',
                        drmaa.JobState.USER_SUSPENDED: 'job is user suspended',
                        drmaa.JobState.DONE: 'job finished normally',
                        drmaa.JobState.FAILED: 'job finished, but failed'}
    temp_directory = os.getenv('TMPDIR')
    submit_dir = '/blue/pinaki.sarder/rc-svc-pinaki.sarder-web/submission'
    def job_monitor():
        s = drmaa.Session()
        s.initialize()
        jt = s.createJobTemplate()
        jt.workingDirectory = temp_directory
        jt.remoteCommand = os.path.join(submit_dir , 'submit.sh')
        jt.nativeSpecification = slurm_config
        jt.args = slurm_run_command
        jt.outputPath = ':' + log_file_name
        jt.errorPath = ':' + log_file_name
        try:
            jobid = s.runJob(jt)
            #Set the jobID for the current thread so we can access it outside this thread incase we need to cancel the job. 
            threading.current_thread().jobId = jobid
            logger.info((f'Submitted singularity job with jobid {jobid}'))
            with open(log_file_name,'r') as f:
                s.deleteJobTemplate(jt)
                while True:
                    job_info = s.jobStatus(jobid)
                    where = f.tell()
                    line = f.readlines()
                    if line:
                        print(''.join(line),end='')
                    else:
                        f.seek(where)
                    if job_info in [drmaa.JobState.DONE, drmaa.JobState.FAILED]:
                        break
                    
                    time.sleep(5)  # Sleep to avoid busy waiting
            exit_status = s.jobStatus(jobid)
            logger.info(decodestatus[exit_status])
            s.exit()
            return exit_status
            
            
        except Exception as e: 
            s.deleteJobTemplate(jt)
            print(f"Error Occured {e}")
            
            

    # Start the job monitor in a new thread
    monitor_thread = utils.SingularityThread(target=job_monitor,daemon=False)
    monitor_thread.start()

    return monitor_thread


def _process_container_args(container_args,kwargs):
    volumes = kwargs['volumes'] or {}
    def find_matching_volume_key(path):
        for key, value in volumes.items():
            if path.startswith(value['bind']):
                # Append the suffix from the original path that isn't part of the 'bind' path 
                suffix = path[len(value['bind']):] if value['bind'] != path else ''
                if 'assetstore' in key:
                    key = '/blue/pinaki.sarder/rc-svc-pinaki.sarder-web' + key
                new_key = key + suffix.replace(" ", "_")  # Replace spaces in suffix with underscores
                return new_key
        return path  # Replace spaces in paths that don't match any volume
    try:
    # Replace paths in container_args with their corresponding volume keys
        updated_container_args = [str(find_matching_volume_key(arg)) for arg in container_args]
    except Exception as e:
        logger.info(f"error {e}")
    return updated_container_args
        
def _get_slurm_config(kwargs):
    #Use this function to add or modify any configuration parameters for the SLURM job
    config_defaults = {
        '--qos': os.getenv('SLURM_QOS'),
        '--account': os.getenv('SLURM_ACCOUNT'),
        '--mem':os.getenv('SLURM_MEMORY','16000'),
        '--ntasks': os.getenv("SLURM_NTASKS",'1'),
        '--time': os.getenv("SLURM_TIME",'72:00'),
        '--partition':os.getenv('SLURM_PARTITION','hpg2-compute'),
        '--gres':os.getenv('SLURM_GRES_CONFIG'),
        '--cpus-per-task':os.getenv('SLURM_CPUS','4'),
        '--exclude':'c0906a-s17'
    }

    config = {k:kwargs.get(k,config_defaults[k]) for k in config_defaults}

    slurm_config = ' '.join(f"{k}={v}" for k,v in config.items() if v is not None)

    logger.info(f"SLURM CONFIG = {slurm_config}")
    return slurm_config
    
