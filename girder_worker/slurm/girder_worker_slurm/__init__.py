import os
import subprocess
import threading
import time

from girder.models.setting import Setting
from girder_worker_singularity.tasks.utils import remove_tmp_folder_apptainer

from girder_worker import logger
from girder_worker.docker import utils

from .girder_plugin import PluginSettings


def slurm_dispatch(task, container_args, run_kwargs, read_streams, write_streams, log_file_name):
    singularity_run_command, slurm_config = _slurm_singularity_config(container_args, **run_kwargs)
    try:
        monitor_thread = _monitor_singularity_job(
            task, singularity_run_command, slurm_config, log_file_name)

        def singularity_exit_condition():
            # Check if the cancel event is called and the job_id is set for the current
            # job thread we are intending to cancel.
            if task.canceled and monitor_thread.job_id:
                try:
                    returnCode = subprocess.call(['scancel', monitor_thread.job_id])
                    if returnCode != 0:
                        raise Exception(f'Failed to Cancel job with jobID {monitor_thread.job_id}')
                except Exception as e:
                    logger.info(f'Error Occured {e}')
            return not monitor_thread.is_alive()

        utils.select_loop(exit_condition=singularity_exit_condition,
                          readers=read_streams,
                          writers=write_streams)
    finally:
        logger.info('DONE')
        remove_tmp_folder_apptainer(container_args)


def _monitor_singularity_job(task, slurm_command, slurm_config, log_file_name):
    # decodestatus = {drmaa.JobState.UNDETERMINED: 'process status cannot be determined',
    #                 drmaa.JobState.QUEUED_ACTIVE: 'job is queued and active',
    #                 drmaa.JobState.SYSTEM_ON_HOLD: 'job is queued and in system hold',
    #                 drmaa.JobState.USER_ON_HOLD: 'job is queued and in user hold',
    #                 drmaa.JobState.USER_SYSTEM_ON_HOLD: 'job is queued and in user and system hold',
    #                 drmaa.JobState.RUNNING: 'job is running',
    #                 drmaa.JobState.SYSTEM_SUSPENDED: 'job is system suspended',
    #                 drmaa.JobState.USER_SUSPENDED: 'job is user suspended',
    #                 drmaa.JobState.DONE: 'job finished normally',
    #                 drmaa.JobState.FAILED: 'job finished, but failed'}
    temp_directory = os.getenv('TMPDIR')
    submit_script = os.getenv('GIRDER_WORKER_SLURM_SUBMIT_SCRIPT')
    # TODO: check for validity ^

    # def job_monitor():
        # s = drmaa.Session()
        # s.initialize()
        # jt = s.createJobTemplate()
        # jt.workingDirectory = temp_directory
        # jt.remoteCommand = submit_script
        # jt.nativeSpecification = slurm_config
        # jt.args = slurm_command
        # jt.outputPath = ':' + log_file_name
        # jt.errorPath = ':' + log_file_name
        # try:
        #     jobid = s.runJob(jt)
        #     # Set the jobID for the current thread so we can access it outside this
        #     # thread incase we need to cancel the job.
        #     threading.current_thread().jobId = jobid
        #     logger.info((f'Submitted singularity job with jobid {jobid}'))
        #     with open(log_file_name, 'r') as f:
        #         while True:
        #             job_info = s.jobStatus(jobid)
        #             where = f.tell()
        #             line = f.readlines()
        #             if line:
        #                 print(''.join(line), end='')
        #             else:
        #                 f.seek(where)
        #             if job_info in [drmaa.JobState.DONE, drmaa.JobState.FAILED]:
        #                 s.deleteJobTemplate(jt)
        #                 break
        #             elif task.canceled:
        #                 s.control(jobid, drmaa.JobControlAction.TERMINATE)
        #                 s.deleteJobTemplate(jt)
        #                 break
        #             time.sleep(5)  # Sleep to avoid busy waiting
        #     exit_status = s.jobStatus(jobid)
        #     logger.info(decodestatus[exit_status])
        #     s.exit()
        #     return exit_status

        # except Exception as e:
        #     s.deleteJobTemplate(jt)
        #     print(f'Error Occured {e}')

    def get_status(job_id):
        process = subprocess.run(['scontrol', 'show', 'job', job_id], capture_output=True)
        if process.returncode != 0:
            logger.error(f'Failed to get job status with error code {process.returncode}')
            return 'INVALID'

        result = process.stdout.decode('utf-8')
        if 'JobState' not in result:
            logger.error(f'Expected JobState, got: `{result}`')
            return 'INVALID'

        values = result.split()
        for value in values:
            if 'JobState' in value:
                return value.split('=')[-1]

        return 'INVALID'

    def job_monitor():
        # TODO: apply slurm_config to submit_command (probably use some list comprehension)
        submit_command = ['sbatch', f'--error={log_file_name}', f'--output={log_file_name}', submit_script]
        submit_command.extend(slurm_command)

        try:
            # Submit the job to the HPC
            print('running', submit_command)
            process = subprocess.run(submit_command, capture_output=True)
            if process.returncode != 0:
                raise Exception(f'Failed to submit job with error code {process.returncode}')

            sbatch_cli_stdout = process.stdout.decode('utf-8').strip()

            # Expecting output like 'Submitted batch job {job_id}'
            if 'Submitted batch job' not in sbatch_cli_stdout:
                raise Exception(f'Expected job_id, got: `{sbatch_cli_stdout}`')

            job_id = sbatch_cli_stdout.split(' ')[-1]
            logger.info(f'Job submitted with job id {job_id}')

            threading.current_thread().job_id = job_id # TODO: refactor this holdover from UF

            with open(log_file_name, 'r') as log_file:
                while True:
                    lines = log_file.readlines()
                    if lines:
                        print(''.join(lines), end='')

                    status = get_status(job_id)

                    if status in ['COMPLETED', 'FAILED', 'CANCELLED']:
                        logger.info(f'Job finished with status {status}')
                        break

                    if status in ['BOOT_FAIL', 'DEADLINE', 'NODE_FAIL', 'OUT_OF_MEMORY', 'PREEMPTED', 'TIMEOUT']:
                        logger.error(f'Job failed with status {status}')
                        break

                    # # TODO: monitor celery task, if cancelled, cancel slurm job
                    # if task.canceled: # TODO: this condition isn't being caught, is it even needed if we're using singularity_exit_condition() to kill?
                    #     process = subprocess.run(apptainer_cancel_cmd(job_id))
                    #     break

                    time.sleep(10)

        except Exception as e:
            print(f'Error Occured {e}')

    # Start the job monitor in a new thread
    monitor_thread = SingularityThread(target=job_monitor, daemon=True)
    monitor_thread.start()

    return monitor_thread


def _slurm_singularity_config(container_args=None, **kwargs):
    image = kwargs['image']
    container_args = container_args or kwargs['container_args'] or []
    try:
        container_args = _process_container_args(container_args, kwargs)

        logger.info('Running container: image: %s args: %s kwargs: %s'
                    % (image, container_args, kwargs))

        singularity_run_command = _generate_singularity_command(container_args, kwargs)
        slurm_config = _get_slurm_config(kwargs)

        return singularity_run_command, slurm_config
    except Exception as e:
        logger.exception(e)
        raise Exception(e)


def _process_container_args(container_args, kwargs):
    volumes = kwargs['volumes'] or {}
    # '/blue/pinaki.sarder/rc-svc-pinaki.sarder-web'
    prefix = os.getenv('GIRDER_WORKER_SLURM_MOUNT_PREFIX')

    def find_matching_volume_key(path):
        for key, value in volumes.items():
            if path.startswith(value['bind']):
                # Append the suffix from the original path that isn't part of the 'bind' path
                suffix = path[len(value['bind']):] if value['bind'] != path else ''
                if 'assetstore' in key:
                    key = prefix + key
                # Replace spaces in suffix with underscores
                new_key = key + suffix.replace(' ', '_')
                return new_key
        return path  # Replace spaces in paths that don't match any volume
    try:
        # Replace paths in container_args with their corresponding volume keys
        updated_container_args = [str(find_matching_volume_key(arg)) for arg in container_args]
    except Exception as e:
        logger.info(f'error {e}')
    return updated_container_args


def _generate_singularity_command(container_args, kwargs):
    container_args = container_args or []
    image = kwargs.pop('image', None)
    singularity_command = []
    if not image:
        raise Exception(' Issue with Slicer_Cli_Plugin_Image. Plugin Not available')
    SIF_DIRECTORY = os.getenv('SIF_IMAGE_PATH')
    image_full_path = os.path.join(SIF_DIRECTORY, image)
    # Code to check for allocating multiple gpus.
    try:
        gpu_index = container_args.index('--gpu')
        gpus = int(container_args[gpu_index + 1])
        set_nvidia_params(kwargs, singularity_command, gpus)
    except ValueError:
        if kwargs['nvidia']:
            set_nvidia_params(kwargs, singularity_command)
    try:
        pwd = kwargs['pwd']
        if not pwd:
            raise Exception('PWD cannot be empty')
        singularity_command.extend(['--pwd', pwd])

        singularity_command.append('--bind')
        volumes = ''
        for key, value in kwargs.get('volumes').items():
            # TODO: make this robust, currently only works for tmp volume mount
            # TODO: ^ when do things get mounted to docker like this?
            # volumes += f'{value["bind"]}:{key},'
            volumes += f'{key},'
        volumes = volumes[:-1] # remove trailing comma
        singularity_command.append(volumes)

        singularity_command.append(image_full_path)
        # missing docker-entrypoint.sh
        # TODO: revisit girder_worker_singularity/tasks/__init__.py:singularity_run (entrypoint variable)
        singularity_command.append('./docker-entrypoint.sh')
        singularity_command.extend(container_args)
    except Exception as e:
        logger.info(f'Error occured - {e}')
        raise Exception(f'Error Occured - {e}')
    return singularity_command


def _get_slurm_config(kwargs):
    # Use this function to add or modify any configuration parameters for the SLURM job
    config_defaults = {
        # '--qos': Setting().get(PluginSettings.SLURM_QOS),
        # '--account': Setting().get(PluginSettings.SLURM_ACCOUNT),
        # '--mem': Setting().get(PluginSettings.SLURM_MEM),
        '--ntasks': Setting().get(PluginSettings.SLURM_NTASKS),
        # '--time': Setting().get(PluginSettings.SLURM_TIME),
        # '--partition': Setting().get(PluginSettings.SLURM_PARTITION),
        '--gres': Setting().get(PluginSettings.SLURM_GRES_CONFIG),
        # '--cpus-per-task': Setting().get(PluginSettings.SLURM_CPUS)
    }

    config = {k: kwargs.get(k, config_defaults[k]) for k in config_defaults}

    slurm_config = ' '.join(f'{k}={v}' for k, v in config.items() if v is not None)

    logger.info(f'SLURM CONFIG = {slurm_config}')
    return slurm_config


def set_nvidia_params(kwargs: dict, singularity_command: list, gpus: int = 1):
    """
    This function is used to set the gpu parameters based on the user input and plugin job.

    Parameters:
    kwargs (dict, required): The keyword arguments dictionary sent to the celery task as an input,
    part of the request

    singularity_command (list, required): A list that container all the arguments to construct a
    singularity command that will be sent to the HPC job

    gps (int, optional): If the plugin doesn't have a --gpu parameter in contianer_args, then a
    default of 1 gpu is allocated, else the user specified number of gpus is allocated.

    Returns:
    None
    """
    kwargs['--gres'] = f'gres:gpu:a100:{gpus}' if gpus > 1 else 'gres:gpu:a100:1'
    kwargs['--partition'] = Setting().get(PluginSettings.SLURM_GPU_PARTITION)
    # Reducing CPU count for gpu-based job for resource conservation
    # kwargs['--cpus-per-task'] = '8'
    singularity_command.append('--nv')


class SingularityThread(threading.Thread):
    """
    This is a custom Thread class in order to handle cancelling a slurm job outside of the thread
    since the task context object is not available inside the thread.
    Methods:
    __init__(self,target, daemon) - Initialize the thread similar to threading. Thread class,
                                    requires a job_id param to keep track of the job_id
    run(self) - This method is used to run the target function. This is essentially called when
                you do thread.start()
    """

    def __init__(self, target, daemon=False):
        super().__init__(daemon=daemon)
        self.target = target
        self.job_id = None

    def run(self):
        if self.target:
            self.target()
