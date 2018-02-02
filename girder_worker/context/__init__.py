from . import girder_context, nongirder_context


def get_context():
    try:
        # Note: If we can import these objects from the girder packages we
        # assume our producer is in a girder REST request. This allows
        # us to create the job model's directly. Otherwise there will be an
        # ImportError and we can create the job via a REST request using
        # the jobInfoSpec in headers.

        from girder.utility.model_importer import ModelImporter # noqa
        from girder.plugins.worker import utils # noqa
        from girder.api.rest import getCurrentUser # noqa
        return girder_context
    except ImportError:
        return nongirder_context
