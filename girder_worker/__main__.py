from .app import app


def main():
    app.conf.update({
        'CELERY_IMPORTS': [
            'girder_worker.tasks'
        ]})

    app.worker_main()

if __name__ == '__main__':
    main()
