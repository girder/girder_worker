import os
import re
import subprocess

from girder_worker import logger


# TODO: this looks janky, idk why we need this?
def remove_tmp_folder_apptainer(container_args=[]):
    """
    This function will run after the slurm job completes and returns. If a temp folder is created
    in the temp directory to do file I/O operations before/while the job was run, we need to
    clean up by removing the folder.
    """
    if not container_args:
        logger.info('Host path not found.')
    # Cautious checking host path before removing it from the filesystem.
    pattern = r'\/tmp\/tmp[^/]+'
    for arg in container_args:
        if re.search(pattern, arg):
            if os.path.exists(arg):
                subprocess.call(['rm', '-rf', arg])
                return
