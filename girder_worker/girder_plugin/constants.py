#!/usr/bin/env python

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

# The path that will be mounted in docker containers for data IO
DOCKER_DATA_VOLUME = '/mnt/girder_worker/data'

# The path that will be mounted in docker containers for utility scripts
DOCKER_SCRIPTS_VOLUME = '/mnt/girder_worker/scripts'


# Settings where plugin information is stored
class PluginSettings:
    BROKER = 'worker.broker'
    BACKEND = 'worker.backend'
    API_URL = 'worker.api_url'
    DIRECT_PATH = 'worker.direct_path'
    # Slurm Settings
    SLURM_ACCOUNT = 'worker.slurm_account'
    SLURM_QOS = 'worker.slurm_qos'
    SLURM_MEM = 'worker.slurm_mem'
    SLURM_CPUS = 'worker.slurm_cpus'
    SLURM_NTASKS = 'worker.slurm_ntasks',
    SLURM_PARTITION = 'worker.slurm_partition'
    SLURM_TIME = 'worker.slurm_time'
    SLURM_GRES_CONFIG = 'worker.slurm_gres_config'
    # GPU Settings
    SLURM_GPU = 'worker.slurm_gpu'
    SLURM_GPU_PARTITION = 'worker.slurm_gpu_partition'
    SLURM_GPU_MEM = 'worker.slurm_gpu_mem'
