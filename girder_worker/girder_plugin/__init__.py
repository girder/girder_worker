#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

# Pre-girder 3.0 plugins supported the same entrypoint (girder.plugin) to register
# themselves.  If a Girder 2.x instance is installed with this package, it will
# attempt to load this entrypoint and fail with an error message.  Due to how
# pre-3.0 plugins worked, it still falls back to the built-in version of worker
# and functions correctly.  The logic below eliminates that error message.

# First ensure girder is installed, otherwise it doesn't make sense to import
# this module at all.
import girder  # noqa

from girder_worker import logger

# Detect if girder>=3 is installed by checking an import that was added in 3.0.
_isGirder3 = False
try:
    from girder.plugin import getPlugin, GirderPlugin
    _isGirder3 = True
except ImportError:
    logger.info('Girder 2.x is detected skipping incompatible entrypoint definition.')


# If girder>=3 is installed, it is safe to continue defining the plugin class, otherwise
# just define a dummy class to prevent error messages from propagating.
if _isGirder3:
    from girder import events
    from girder.constants import AccessType
    from girder_jobs.models.job import Job

    from .api.worker import Worker
    from . import event_handlers

    class WorkerPlugin(GirderPlugin):
        DISPLAY_NAME = 'Worker'
        CLIENT_SOURCE_PATH = 'web_client'

        def load(self, info):
            getPlugin('jobs').load(info)

            info['apiRoot'].worker = Worker()

            events.bind('jobs.schedule', 'worker', event_handlers.schedule)
            events.bind('jobs.status.validate', 'worker', event_handlers.validateJobStatus)
            events.bind('jobs.status.validTransitions', 'worker', event_handlers.validTransitions)
            events.bind('jobs.cancel', 'worker', event_handlers.cancel)
            events.bind('model.job.save.after', 'worker', event_handlers.attachJobInfoSpec)
            events.bind('model.job.save', 'worker', event_handlers.attachParentJob)
            Job().exposeFields(AccessType.SITE_ADMIN, {'celeryTaskId', 'celeryQueue'})
else:
    class WorkerPlugin(object):
        pass
