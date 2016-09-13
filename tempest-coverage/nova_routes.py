import nova.api.openstack.compute
from misc import REPLACEMENTS_DICT
from nova import config

config.parse_args([])

router_v21 = nova.api.openstack.compute.APIRouterV21()


def format_methods(r):
    if r.conditions:
        method = r.conditions.get('method', '')
        return type(method) is str and method or ', '.join(method)
    else:
        return ''


def normalize_route(route):
    for regex, repl in REPLACEMENTS_DICT.items():
        route = regex.sub(repl, route)
    return route


def get_routes(router, patterns_to_exclude=None, route_prefix_to_add=''):
    routes = []
    if not patterns_to_exclude:
        patterns_to_exclude = []

    for r in router.map.matchlist:
        for pattern_to_exclude in patterns_to_exclude:
            if pattern_to_exclude in r.routepath:
                break
        else:
            routes.append(
                (format_methods(r),
                 route_prefix_to_add + normalize_route(r.routepath))
            )

    return routes


table = [('Methods', 'Path')] + get_routes(router_v21,
                                           ['/new', '/edit', '(format)'],
                                           '/v2.1')

# import pdb; pdb.set_trace()
widths = [max(len(row[col]) for row in table) for col in range(len(table[0]))]

print('\n'.join(
    ' '.join(row[col].ljust(widths[col])
             for col in range(len(widths)))
    for row in table))
