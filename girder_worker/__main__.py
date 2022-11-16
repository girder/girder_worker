import sys

from .app import app


def main():
    app.worker_main(argv=['worker'] + sys.argv[1:])


if __name__ == '__main__':
    main()
