def is_nvidia_image(api, image):
    labels = api.inspect_image(image).get('Config', {}).get('Labels')
    return bool(labels and labels.get('com.nvidia.volumes.needed') == 'nvidia_driver')


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
    kwargs['--gres'] = f'gres:gpu:a100:{gpus}' if gpus > 1 else f'gres:gpu:a100:1'
    kwargs['--partition'] = 'gpu'
    kwargs['--mem'] = '32000'
    # Reducing CPU count for gpu-based job for resource conservation
    kwargs['--cpus-per-task'] = '8'
    singularity_command.append('--nv')
