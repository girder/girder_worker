import os
import shutil
import subprocess
import tempfile
import time
from girder_worker import config, logger
from girder_worker.docker.utils import chmod_writable

# Minimum interval in seconds at which to run the docker-gc script
MIN_GC_INTERVAL = 600


def before_run(e):
    import executor
    if e.info['task'].get('mode') == 'docker':
        executor.validate_task_outputs(e.info['task_outputs'])
    if not _read_bool_from_config('gc', False):
        e.info.setdefault('kwargs', {})['_rm_container'] = True


def _read_from_config(key, default):
    """
    Helper to read Docker specific config values from the worker config files.
    """
    if config.has_option('docker', key):
        return config.get('docker', key)
    else:
        return default


def _read_bool_from_config(key, default):
    """
    Helper to read Docker specific bool config values from the worker config files.
    """
    if config.has_option('docker', key):
        return config.getboolean('docker', key)
    else:
        return default


def docker_gc(e):
    """
    Garbage collect containers that have not been run in the last hour using the
    https://github.com/spotify/docker-gc project's script, which is copied in
    the same directory as this file. After that, deletes all images that are
    no longer used by any containers.
    """
    if not _read_bool_from_config('gc', False):
        return
    stampfile = os.path.join(config.get('girder_worker', 'tmp_root'), '.dockergcstamp')
    if os.path.exists(stampfile) and time.time() - os.path.getmtime(stampfile) < MIN_GC_INTERVAL:
        return
    else:  # touch the file
        with open(stampfile, 'w') as f:
            f.write('')

    logger.info('Garbage collecting docker containers and images.')
    gc_dir = tempfile.mkdtemp()

    try:
        script = os.path.join(os.path.dirname(__file__), 'docker-gc')
        if not os.path.isfile(script):
            raise Exception('Docker GC script %s not found.' % script)
        if not os.access(script, os.X_OK):
            raise Exception('Docker GC script %s is not executable.' % script)

        env = os.environ.copy()
        env['FORCE_CONTAINER_REMOVAL'] = '1'
        env['STATE_DIR'] = gc_dir
        env['PID_DIR'] = gc_dir
        env['GRACE_PERIOD_SECONDS'] = str(_read_from_config('cache_timeout', 3600))

        # Handle excluded images
        excluded = _read_from_config('exclude_images', '').split(',')
        excluded = [img for img in excluded if img.strip()]
        if excluded:
            exclude_file = os.path.join(gc_dir, '.docker-gc-exclude')
            with open(exclude_file, 'w') as fd:
                fd.write('\n'.join(excluded) + '\n')
            env['EXCLUDE_FROM_GC'] = exclude_file

        p = subprocess.Popen(args=(script,), env=env)
        p.wait()  # Wait for garbage collection subprocess to finish

        if p.returncode != 0:
            raise Exception('Docker GC returned code %d.' % p.returncode)
    finally:
        shutil.rmtree(gc_dir)


def task_cleanup(e):
    """
    Since files written by docker containers are owned by root, we can't
    clean them up in the worker process since that typically doesn't run
    as root. So, we run a lightweight container to make the temp dir cleanable.
    """
    if e.info['task']['mode'] == 'docker' and '_tempdir' in e.info['kwargs']:
        tmpdir = e.info['kwargs']['_tempdir']
        chmod_writable(tmpdir)


def load(params):
    from girder_worker.core import events, register_executor
    import executor

    events.bind('run.before', params['name'], before_run)
    events.bind('run.finally', params['name'], task_cleanup)
    events.bind('cleanup', params['name'], docker_gc)
    register_executor('docker', executor.run)
