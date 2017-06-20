from .choice import Choice


class StringMultichoice(Choice):
    paramType = 'string-enumeration-multiple'
    multiple = True
