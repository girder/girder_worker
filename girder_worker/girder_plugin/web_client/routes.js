/* eslint-disable import/first */

import router from '@girder/core/router';
import events from '@girder/core/events';
import { exposePluginConfig } from '@girder/core/utilities/PluginUtils';

exposePluginConfig('worker', 'plugins/worker/config');

import ConfigView from './views/ConfigView';
router.route('plugins/worker/config', 'workerConfig', function () {
    events.trigger('g:navigateTo', ConfigView);
});

import taskStatusView from './views/taskStatusView';
router.route('plugins/worker/task/status', 'workerTaskStatus', function () {
    events.trigger('g:navigateTo', taskStatusView);
});
