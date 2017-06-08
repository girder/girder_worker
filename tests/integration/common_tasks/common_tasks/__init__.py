from girder_worker import GirderWorkerPluginABC


class CommonTasksPlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app

        # Note: within the context of the executing docker test
        # environment the RabbitMQ server is addressable as 'rabbit.'
        # Usually we statically configure the broker url in
        # worker.local.cfg or fall back to worker.dist.cfg.  In this
        # case however we are mounting the local girder_worker
        # checkout inside the docker containers and don't want to
        # surprise users by programatically modifying their
        # configuration from the docker container's entrypoint. To
        # solve this we set the broker URL for the girder_worker app
        # inside the girder_worker container here.

        self.app.conf.update({
            'broker_url': 'amqp://guest:guest@rabbit/'
        })

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['common_tasks.test_tasks.fib',
                'common_tasks.test_tasks.fail']
