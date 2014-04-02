import celery

celeryapp = celery.Celery('romanesco',
    backend='mongodb://localhost/romanesco',
    broker='mongodb://localhost/romanesco')

analysis = {
    "name": "append_tables",
    "inputs": [{"name": "a", "type": "table", "format": "rows"}, {"name": "b", "type": "table", "format": "rows"}],
    "outputs": [{"name": "c", "type": "table", "format": "rows"}],
    "script": "c = a + b",
    "mode": "python"
}

async_result = celeryapp.send_task("romanesco.run", [analysis], {
    "inputs": {
        "a": {"format": "json.rows", "data": '[{"aa": 1, "bb": 2}]'},
        "b": {"format": "json.rows", "data": '[{"aa": 3, "bb": 4}]'}
    },
    "outputs": {
        "c": {"format": "json.rows", "uri": "file://output.json"}
    }
})

print async_result.get()
