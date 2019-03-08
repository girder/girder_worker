FROM girder/girder:2.x-maintenance
MAINTAINER Christopher Kotfila <chris.kotfila@kitware.com>

RUN pip install ansible girder-client

COPY ./scripts /scripts

# Allow mounting /girder_worker
RUN mkdir /girder_worker
VOLUME /girder_worker

# Make sure remote debugging is available
RUN pip install rpdb
# Make sure we have the newest girder_client
RUN pip install -U "git+https://github.com/girder/girder.git@2.x-maintenance#egg=girder_client&subdirectory=clients/python"

# Make sure we have the newest girder_client (on 2.x-maintenance)
RUN pip install -U "git+https://github.com/girder/girder.git@2.x-maintenance#egg=girder_client&subdirectory=clients/python"

ENTRYPOINT ["/scripts/girder_entrypoint.sh", "-H", "0.0.0.0", "-p", "8989", "-d", "mongodb://mongo:27017/girder"]
