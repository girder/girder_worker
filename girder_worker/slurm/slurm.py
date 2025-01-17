import requests
import json


def uint64_no_val_struct(number):
    # https://slurm.schedmd.com/rest_api.html#v0.0.42_uint64_no_val_struct
    return {
        'set': True,
        'infinite': False,
        'number': number,
    }


def job_desc_msg(account, script, script_args, **kwargs):
    # https://slurm.schedmd.com/rest_api.html#v0.0.42_job_desc_msg
    # TODO: rigorously validate kwargs (not [])
    # TODO: see if other kwards are necessary... generic support?
    job = {
        'script': script,
        'argv': script_args,

        'account': account,
        'partition': kwargs['partition'],
        'time_limit': uint64_no_val_struct(kwargs['time_limit']), # TODO: needs to be UNIX timestamp

        'tasks': kwargs['tasks'],  # --ntasks
        'qos': kwargs['qos'],
        'cpus_per_task': kwargs['cpus_per_task'],
        'memory_per_node': uint64_no_val_struct(kwargs['memory_per_node']),
        'current_working_directory': kwargs['current_working_directory'],
        # TODO: need to add --gres, don't know which variable it is
        #    A: --gres=gpu:2 -> 'tres_per_node': 'gres/gpu:2',
    }
    return job


def job_submit_req(job):
    # https://slurm.schedmd.com/rest_api.html#v0.0.42_job_submit_req
    return {
        'job': job,
    }


class SlurmJob:
    def __init__(self, address):
        self.url = f'{address}/slurm/v0.0.42' # TODO: make this more general (not hard-coded to v0.0.42, if possible)
        self.job_id = None

    # sbatch equivalent
    def submit(self, job):
        job_request = json.dumps(job_submit_req(job))
        resp = requests.put(self.url + '/job/submit', data=job_request)

        # TODO: handle better
        if resp.status_code != 200:
            raise Exception(f'Failed to submit job: {resp.text}')

        resp = resp.json() # https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_job_submit_response
        self.job_id = resp['job_id']
        return resp

    def status(self):
        resp = requests.get(self.url + f'/job/{self.job_id}')

        # TODO: handle better
        if resp.status_code != 200:
            raise Exception(f'Failed to get job status: {resp.text}')

        return resp.json() # https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_job_info_resp

    def cancel(self):
        resp = requests.delete(self.url + f'/job/{self.job_id}')

        # TODO: handle better
        if resp.status_code != 200:
            raise Exception(f'Failed to cancel job: {resp.text}')

        return resp.json() # https://slurm.schedmd.com/rest_api.html#v0.0.42_openapi_kill_job_resp
