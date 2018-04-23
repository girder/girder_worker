from .app import app


def main():
    app.worker_main()


if __name__ == '__main__':
    main()
