from girder_worker import GirderWorkerPluginABC


class GWExamplePlugin(GirderWorkerPluginABC):
    def __init__(self, app, *args, **kwargs):
        self.app = app
        # Here we can also change application settings. E.g.
        # changing the task time limit:
        #
        # self.app.config.update({
        #     'TASK_TIME_LIMIT': 300
        # })

    def task_imports(self):
        # Return a list of python importable paths to the
        # plugin's path directory
        return ['gwexample.analyses.tasks']
