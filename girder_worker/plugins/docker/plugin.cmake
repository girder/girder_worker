add_python_test(docker PLUGIN docker PLUGINS_ENABLED docker)
set_property(TEST plugins.docker.docker APPEND PROPERTY ENVIRONMENT "WORKER_FORCE_DOCKER_START=true")
