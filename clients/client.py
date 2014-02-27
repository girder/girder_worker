import celery

celeryapp = celery.Celery('cardoon',
    backend='mongodb://localhost/cardoon',
    broker='mongodb://localhost/cardoon')

analysis = {
    "name": "append_tables",
    "inputs": [{"name": "a", "type": "table", "format": "python.rows"}, {"name": "b", "type": "table", "format": "python.rows"}],
    "outputs": [{"name": "c", "type": "table", "format": "python.rows"}],
    "script": "c = a + b",
    "mode": "python"
}

async_result = celeryapp.send_task("cardoon.run", [analysis], {
    "inputs": {
        "a": {"format": "json.rows", "data": '[{"aa": 1, "bb": 2}]'},
        "b": {"format": "json.rows", "data": '[{"aa": 3, "bb": 4}]'}
    },
    "outputs": {
        "c": {"format": "json.rows", "uri": "file://output.json"}
    }
})

print async_result.get()
