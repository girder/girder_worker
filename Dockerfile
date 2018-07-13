FROM ubuntu:xenial as base

RUN apt-get update && \
  apt-get install -qy software-properties-common python-software-properties && \
  apt-get update && apt-get install -qy \
    build-essential \
    wget \
    python \
    r-base \
    libffi-dev \
    libssl-dev \
    libjpeg-dev \
    zlib1g-dev \
    libpython-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py


FROM base as build

RUN apt-get update && apt-get install -qy git

COPY ./ /girder_worker/
WORKDIR /girder_worker

RUN rm -rf ./dist && python setup.py sdist

FROM base
COPY --from=build /girder_worker/dist/*.tar.gz /
COPY --from=build /girder_worker/docker-entrypoint.sh /docker-entrypoint.sh
RUN pip install /*.tar.gz

RUN useradd -D --shell=/bin/bash && useradd -m worker

RUN chown -R worker:worker /usr/local/lib/python2.7/dist-packages/girder_worker/

USER worker


RUN girder-worker-config set celery broker "amqp://%(RABBITMQ_USER)s:%(RABBITMQ_PASS)s@%(RABBITMQ_HOST)s/"


VOLUME /girder_worker

ENTRYPOINT ["/docker-entrypoint.sh"]
