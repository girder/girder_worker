/**
 * Administrative configuration view. Shows the global-level settings for this
 * plugin.
 */
girder.views.romanesco_ConfigView = girder.View.extend({
    events: {
        'submit #g-romanesco-settings-form': function (event) {
            event.preventDefault();
            this.$('#g-romanesco-settings-error-message').empty();

            this._saveSettings([{
                key: 'romanesco.broker',
                value: this.$('#g-romanesco-broker').val().trim()
            }, {
                key: 'romanesco.backend',
                value: this.$('#g-romanesco-backend').val().trim()
            }]);
        }
    },
    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
              list: JSON.stringify(['romanesco.broker', 'romanesco.backend'])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#g-romanesco-broker').val(resp['romanesco.broker']);
            this.$('#g-romanesco-backend').val(resp['romanesco.backend']);
        }, this));
    },

    render: function () {
        this.$el.html(girder.templates.romanesco_config());

        if (!this.breadcrumb) {
            this.breadcrumb = new girder.views.PluginConfigBreadcrumbWidget({
                pluginName: 'Romanesco',
                el: this.$('.g-config-breadcrumb-container'),
                parentView: this
            });
        }

        this.breadcrumb.render();

        return this;
    },

    _saveSettings: function (settings) {
        girder.restRequest({
            type: 'PUT',
            path: 'system/setting',
            data: {
                list: JSON.stringify(settings)
            },
            error: null
        }).done(_.bind(function (resp) {
            girder.events.trigger('g:alert', {
                icon: 'ok',
                text: 'Settings saved.',
                type: 'success',
                timeout: 4000
            });
        }, this)).error(_.bind(function (resp) {
            this.$('#g-romanesco-settings-error-message').text(
                resp.responseJSON.message);
        }, this));
    }
});

girder.router.route('plugins/romanesco/config', 'romanescoCfg', function () {
    girder.events.trigger('g:navigateTo', girder.views.romanesco_ConfigView);
});

girder.exposePluginConfig('romanesco', 'plugins/romanesco/config');
