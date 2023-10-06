FROM ubuntu:22.04 as base

RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -qy tzdata && \
  apt-get install -qy software-properties-common python3-software-properties && \
  apt-get update && apt-get install -qy \
  build-essential \
  wget \
  python3 \
  r-base \
  libffi-dev \
  libssl-dev \
  libjpeg-dev \
  zlib1g-dev \
  r-base \
  libpython3-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/pip/get-pip.py && python3 get-pip.py


FROM base as build

RUN apt-get update && apt-get install -qy git

COPY ./ /girder_worker/
WORKDIR /girder_worker

RUN rm -rf ./dist && python3 setup.py sdist


FROM base
COPY --from=build /girder_worker/dist/*.tar.gz /
COPY --from=build /girder_worker/docker-entrypoint.sh /docker-entrypoint.sh
RUN pip3 install /*.tar.gz

RUN useradd -D --shell=/bin/bash && useradd -m worker

RUN chown -R worker:worker /usr/local/lib/python3.10/dist-packages/girder_worker/

USER worker

RUN girder-worker-config set celery broker "amqp://%(RABBITMQ_USER)s:%(RABBITMQ_PASS)s@%(RABBITMQ_HOST)s/"


VOLUME /girder_worker

ENV PYTHON_BIN=python3

ENTRYPOINT ["/docker-entrypoint.sh"]
