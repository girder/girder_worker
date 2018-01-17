FROM ubuntu:xenial

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
    r-base \
    libpython-dev && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

RUN wget https://bootstrap.pypa.io/get-pip.py && python get-pip.py


WORKDIR /girder_worker
COPY setup.py /girder_worker/setup.py
COPY requirements.txt /girder_worker/requirements.txt
COPY requirements.in /girder_worker/requirements.in
COPY README.rst /girder_worker/README.rst
COPY examples /girder_worker/examples
COPY scripts /girder_worker/scripts
COPY girder_worker /girder_worker/girder_worker
COPY docker-entrypoint.sh /girder_worker/docker-entrypoint.sh

RUN pip install -e .

RUN useradd -D --shell=/bin/bash && useradd -m worker

# RUN /usr/local/bin/girder-worker-config set girder_worker tmp_root /tmp
RUN chown -R worker:worker /girder_worker

USER worker


RUN girder-worker-config set celery broker "amqp://%(RABBITMQ_USER)s:%(RABBITMQ_PASS)s@%(RABBITMQ_HOST)s/"


VOLUME /girder_worker

ENTRYPOINT ["./docker-entrypoint.sh"]
