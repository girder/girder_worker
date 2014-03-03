from girder import events

def load(info):
    def cardoonItemGet(event):
        path = event.info['pathParams']
        if len(path) >= 2 and path[1] == 'cardoon':
            # item = info['apiRoot'].item
            event.addResponse("Haha you've been cardoon-ed!")
            event.stopPropagation()
            event.preventDefault()

    name = 'rest.item.get.before'
    handlerName = 'cardoon'
    events.bind(name, handlerName, cardoonItemGet)
