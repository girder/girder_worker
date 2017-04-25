from girder.api import access
from girder.api.describe import Description, describeRoute
from girder.api.rest import Resource, filtermodel

class Fib(Resource):
    def __init__(self):
        super(Fib, self).__init__()
        self.resourceName = 'fib'

        self.route('POST', (), self.run_fib_sequence)
        self.route('POST', ('gwrun', ), self.run_gw_task)
        self.route('POST', ('gwdocker', ), self.run_docker_task)

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Fire off a a fibonacci sequence job')
        .param('number', 'The upper bound of the fibonacci sequence',
               dataType='integer')
    )
    def run_fib_sequence(self, params):
        number = int(params.get('number', 10))
        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='Fib_Seq', type='worker', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(number,), kwargs={},
            otherFields={
                'celeryTaskName': 'gwexample.analyses.tasks.fib_seq'
            })

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Fire off a girder_worker.run job')
    )
    def run_gw_task(self, params):
        analysis = {
            'name': 'add',
            'inputs': [
                {
                    'name': 'a',
                    'type': 'integer',
                    'format': 'integer',
                    'default': {
                        'format': 'json',
                        'data': '0'
                    }
                },
                {
                    'name': 'b',
                    'type': 'integer',
                    'format': 'integer'
                }
            ],
            'outputs': [{'name': 'c', 'type': 'integer', 'format': 'integer'}],
            'script': 'c = a + b',
            'mode': 'python'}

        inputs={'a': {'format': 'integer', 'data': 1},
                'b': {'format': 'integer', 'data': 2}}

        outputs={'c': {'format': 'integer'}}


        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='GW_run', type='worker', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(analysis,),
            kwargs={'inputs': inputs, 'outputs': outputs})

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job

    @access.token
    @filtermodel(model='job', plugin='jobs')
    @describeRoute(
        Description('Fire off a docker job')
    )
    def run_docker_task(self, params):
        test_image = 'girder/girder_worker_test:latest'
        task = {
            'mode': 'docker',
            'docker_image': test_image,
            'pull_image': True,
            'container_args': ['$input{test_mode}', '$input{message}'],
            'inputs': [{
                'id': 'test_mode',
                'name': '',
                'format': 'string',
                'type': 'string'
            }, {
                'id': 'message',
                'name': '',
                'format': 'string',
                'type': 'string'
            }],
            'outputs': []
        }

        inputs = {
            'test_mode': {
                'format': 'string',
                'data': 'stdio'
            },
            'message': {
                'format': 'string',
                'data': "Hello from girder_worker docker test!"
            }
        }
        outputs = []

        jobModel = self.model('job', 'jobs')
        job = jobModel.createJob(
            title='GW_docker', type='worker', handler='worker_handler',
            user=self.getCurrentUser(), public=False, args=(task,),
            kwargs={'inputs': inputs, 'outputs': outputs})

        jobModel.save(job)
        jobModel.scheduleJob(job)

        return job


def load(info):
    info['apiRoot'].fib = Fib()
