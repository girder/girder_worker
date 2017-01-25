import subprocess


def before_run(e):
    import executor
    if e.info['task']['mode'] == 'docker':
        executor.validate_task_outputs(e.info['task_outputs'])


def cleanup(e):
    """
    Since files written by docker containers are owned by root, we can't
    clean them up in the worker process since that typically doesn't run
    as root. So, we run a lightweight container to clean up the temp dir.
    """
    from .executor import DATA_VOLUME
    if e.info['task']['mode'] == 'docker' and '_tempdir' in e.info['kwargs']:
        tmpdir = e.info['kwargs']['_tempdir']
        cmd = [
            'docker', 'run', '--rm', '-v', '%s:%s' % (tmpdir, DATA_VOLUME),
            'busybox', 'rm', '-rf', '%s/*' % DATA_VOLUME
        ]
        p = subprocess.Popen(args=cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate()
        if p.returncode:
            print('Error cleaning docker tmpdir %s.' % tmpdir)
            print('STDOUT: ' + out)
            print('STDERR: ' + err)
            raise Exception('Docker tempdir cleanup returned code %d.' % p.returncode)


def load(params):
    from girder_worker.core import events, register_executor
    import executor

    events.bind('run.before', params['name'], before_run)
    events.bind('run.finally', params['name'], cleanup)
    register_executor('docker', executor.run)
