#!/usr/bin/env python
# coding=utf-8

import json, sys, linecache
from operator import attrgetter

# log the current exception
def log_exception():
    exc_type, exc_obj, tb = sys.exc_info()
    f = tb.tb_frame
    lineno = tb.tb_lineno
    filename = f.f_code.co_filename
    linecache.checkcache(filename)
    line = linecache.getline(filename, lineno, f.f_globals)
    print("Exception:\t{}, Line {}".format(filename, lineno))
    print( '          \t{}'.format(line.strip()))
    print( '          \t{}:{}'.format(type(exc_obj),exc_obj))


# determines if object is iterable
def is_iterable(obj):
    try:
        it = iter(obj)
    except TypeError: 
        return False
    return True

# Get a list of the unique values in a list
def get_unique(list_of_values):
    # intilize a null list
    unique_list = []
    
    # traverse for all elements
    for x in list_of_values:
        # check if exists in unique_list or not
        if x not in unique_list:
            unique_list.append(x)
    return unique_list

# Get a list of unique field values from a list of items
def get_unique_values(list_of_items, field_name):
    unique_list = []
    for item in list_of_items:
        field_value = item[field_name]
        if field_value not in unique_list:
            unique_list.append(field_value)
    return unique_list

# Get a list of items whose item[field] = value
def get_matching_items(list_of_items, field_name, value):
    results = []
    for item in list_of_items:
        field_value = item[field_name]
        if field_value == value:
            results.append(item)
    return results

# Set an attribute on an object  using a dotted path
# example: set_attr_nested(person,"name.first","Michael")
def setattr_nested(obj, path, value):
    path, _, target = path.rpartition('.')
    if path != "":
        for attrname in path.split('.'):
            obj = getattr(obj, attrname)
    setattr(obj, target, value)


# Get a value or a list of values from a dictionary key using a path
# Example: dictor(data, "employees.John Doe.first_name")
def dictor(data, path=None, default=None, checknone=False, ignorecase=False, pathsep=".", search=None, pretty=False):
    '''Get a value or a list of values from a dictionary key using a path
    Args:
        data (dict): Input dictionary to be searched in.
        path (str, optional): Dictionary key search path (pathsep separated).
            Defaults to None.
        default (Any, optional): Default value to return if the key is not found.
            Defaults to None.
        checknone (bool, optional): If set, an exception is thrown if the value
            is None. Defaults to False.
        ignorecase (bool, optional): If set, upper/lower-case keys are treated
            the same. Defaults to False.
        pathsep (str, optional): Path separator for path parameter. Defaults to ".".
        search (Any, optional): Search for specific keys and output a list of values.
            Defaults to None.
        pretty (bool, optional): Pretty prints the result. Defaults to False.
    Raises:
        ValueError: Raises if checknone is set.
    Returns:
        Any: Returns one value or a list of values for the specified key.
    Examples:
        > dictor(data, "employees.John Doe.first_name")
        parse key index and fallback on default value if None,
        > dictor(data, "employees.5.first_name", "No employee found")
        pass a parameter
        > dictor(data, "company.{}.address".format(my_company))
        if using Python 3, can use F-strings to pass parameter
        > param = 'MyCompany'
        > dictor(data, f"company.{param}.address")
        lookup a 3rd element of List, on second key, lookup index=5
        > dictor(data, "3.first.second.5")
        lookup a nested list of lists
        > dictor(data, "0.first.1.2.second.third.0.2"
        check if return value is None, if it is, raise an error
        > dictor(data, "some.key.value", checknone=True)
        > ValueError: value not found for search path: "some.key.value"
        ignore letter casing when searching
        > dictor(data, "employees.Fred Flintstone", ignorecase=True)
        search data for specific keys (will return a list of all keys it finds)
        > dictor(data, "employees", search="name")
        pretty-print output
        > dictor(data, "employees", pretty=True)
    '''
    def __format(data, pretty):
        ''' formats output if pretty=True '''
        if pretty:
            return json.dumps(data, indent=4, sort_keys=True)
        else:
            return data

    if search is None and (path is None or path == ''):
        return __format(data, pretty)

    try:
        if path:
            for key in path.split(pathsep):
                if isinstance(data, (list, tuple)):
                    val = data[int(key)]
                else:
                    if ignorecase:
                        for datakey in data.keys():
                            if datakey.lower() == key.lower():
                                key = datakey
                                break
                    if key in data:
                        val = data[key]
                    else:
                        val = None
                        break
                data = val

        if search:
            search_ret = []
            if isinstance(data, (list, tuple)):
                for d in data:
                    for key in d.keys():
                        if key == search:
                            try:
                                search_ret.append(d[key])
                            except (KeyError, ValueError, IndexError, TypeError, AttributeError):
                                pass
            else:
                for key in data.keys():
                    if key == search:
                        try:
                            search_ret.append(data[key])
                        except (KeyError, ValueError, IndexError, TypeError, AttributeError):
                            pass
            if search_ret:
                val = search_ret
            else:
                val = default
    except (KeyError, ValueError, IndexError, TypeError, AttributeError):
        val = default

    if checknone:
        if val is None or val == default:
            raise ValueError('value not found for search path: "%s"' % path)

    if val is None or val == '':
        return default
    else:
        return __format(val, pretty)