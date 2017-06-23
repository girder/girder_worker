def run(task, inputs, outputs, task_inputs, task_outputs, **kwargs):  # noqa
    from girder_worker.core import events, io, run as core_run, utils

    # Make map of steps
    steps = {step['name']: step for step in task['steps']}

    # Make map of input bindings
    bindings = {step['name']: {} for step in task['steps']}

    # Create dependency graph and downstream pointers
    dependencies = {step['name']: set() for step in task['steps']}
    downstream = {}
    for conn in task['connections']:
        # Add dependency graph link for internal links
        if 'input_step' in conn and 'output_step' in conn:
            dependencies[conn['input_step']].add(conn['output_step'])

        # Add downstream links for links with output
        if 'output_step' in conn:
            ds = downstream.setdefault(conn['output_step'], {})
            ds_list = ds.setdefault(conn['output'], [])
            ds_list.append(conn)

        # Set initial bindings for inputs
        if 'input_step' in conn and 'output_step' not in conn:
            name = conn['name']
            bindings[conn['input_step']][conn['input']] = task_inputs[name].copy()
            bindings[conn['input_step']][conn['input']]['data'] = inputs[name]['script_data']

    # Traverse analyses in topological order
    for step_set in utils.toposort(dependencies):
        for step in step_set:
            # Visualizations cannot be executed
            if 'visualization' in steps[step] and steps[step]['visualization']:
                continue

            # Run step
            print '--- beginning: %s ---' % steps[step]['name']
            out = core_run(steps[step]['task'], bindings[step])
            print '--- finished: %s ---' % steps[step]['name']
            # Update bindings of downstream analyses
            if step in downstream:
                for name, conn_list in downstream[step].iteritems():
                    for conn in conn_list:
                        if 'input_step' in conn:
                            # This is a connection to a downstream step
                            b = bindings[conn['input_step']]
                            b[conn['input']] = out[name]
                        else:
                            # This is a connection to a final output
                            o = outputs[conn['name']]
                            o['script_data'] = out[name]['data']

    # Output visualization parameters
    outputs['_visualizations'] = []
    for step in task['steps']:
        if 'visualization' not in step or not step['visualization']:
            continue
        vis_bindings = {}
        for b, value in bindings[step['name']].iteritems():
            value['script_data'] = value['data']
            vis_input = None
            for step_input in step['task']['inputs']:
                if step_input['name'] == b:
                    vis_input = step_input

            if not vis_input:
                raise Exception('Could not find visualization input named %s.' % b)

            info = {
                'task': task,
                'task_inputs': task_inputs,
                'task_outputs': task_outputs,
                'mode': value.get('mode'),
                'inputs': inputs,
                'outputs': outputs,
                'status': kwargs.get('status'),
                'job_mgr': kwargs.get('_job_manager'),
                'kwargs': kwargs
            }

            e = events.trigger('run.handle_output', {
                'info': info,
                'task_output': vis_input,
                'output': value,
                'outputs': {step['name']: value},
                'name': step['name']
            })

            if not e.default_prevented and 'mode' in value:
                io.push(value['data'], value)
            else:
                vis_bindings[b] = {
                    'type': vis_input['type'],
                    'format': vis_input['format'],
                    'data': value['data']
                }

            """
            # Validate the output
            if (validate and not girder_worker.core.isvalid(
                    vis_input['type'], value)):
                raise Exception(
                    'Output %s (%s) is not in the expected type (%s) and '
                    'format (%s).' % (
                        name, type(value['data']),
                        vis_input['type'], value['format']))

            if auto_convert:
                vis_bindings[b] = girder_worker.core.convert(
                    vis_input['type'],
                    value,
                    {'format': vis_input['format']}
                )

            elif value['format'] == vis_input['format']:
                data = script_output['data']
                if 'mode' in value:
                    girder_worker.core.io.push(data, value)
                else:
                    vis_bindings[b] = {
                        'type': vis_input['type'],
                        'format': vis_input['format'],
                        'data': data
                    }
            else:
                raise Exception(
                    'Expected exact format match but "' +
                    value['format'] +
                    '" != "' + vis_input['format'] + '".'
                )
            """

            vis_bindings[b].pop('script_data', None)

        outputs['_visualizations'].append({
            'mode': 'preset',
            'type': step['name'],
            'inputs': vis_bindings
        })
