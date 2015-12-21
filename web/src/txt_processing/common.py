prefix_to_state_enum = {
    '-': 'Incomplete',
    '?': 'Needs Review',
    '//': 'Paused',
    '...': 'Deferred',
    'XXX': 'Dropped',
    '->': 'Delegated',
    'x': 'Complete',
    '': 'Inbox',
}

state_enum_to_prefix = {v:k for k,v in prefix_to_state_enum.iteritems()}


def convert_prefix_to_state(prefix):
    return prefix_to_state_enum[prefix]

def convert_state_to_prefix(state_enum):
    return state_enum_to_prefix[state_enum]
