import pkg_resources as pr
from girder_worker import app


def main():
    includes = []
    for ep in pr.iter_entry_points(group='girder_worker.tasks'):
        module = ep.load()
        includes.append(module.__name__)

    app.conf.update({
        'CELERY_IMPORTS': includes
    })
    app.worker_main()


if __name__ == '__main__':
    main()
