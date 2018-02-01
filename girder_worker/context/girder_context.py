from girder_worker.task import Task
from girder_worker.utils import _maybe_model_repr
from girder_worker_utils import _walk_obj


def create_task_job(sender=None, body=None, exchange=None,
                    routing_key=None, headers=None, properties=None,
                    declare=None, retry_policy=None, **kwargs):

    from girder.utility.model_importer import ModelImporter
    from girder.plugins.worker import utils
    from girder.api.rest import getCurrentUser

    job_model = ModelImporter.model('job', 'jobs')

    user = headers.pop('girder_user', getCurrentUser())

    # Sanitize any Transform objects
    task_args = tuple(_walk_obj(body[0], _maybe_model_repr))
    task_kwargs = _walk_obj(body[1], _maybe_model_repr)

    job = job_model.createJob(
        **{'title': headers.pop('girder_job_title',
                                Task._girder_job_title),
           'type': headers.pop('girder_job_type',
                               Task._girder_job_type),
           'handler': headers.pop('girder_job_handler',
                                  Task._girder_job_handler),
           'public': headers.pop('girder_job_public',
                                 Task._girder_job_public),
           'user': user,
           'args': task_args,
           'kwargs': task_kwargs,
           'otherFields': dict(
               celeryTaskId=headers['id'],
               **headers.pop('girder_job_other_fields',
                             Task._girder_job_other_fields))})

    headers['jobInfoSpec'] = utils.jobInfoSpec(job)


def attach_girder_api_url(sender=None, body=None, exchange=None,
                          routing_key=None, headers=None, properties=None,
                          declare=None, retry_policy=None, **kwargs):
    from girder.plugins.worker import utils
    headers['girder_api_url'] = utils.getWorkerApiUrl()


def attach_girder_client_token(sender=None, body=None, exchange=None,
                               routing_key=None, headers=None, properties=None,
                               declare=None, retry_policy=None, **kwargs):
    from girder.utility.model_importer import ModelImporter
    from girder.api.rest import getCurrentUser
    token_model = ModelImporter.model('token')
    scope = 'jobs.rest.create_job'
    try:
        token = token_model.createToken(scope=scope, user=user)
    except NameError:
        token = token_model.createToken(scope=scope, user=getCurrentUser())
    headers['girder_client_token'] = token['_id']
