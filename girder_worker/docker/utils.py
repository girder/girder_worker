from types import SimpleNamespace
import select
import uuid
import os
import docker
from docker.errors import DockerException
from girder_worker import logger
import re
import subprocess
import threading

def select_loop(exit_condition=lambda: True, readers=None, writers=None):
    """
    Run a select loop for a set of readers and writers

    :param exit_condition: A function to evaluate to determine if the select
        loop should terminate if all pipes are empty.
    :type exit_condition: function
    :param readers: The list of ReaderStreamConnector's that will be added to the
        select call.
    :type readers: list
    :param writers: The list of WriteStreamConnector's that will be added to the
        select call.
    :type writers: list
    """

    BUF_LEN = 65536

    try:
        while True:
            # We evaluate this first so that we get one last iteration of
            # of the loop before breaking out of the loop.
            exit = exit_condition()

            open_writers = [writer for writer in writers if writer.fileno() is not None]

            # get ready pipes, timeout of 100 ms
            readable, writable, _ = select.select(readers, open_writers, (), 0.1)

            for ready in readable:
                read = ready.read(BUF_LEN)
                if read == 0:
                    readers.remove(ready)

            for ready in writable:
                # TODO for now it's OK for the input reads to block since
                # input generally happens first, but we should consider how to
                # support non-blocking stream inputs in the future.
                written = ready.write(BUF_LEN)
                if written == 0:
                    writers.remove(ready)

            need_opening = [writer for writer in writers if writer.fileno() is None]
            for connector in need_opening:
                connector.open()

            # all pipes empty?
            empty = (not readers or not readable) and (not writers or not writable)

            if (empty and exit):
                break

    finally:
        for stream in readers + writers:
            stream.close()


CONTAINER_PATH = '/mnt/girder_worker/data'


def chmod_writable(host_paths):
    """
    Since files written by docker containers are owned by root, we can't
    clean them up in the worker process since that typically doesn't run
    as root. So, we run a lightweight container to make the temp dir cleanable.
    """
    if not isinstance(host_paths, (list, tuple)):
        host_paths = (host_paths,)

    if 'DOCKER_CLIENT_TIMEOUT' in os.environ:
        timeout = int(os.environ['DOCKER_CLIENT_TIMEOUT'])
        client = docker.from_env(version='auto', timeout=timeout)
    else:
        client = docker.from_env(version='auto')

    config = {
        'tty': True,
        'volumes': {},
        'detach': False,
        'remove': True
    }

    container_paths = []
    for host_path in host_paths:
        container_path = os.path.join(CONTAINER_PATH, uuid.uuid4().hex)
        container_paths.append(container_path)
        config['volumes'][host_path] = {
            'bind': container_path,
            'mode': 'rw'
        }

    args = ['chmod', '-R', 'a+rw'] + container_paths

    try:
        client.containers.run('busybox:latest', args, **config)
    except DockerException:
        logger.exception('Error setting perms on docker volumes %s.' % host_paths)
        raise


def remove_tmp_folder_apptainer(container_args=[]):
    '''
    This function will run after the slurm job completes and returns. If a temp folder is created in the temp directory to 
    do file I/O operations before/while the job was run, we need to clean up by removing the folder. 
    '''
    if not container_args:
        logger.info("Host path not found. ")
        return
    #Cautious checking host path before removing it from the filesystem.  
    pattern = r"\/tmp\/tmp[^/]+"
    for arg in container_args:
        if re.search(pattern,arg):
            if os.path.exists(arg):
                subprocess.call(['rm','-rf',arg])
                return

class SingularityThread(threading.Thread):
    '''
    This is a custom Thread class in order to handle cancelling a slurm job outside of the thread since the task context object is not available inside the thread.
    Methods:

    __init__(self,target, daemon) - Initialize the thread similar to threading.Thread class, requires a jobId param to keep track of the jobId

    run(self) - This method is used to run the target function. This is essentially called when you do thread.start()
    '''
    def __init__(self,target,daemon=False):
        super().__init__(daemon=daemon)
        self.target = target
        self.jobId = None
    
    def run(self):
        if self.target:
            self.target()

def apptainer_cancel_cmd(jobID,slurm=True):
    if not jobID:
        raise Exception("Please provide jobID for the job that needs to be cancelled")
    cmd = []
    #If any other type of mechanism is used to interact with HPG, use that. 
    if slurm:
        cmd.append('scancel')
    cmd.append(jobID)
    return cmd


