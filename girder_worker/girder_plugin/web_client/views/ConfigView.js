import PluginConfigBreadcrumbWidget from '@girder/core/views/widgets/PluginConfigBreadcrumbWidget';
import View from '@girder/core/views/View';
import events from '@girder/core/events';
import { restRequest } from '@girder/core/rest';
import router from '@girder/core/router';

import ConfigViewTemplate from '../templates/configView.pug';

var ConfigView = View.extend({
    events: {
        'submit #g-worker-settings-form': function (event) {
            event.preventDefault();
            this.$('#g-worker-settings-error-message').empty();

            this._saveSettings([{
                key: 'worker.api_url',
                value: this.$('#g-worker-api-url').val().trim()
            }, {
                key: 'worker.broker',
                value: this.$('#g-worker-broker').val().trim()
            }, {
                key: 'worker.backend',
                value: this.$('#g-worker-backend').val().trim()
            }, {
                key: 'worker.direct_path',
                value: this.$('#g-worker-direct-path').is(':checked')
            }, {
                key: 'worker.slurm_account',
                value: this.$('#g-worker-slurm-account').val().trim()
            }, {
                key: 'worker.slurm_qos',
                value: this.$('#g-worker-slurm-qos').val().trim()
            }, {
                key: 'worker.slurm_mem',
                value: this.$('#g-worker-slurm-mem').val().trim()
            }, {
                key: 'worker.slurm_cpus',
                value: this.$('#g-worker-slurm-cpu').val().trim()
            }, {
                key: 'worker.slurm_ntasks',
                value: this.$('#g-worker-slurm-ntasks').val().trim()
            }, {
                key: 'worker.slurm_partition',
                value: this.$('#g-worker-slurm-partition').val().trim()
            }, {
                key: 'worker.slurm_time',
                value: this.$('#g-worker-slurm-time').val().trim()
            }, {
                key: 'worker.slurm_gres_config',
                value: this.$('#g-worker-slurm-gres-config').val().trim()
            }, {
                key: 'worker.slurm_gpu',
                value: this.$('#g-worker-slurm-gpu').val().trim()
            }, {
                key: 'worker.slurm_gpu_partition',
                value: this.$('#g-worker-slurm-gpu-partition').val().trim()
            }, {
                key: 'worker.slurm_gpu_mem',
                value: this.$('#g-worker-slurm-gpu-mem').val().trim()
            }]);
        },

        'click .q-worker-task-info': function (event) {
            router.navigate('#plugins/worker/task/status', {trigger: true});
        }
    },

    initialize: function () {
        restRequest({
            method: 'GET',
            url: 'system/setting',
            data: {
                list: JSON.stringify([
                    'worker.api_url',
                    'worker.broker',
                    'worker.backend',
                    'worker.direct_path',
                    'worker.slurm_account',
                    'worker.slurm_qos',
                    'worker.slurm_mem',
                    'worker.slurm_cpus',
                    'worker.slurm_ntasks',
                    'worker.slurm_partition',
                    'worker.slurm_time',
                    'worker.slurm_gres_config',
                    'worker.slurm_gpu',
                    'worker.slurm_gpu_partition',
                    'worker.slurm_gpu_mem'
                ])
            }
        }).done((resp) => {
            this.render();
            this.$('#g-worker-api-url').val(resp['worker.api_url']);
            this.$('#g-worker-broker').val(resp['worker.broker']);
            this.$('#g-worker-backend').val(resp['worker.backend']);
            this.$('#g-worker-direct-path').prop('checked', resp['worker.direct_path']);
            this.$('#g-worker-slurm-account').val(resp['worker.slurm_account']);
            this.$('#g-worker-slurm-qos').val(resp['worker.slurm_qos']);
            this.$('#g-worker-slurm-mem').val(resp['worker.slurm_mem']);
            this.$('#g-worker-slurm-cpu').val(resp['worker.slurm_cpus']);
            this.$('#g-worker-slurm-ntasks').val(resp['worker.slurm_ntasks']);
            this.$('#g-worker-slurm-partition').val(resp['worker.slurm_partition']);
            this.$('#g-worker-slurm-time').val(resp['worker.slurm_time']);
            this.$('#g-worker-slurm-gres-config').val(resp['worker.slurm_gres_config']);
            this.$('#g-worker-slurm-gpu').val(resp['worker.slurm_gpu']);
            this.$('#g-worker-slurm-gpu-partition').val(resp['worker.slurm_gpu_partition']);
            this.$('#g-worker-slurm-gpu-mem').val(resp['worker.slurm_gpu_mem']);
        });
    },

    render: function () {
        this.$el.html(ConfigViewTemplate());

        if (!this.breadcrumb) {
            this.breadcrumb = new PluginConfigBreadcrumbWidget({
                pluginName: 'Worker',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            });
        }

        this.breadcrumb.render();

        return this;
    },

    _saveSettings: function (settings) {
        restRequest({
            method: 'PUT',
            url: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done((resp) => {
            events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }).fail((resp) => {
            this.$('#g-worker-settings-error-message').text(
                resp.responseJSON.message);
        });
    }
});

export default ConfigView;
