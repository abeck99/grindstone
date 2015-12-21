import regex
from common import convert_prefix_to_state

from tzlocal import get_localzone
tz = get_localzone()
import parsedatetime
cal = parsedatetime.Calendar()
import iso8601

# name_regex = r'^(?P<indention>\s*)(?P<_type>(?P<type>\?)|(?P<type>//)|(?P<type>\.\.\.)(?P<deferred_to>(?:.*?:|))|(?P<type>XXX)|(?P<type>->)(?P<delegated_to>(?:.*?:|))|(?P<type>-)|(?P<type>x)|(?P<type>))(?P<name>[^~]*)(?P<_tags>~\((?P<tags>.*?)\)|)(?P<filler_a>[^~]*)(?P<_ID>~\[(?P<ID>.*?)\]|)(?P<filler_b>[^~]*)(?P<filler_c>[^~]*)(?P<_tags_alt>~\((?P<tags>.*?)\)|)(?P<filler_d>.*)$'
name_regex = r'^(?P<indention>\s*)(?P<_type>(?P<type>\?)|(?P<type>//)|(?P<type>\.\.\.)(?:(?P<deferred_to>(?:.*?)):|)|(?P<type>XXX)|(?P<type>->)(?:(?P<delegated_to>(?:.*?)):|)|(?P<type>-)|(?P<type>x)|(?P<type>))(?P<name>[^~]*)(?P<_tags>~\((?P<tags>.*?)\)|)(?P<filler_a>[^~]*)(?P<_ID>~\[(?P<ID>.*?)\]|)(?P<filler_b>[^~]*)(?P<filler_c>[^~]*)(?P<_tags_alt>~\((?P<tags>.*?)\)|)(?P<filler_d>.*)$'
# name_regex = r'^(?P<indention>\s*)(?P<_type>(?P<type>\?)|(?P<type>//)|(?P<type>\.\.\.)(?:(?P<deferred_to>(?:.*?)):|)|(?P<type>XXX)|(?P<type>->)(?:(?P<delegated_to>(?:.*?)):|)|(?P<type>-)|(?P<type>x)|(?P<type>))\s*?(?P<name>[^~]*)(?P<_tags>~\((?P<tags>.*?)\)|)(?P<filler_a>[^~]*)(?P<_ID>~\[(?P<ID>.*?)\]|)(?P<filler_b>[^~]*)(?P<filler_c>[^~]*)(?P<_tags_alt>~\((?P<tags>.*?)\)|)(?P<filler_d>.*)$'

# indention
# type
# deferred_to
# delegated_to
# name
# tags
# ID
# filler_a
# filler_b
# filler_c
# filler_d


def string_to_isoformat(s):
    if s is None:
        return None
    try:
        dt = iso8601.parse_date(s)
    except iso8601.iso8601.ParseError:
        dt, _ = cal.parseDT(datetimeString=s, tzinfo=tz)
    return dt.isoformat()


class MalformedTextException(Exception):
    pass


def string_or_none_from_dict(d, k):
    if not d.has_key(k):
        return None
    s = d[k]
    if s is None:
        return None
    s = s.strip()
    if len(s) == 0:
        return None
    return s


class TaskObject(object):
    def __init__(self, line_no, indention_level, d=None):
        self.indention_level = indention_level
        self.id_string = None
        self.children = []
        if d is None:
            self.is_root = True
            self.name = "ROOT"
            return
        self.is_root = False

        self.status = convert_prefix_to_state(d['type'])
        self.deferred_to = string_to_isoformat(string_or_none_from_dict(d, 'deferred_to'))
        self.delegated_to = string_or_none_from_dict(d, 'delegated_to')
        self.name = string_or_none_from_dict(d, 'name')

        tags = d['tags']
        if tags is None:
            self.tags = []
        else:
            self.tags = [tag.strip() for tag in d['tags'].split(',') if len(tag.strip()) > 0]

        id_string = string_or_none_from_dict(d, 'ID')
        self.id_string = id_string

        if len(d['_tags']) > 0 and len(d['_tags_alt']) > 0:
            print d
            raise MalformedTextException('Error parsing, only one ~() can exist: Line ' + str(line_no))
        if any([len(d[k].strip()) > 0 for k in ['filler_a', 'filler_b', 'filler_c', 'filler_d']]):
            print d
            raise MalformedTextException('Error parsing, Misplaced ~: Line ' + str(line_no))
        self.blocked_by = []
        self.description = []
    def add_child(self, obj):
        self.children.append(obj)
    def push_description(self, desc):
        self.description.append(desc)
    def push_blocked_by(self, blocked_by):
        self.blocked_by.extend([b.strip() for b in blocked_by.split(',') if len(b.strip()) > 0])
    def to_dict(self):
        if self.is_root:
            return [c.to_dict() for c in self.children]
        else:
            return {
                "name": self.name,
                "_id": self.id_string,
                "children": [c.to_dict() for c in self.children],
                "status": self.status,
                "deferred_to": self.deferred_to,
                "delegated_to": self.delegated_to,
                "tags": self.tags,
                "description": "\n".join(self.description),
                "blocked_by": self.blocked_by,
            }


class ObjectList(object):
    def __init__(self):
        self.object_stack = [TaskObject(-1, -1)]
    def new_object(self, line_no, d):
        indention_level = len(d['indention'])

        new_object = TaskObject(line_no, indention_level, d)

        while True:
            current_object = self.current_object()
            if indention_level > current_object.indention_level:
                current_object.add_child(new_object)
                break
            del self.object_stack[-1]
        self.object_stack.append(new_object)
        return new_object
    def current_object(self):
        return self.object_stack[-1]
    def root(self):
        return self.object_stack[0]


def convert_txt_to_json(in_str):
    in_str = in_str.replace('\t', '    ')
    lines = in_str.split('\n')
    i = 0
    object_list = ObjectList()

    while True:
        if i >= len(lines):
            break

        line = lines[i]
        i += 1
        if len(line.strip()) == 0:
            continue

        match = regex.fullmatch(name_regex, line)
        if match is None:
            continue

        current_object = object_list.current_object()
        if not current_object.is_root:
            indent_string = ''.join([' ']*current_object.indention_level)
            description_prefix = indent_string + ": "
            blocked_by_prefix = indent_string + "BLOCKED BY: "
            if line.startswith(description_prefix):
                current_object.push_description(line[len(description_prefix):])
                continue
            if line.startswith(blocked_by_prefix):
                current_object.push_blocked_by(line[len(blocked_by_prefix):])
                continue

        object_list.new_object(i, match.groupdict())
    return object_list.root().to_dict()


if __name__ == '__main__':
    import sys
    import json
    in_file = sys.argv[1]
    out_file = sys.argv[2]
    with open(in_file) as f:
        out_json = convert_txt_to_json(f.read())
    with open(out_file, 'w') as f:
        out_text = json.dumps(out_json, sort_keys=True,
                      indent=4, separators=(',', ': '))
        f.write(out_text)
