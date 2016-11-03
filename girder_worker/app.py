import girder_worker
from celery import Celery


class _CeleryConfig:
    CELERY_ACCEPT_CONTENT = ['json', 'pickle', 'yaml']

app = Celery(
    main=girder_worker.config.get('celery', 'app_main'),
    backend=girder_worker.config.get('celery', 'broker'),
    broker=girder_worker.config.get('celery', 'broker'))

app.config_from_object(_CeleryConfig)
