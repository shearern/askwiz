
from .exceptions import ValidationFailed


def merge_dicts(target, source):
    '''
    Merge data from one dict into another

    :param target: Dictionary to merge into
    :param source: Dictionary to merge from
    '''

    for key in source:
        if key in target and source[key].__class__ is dict and target[key].__class__ is dict:
            merge_dicts(target[key], source[key])
        else:
            target[key] = source[key]


def add_validator(existing, new_validator):
    if existing is None:
        existing = list()
    else:
        existing = list(existing)
    existing.append(new_validator)
    return existing


