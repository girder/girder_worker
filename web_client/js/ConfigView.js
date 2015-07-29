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
            }, {
                key: 'romanesco.full_access_users',
                value: this.$('#g-romanesco-full-access-users').val().trim()
            }, {
                key: 'romanesco.full_access_groups',
                value: this.$('#g-romanesco-full-access-groups').val().trim()
            }, {
                key: 'romanesco.safe_folders',
                value: this.$('#g-romanesco-safe-folders').val().trim()
            }, {
                key: 'romanesco.require_auth',
                value: this.$('#g-romanesco-require-auth').is(':checked')
            }]);
        }
    },

    initialize: function () {
        girder.restRequest({
            type: 'GET',
            path: 'system/setting',
            data: {
              list: JSON.stringify([
                  'romanesco.broker',
                  'romanesco.backend',
                  'romanesco.full_access_users',
                  'romanesco.full_access_groups',
                  'romanesco.safe_folders',
                  'romanesco.require_auth'
              ])
            }
        }).done(_.bind(function (resp) {
            this.render();
            this.$('#g-romanesco-broker').val(resp['romanesco.broker']);
            this.$('#g-romanesco-backend').val(resp['romanesco.backend']);
            this.$('#g-romanesco-full-access-users').val(JSON.stringify(
                resp['romanesco.full_access_users'] || []));
            this.$('#g-romanesco-full-access-groups').val(JSON.stringify(
                resp['romanesco.full_access_groups'] || []));
            this.$('#g-romanesco-safe-folders').val(JSON.stringify(
                resp['romanesco.safe_folders'] || []));
            this.$('#g-romanesco-require-auth').attr('checked',
                resp['romanesco.require_auth'] === false ? null : 'checked');
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
