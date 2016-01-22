from common import convert_state_to_prefix

indent_string = '    '

#            return {
#                "name": self.name,
#                "_id": self.id_string,
#                "children": [c.to_dict() for c in self.children],
#                "status": self.status,
#                "deferred_to": self.deferred_to,
#                "delegated_to": self.delegated_to,
#                "tags": self.tags,
#                "description": "\n".join(self.description),
#                "blocked_by": self.blocked_by,
#            }

def val_or_default_from_dict(d, k, default):
    ret = d.get(k, default)
    if ret is None:
        return default
    return ret


def mark_list_objs(in_arr):
    arr_len = len(in_arr)
    is_list = arr_len > 1

    for i in xrange(arr_len-1):
        obj = in_arr[i]
        next_obj = in_arr[i+1]

        if obj.get('_id', None) not in next_obj.get('blocked_by', []):
            is_list = False
            break

    for i in xrange(arr_len):
        obj = in_arr[i]
        next_obj = in_arr[i+1] if i+1 < arr_len else None

        obj['__internal_list_num'] = i+1 if is_list else None

        if is_list and next_obj is not None:
            next_obj['blocked_by'].remove(obj['_id'])


def append_obj_to_string_list(in_array, obj, level):
    name = val_or_default_from_dict(obj, 'name', '')
    _id = val_or_default_from_dict(obj, '_id', '')
    prefix = convert_state_to_prefix(val_or_default_from_dict(obj, 'status', 'Inbox'))
    deferred_to = val_or_default_from_dict(obj, 'deferred_to', '')
    delegated_to = val_or_default_from_dict(obj, 'delegated_to', '')
    tags = ', '.join(val_or_default_from_dict(obj, 'tags', []))
    description = val_or_default_from_dict(obj, 'description', '')
    blocked_by = ', '.join(val_or_default_from_dict(obj, 'blocked_by', []))
    trailing_space = int(val_or_default_from_dict(obj, 'trailing_space', 0))
    list_num = obj['__internal_list_num']

    indent_prefix = ''.join([indent_string]*level)

    if prefix == '':
        if list_num is None:
            main_string_list = [indent_prefix + name]
        else:
            main_string_list = [indent_prefix + str(list_num) + " " + name]
    else:
        if list_num is None:
            main_string_list = [indent_prefix + prefix]
        else:
            main_string_list = [indent_prefix + str(list_num) + prefix]

        if prefix == '->' and len(delegated_to) > 0:
            main_string_list.append(delegated_to+":")
        if prefix == '...' and len(deferred_to) > 0:
            main_string_list.append(deferred_to+":")
        main_string_list.append(name)
    if len(tags) > 0:
        main_string_list.append('~(' + tags + ')')
    if len(_id) > 0:
        main_string_list.append('~[' + _id + ']')

    in_array.append(' '.join(main_string_list))

    if len(description) > 0:
        in_array.extend([indent_prefix+': '+s for s in description.split('\n')])
    if len(blocked_by) > 0:
        in_array.append(indent_prefix+'BLOCKED BY: '+blocked_by)

    in_array.extend([indent_prefix]*trailing_space)

    # TODO: warn on infinite loops with the parent...
    children = val_or_default_from_dict(obj, 'children', [])
    children.sort(key=lambda o: o.get('order_in_list', 0))
    mark_list_objs(children)
    for child in children:
        append_obj_to_string_list(in_array, child, level+1)


def convert_json_to_txt(in_json):
    out_text_list = []
    in_json.sort(key=lambda o: o.get('order_in_list', 0))
    mark_list_objs(in_json)
    for obj in in_json:
        append_obj_to_string_list(out_text_list, obj, 0)
    return '\n'.join(out_text_list)


if __name__ == "__main__":
    import sys
    import json
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    with open(in_file) as f:
        out_text = convert_json_to_txt(json.loads(f.read()))
    with open(out_file, 'w') as f:
        f.write(out_text)
