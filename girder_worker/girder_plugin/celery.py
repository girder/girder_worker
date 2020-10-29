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

from __future__ import absolute_import

import celery

from girder.models.setting import Setting

from .constants import PluginSettings

_celeryapp = None


def getCeleryApp():
    """
    Lazy loader for the celery app. Reloads anytime the settings are updated.
    """
    global _celeryapp

    if _celeryapp is None:
        backend = Setting().get(PluginSettings.BACKEND) or 'amqp://guest:guest@localhost/'
        broker = Setting().get(PluginSettings.BROKER) or 'amqp://guest:guest@localhost/'
        _celeryapp = celery.Celery('girder_worker', backend=backend, broker=broker)
    return _celeryapp
