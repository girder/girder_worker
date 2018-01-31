from . import girder_context, nongirder_context


def get_context():
    try:
        from girder.utility.model_importer import ModelImporter # noqa
        from girder.plugins.worker import utils # noqa
        from girder.api.rest import getCurrentUser # noqa
        return girder_context
    except ImportError:
        return nongirder_context
