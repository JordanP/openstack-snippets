#!/usr/bin/env python
"""
A CLI tool to list long running Rackspace Cloud servers.

Dependencies:
    This script uses several 3rd party Python modules. You should install
    them in a virtualenv with the following command:

    .. code:: shell

        $ pip install eventlet humanize iso8601 requests tabulate

Note:
    - Authentication requires a Rackspace username and a Rackspace API key. In
      order to avoid hardcoding credentials in this file, users can pass the
      CLI arguments `--rax-username` and `--rax-api-key`. Alternatively, the
      environement variables `RAX_USERNAME` and `RAX_API_KEY` can be set and
      will be read by the program. This is the safest option because CLI
      arguments can be read by any users (e.g with the `ps aux` command) on a
      system.
`
Hacking:
    - Please run pep8 and pylint

TODO:
    - Send HipChat Notification
"""

import argparse
import datetime
import functools
import logging
import os
import ssl
import sys

import eventlet
import humanize
import iso8601
import requests
import tabulate

eventlet.monkey_patch()

OS_AUTH_URL = 'https://identity.api.rackspacecloud.com/v2.0'
TOKEN_ID = None

EXC_TO_RETRY = (requests.exceptions.ConnectionError,
                requests.exceptions.ReadTimeout,
                ssl.SSLError)

# This mapping is used because listing all users in an organization
# requires to be "admin" and we want this script to be usable by "simple"
# users.
# NOTE(Admin): update this mapping each time a new Rackspace user is created.
USERID_TO_USERNAME = {
    '6d10dce340f941d7b5f62bdfabf690fc': 'jordan.pittier',
}


# From Russell Heilling: http://stackoverflow.com/a/10551190
class EnvDefault(argparse.Action):  # pylint: disable=R0903

    def __init__(self, envvar, required=True, default=None, **kwargs):
        # Overriding default with environment variable if available
        if envvar in os.environ:
            default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values)


def retry(excs, max_attempts=3):
    """Decorator to retry a function call if it raised a given exception.

    Args:
        excs: an exception or a tuple of exceptions
        max_attempts (int): the maximum number of times the function call
            should be retried.
    """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for i in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except excs as exc:
                    if i == max_attempts-1:
                        raise
                    else:
                        if hasattr(func, 'func_name'):  # Python 2
                            name = func.func_name
                        else:   # Python 3
                            name = func.__name__
                        logging.error("%s failed with %r", name, exc)
        return wrapper
    return decorate


def get_token(username, api_key):
    auth = {
        "RAX-KSKEY:apiKeyCredentials": {
            "username": username,
            "apiKey": api_key
        }
    }
    headers = {
        'Content-type': 'application/json'
    }
    data = {
        'auth': auth
    }

    req = requests.post(OS_AUTH_URL + '/tokens', headers=headers, json=data)
    req.raise_for_status()

    return req.json()


def get_service_catalog_from_token(token):
    return token['access']['serviceCatalog']


def list_compute_endpoints(service_catalog):
    compute_endpoints = {}

    for endpoints in service_catalog:
        if endpoints['type'] == 'compute':
            for endpoint in endpoints['endpoints']:
                compute_endpoints[endpoint['region']] = endpoint['publicURL']

    return compute_endpoints


def _req(method, url):
    headers = {
        'X-Auth-Token': TOKEN_ID,
        'Content-type': 'application/json'
    }
    req = requests.request(method, url, headers=headers, timeout=4.0)
    req.raise_for_status()

    logging.info("HTTP %s to %s took %d ms", method.upper(), req.url,
                 req.elapsed.microseconds/1000)

    # "204 No Content" has obviously no body
    if req.status_code != 204:
        return req.json()


@retry(EXC_TO_RETRY, 3)
def list_cloud_servers_by_endpoint(compute_endpoint):
    url = "%s/servers/detail" % compute_endpoint
    return _req('get', url)['servers']


def list_all_cloud_servers(compute_endpoints):
    servers = []
    pool = eventlet.GreenPool()

    def worker(region, endpoint):
        for srv in list_cloud_servers_by_endpoint(endpoint):
            servers.append((region, srv))

    for region, endpoint in compute_endpoints.items():
        pool.spawn(worker, region, endpoint)

    pool.waitall()
    return servers


def get_server_creation_time_delta(server):
    now = datetime.datetime.now(tz=iso8601.iso8601.UTC)
    abs_created = iso8601.parse_date(server['created'])
    return now - abs_created


def list_users():
    url = OS_AUTH_URL + '/users'

    return {
        user['id']: user['username'] for user in _req('get', url)['users']
    }


def parse_args():
    parser = argparse.ArgumentParser(
        description="Look for old VMs and optionnaly delete them.")
    parser.add_argument("--verbose", action="store_true",
                        help="Make output verbose")
    parser.add_argument("--delete", action="store_true",
                        help="Delete old VMs instead of just listing them")
    parser.add_argument("--duration", required=False, default=3*60, type=int,
                        help="Duration, in minutes, after which a VM is "
                             "considered old. (default: 180)")
    parser.add_argument("--rax-username", action=EnvDefault,
                        envvar='RAX_USERNAME', required=True,
                        help="Rackspace Cloud username (e.g rayenebenrayana). "
                             "(default: env['RAX_USERNAME']")
    parser.add_argument("--rax-api-key", action=EnvDefault,
                        envvar='RAX_API_KEY', required=True,
                        help="Rackspace Cloud API Key. "
                             "(default: env['RAX_API_KEY'])")

    return parser.parse_args()


def delete_server_if_name_matches(server):
    def get_server_url(server):
        for link in server['links']:
            if link['rel'] == 'self':
                return link['href']
        raise AttributeError("No URL to server found.")

    if server['name'].startswith('build-'):
        url = get_server_url(server)
        logging.info('Going to delete server %s at %s',
                     server['name'], url)
        _req('delete', url)


def main():
    global TOKEN_ID

    args = parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(asctime)s:%(message)s',
        level=log_level
    )

    token = get_token(args.rax_username, args.rax_api_key)
    service_catalog = get_service_catalog_from_token(token)
    compute_endpoints = list_compute_endpoints(service_catalog)

    TOKEN_ID = token['access']['token']['id']

    # Uncomment the following line to print the current `USERID_TO_USERNAME`
    # mapping. You need to have an admin token to do that.
    # import pprint; pprint.pprint(list_users())

    def get_and_process_old_servers(compute_endpoints):
        old_servers = []
        for region, srv in list_all_cloud_servers(compute_endpoints):
            if get_server_creation_time_delta(srv).seconds > args.duration*60:
                old_servers.append({
                    'name': srv['name'],
                    'region': region,
                    'owner': USERID_TO_USERNAME.get(srv['user_id'], 'Unknown'),
                    'created': humanize.naturaltime(
                        get_server_creation_time_delta(srv))
                })
                if args.delete:
                    delete_server_if_name_matches(srv)

        return old_servers

    old_servers = get_and_process_old_servers(compute_endpoints)
    if old_servers:
        print(tabulate.tabulate(old_servers, headers="keys"))

    sys.exit(0)

if __name__ == "__main__":
    logging.getLogger("requests.packages.urllib3").setLevel(logging.WARNING)
    requests.packages.urllib3.disable_warnings()
    main()
