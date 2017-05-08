# -*- coding: utf-8 -*-

from Bio.Phylo import BaseTree


def recursive_attr(obj):
    """Recursively parase through phyloXML data that is not a Clade"""
    dictionary = {}
    try:
        # if obj has subobjects, parse throuh them and insert in a dictionary
        for key in obj.__dict__.keys():
            attr = getattr(obj, key)
            if attr and attr is not None:
                if isinstance(attr, BaseTree.TreeElement):
                    dictionary[key] = recursive_attr(attr)
                else:
                    dictionary[key] = getattr(obj, key)
        return dictionary
    except Exception:
        # else just return the object
        return obj


def recursive_clade(obj, data_coll, tree_coll=None):
    """Recursively parse through phyloXML"""
    # instantiate variables
    clade_children = []
    tempDict = {}
    if tree_coll is not None:
        treeDict = {}

    # iterate through each attribute of the obj
    for key in obj.__dict__.keys():
        attr = getattr(obj, key)
        if attr and attr is not None:
            # debugging
            print 'key = %s, attr = %s' % (key, attr)

            # get all non-recursive clade attributes first
            # do we need to even do this first? SZ -Aug 16, 2012
            if isinstance(attr, BaseTree.Clade):
                clade_children.append(attr)
            elif isinstance(attr, list):
                tempDictList = []
                # iterate through each element of the list
                for elem in attr:
                    if isinstance(elem, BaseTree.Clade):
                        clade_children.append(elem)
                    # if it's a complex phyloxml TreeElement attribute, parse
                    # it using recurisve_attr
                    else:
                        print('  elem3, attr = %s, type = %s'
                              % (attr, type(elem)))
                        tempDictList.append(recursive_attr(elem))
                tempDict[key] = tempDictList
            else:  # isinstance(attr, BaseTree.TreeElement):
                tempDict[key] = recursive_attr(attr)
    # process all clades that are children of obj
    if clade_children:
        tempDict['clades'] = []
        if tree_coll is not None:
            treeDict['clades'] = []
        for child in clade_children:
            child_id = recursive_clade(child, data_coll, tree_coll)
            tempDict['clades'].append(child_id['dataId'])

            if tree_coll is not None:
                # if we want to insert dataLink data in the treeDict, this is
                # how we'd do it
                # treeDict['children'].append({'treeLink':child_id['treeId'],
                #                              'dataLink':child_id['dataId']})
                treeDict['clades'].append(child_id['treeId'])
    # if args.debug_level >= 1:
    # print 'object name: ', obj.name, tempDict
    # insert into mongodb here

    # add mongodb id
    tempDict['_id'] = insertIntoMongo(tempDict, data_coll)
    if tree_coll is not None:
        treeDict['dataLink'] = tempDict['_id']
        insertIntoMongo(treeDict, tree_coll)
    # if args.debug_level >= 1:
    # print tempDict
    # CRL - added option for return withou treeDict
    if tree_coll is not None:
        return {'dataId': tempDict['_id'], 'treeId': treeDict['_id']}
    else:
        return {'dataId': tempDict['_id']}


def insertIntoMongo(item, collection):
    return collection.insert(item)
