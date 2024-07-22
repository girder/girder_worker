import drmaa
import time
import threading
import os
from girder_worker.docker import utils
from girder_worker import logger

try:
    from girder_worker.docker import nvidia
except ImportError:
    pass


def slurm_dispatch(task, container_args, run_kwargs, read_streams, write_streams, log_file_name):
    slurm_run_command,slurm_config = _run_singularity_container(container_args,**run_kwargs)
    try:
        monitor_thread = _monitor_singularity_job(task,slurm_run_command,slurm_config,log_file_name)
        def singularity_exit_condition():
            return not monitor_thread.is_alive()
        utils.select_loop(exit_condition=singularity_exit_condition,
                          readers=read_streams,
                          writers=write_streams)
    finally:
        logger.info('DONE')


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
        jt.remoteCommand = os.path.join(submit_dir, 'submit.sh')
        jt.nativeSpecification = slurm_config
        jt.args = slurm_run_command
        jt.outputPath = ':' + log_file_name
        jt.errorPath = ':' + log_file_name
        try:
            jobid = s.runJob(jt)
            logger.info((f'Submitted singularity job with jobid {jobid}'))
            with open(log_file_name, 'r') as f:
                while True:
                    job_info = s.jobStatus(jobid)
                    where = f.tell()
                    line = f.readlines()
                    if line:
                        print(''.join(line), end='')
                    else:
                        f.seek(where)
                    if job_info in [drmaa.JobState.DONE, drmaa.JobState.FAILED]:
                        s.deleteJobTemplate(jt)
                        break
                    elif task.canceled:
                        s.control(jobid, drmaa.JobControlAction.TERMINATE)
                        s.deleteJobTemplate(jt)
                        break
                    time.sleep(5)  # Sleep to avoid busy waiting
            exit_status = s.jobStatus(jobid)
            logger.info(decodestatus[exit_status])
            s.exit()
            return exit_status

        except Exception as e:
            s.deleteJobTemplate(jt)
            print(f'Error Occured {e}')

    # Start the job monitor in a new thread
    monitor_thread = threading.Thread(target=job_monitor, daemon=True)
    monitor_thread.start()

    return monitor_thread


def _run_singularity_container(container_args=None,**kwargs):
    image = kwargs['image']
    container_args = container_args or kwargs['container_args'] or []
    try:
        container_args = _process_container_args(container_args, kwargs)

        logger.info('Running container: image: %s args: %s kwargs: %s'
                    % (image, container_args, kwargs))

        slurm_run_command = _generate_slurm_script(container_args,kwargs)

        slurm_config = _get_slurm_config(kwargs)

        return [slurm_run_command, slurm_config]
    except Exception as e:
        logger.exception(e)
        raise Exception(e)


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


def _generate_slurm_script(container_args, kwargs):
    container_args = container_args or []
    image = kwargs.pop('image', None)
    singularity_command = []
    if not image:
        raise Exception(' Issue with Slicer_Cli_Plugin_Image. Plugin Not available')
    SIF_DIRECTORY = os.getenv('SIF_IMAGE_PATH')
    image_full_path = os.path.join(SIF_DIRECTORY, image)
    #Code to check for allocating multiple gpus.
    try:
        gpu_index = container_args.index('--gpu')
        gpus = int(container_args[gpu_index+1])
        nvidia.set_nvidia_params(kwargs, singularity_command, gpus)
    except ValueError as e:
        if kwargs['nvidia']:
            nvidia.set_nvidia_params(kwargs, singularity_command)
    try:
        pwd = kwargs['pwd']
        if not pwd:
            raise Exception("PWD cannot be empty")
        singularity_command.extend(['--pwd', pwd])
        singularity_command.append(image_full_path)
        singularity_command.extend(container_args)
    except Exception as e:
        logger.info(f"Error occured - {e}")
        raise Exception(f"Error Occured - {e}")
    return singularity_command


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
        '--cpus-per-task':os.getenv('SLURM_CPUS','4')
    }

    config = {k:kwargs.get(k,config_defaults[k]) for k in config_defaults}

    slurm_config = ' '.join(f"{k}={v}" for k,v in config.items() if v is not None)

    logger.info(f"SLURM CONFIG = {slurm_config}")
    return slurm_config
