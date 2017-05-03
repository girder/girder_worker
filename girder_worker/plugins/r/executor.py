import rpy2.robjects
import six


def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):
    env = rpy2.robjects.globalenv

    # Clear out workspace variables and packages
    rpy2.robjects.reval("""
        rm(list = ls())
        pkgs <- names(sessionInfo()$otherPkgs)
        if (!is.null(pkgs)) {
            pkgs <- paste('package:', pkgs, sep = '')
            lapply(pkgs, detach, character.only = TRUE, unload = TRUE)
        }
        """, env)

    env['tempdir'] = kwargs.get('_tempdir')

    for name in inputs:
        env[str(name)] = inputs[name]['script_data']

    if isinstance(task['script'], six.binary_type):
        task['script'] = task['script'].decode('utf8')
    rpy2.robjects.reval(task['script'], env)

    for name, task_output in six.viewitems(task_outputs):
        d = outputs[name]
        d['script_data'] = env[str(name)]

        # Hack to detect scalar values from R.
        # The R value might not have a len() so wrap in a try/except.
        try:
            if len(d['script_data']) == 1:
                d['script_data'] = d['script_data'][0]
        except TypeError:
            pass
