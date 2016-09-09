#!/usr/bin/env python
import argparse
import asyncio
import json
import logging
import os
import sys
import traceback
import urllib

from pulsar.apps import http
from pulsar.apps.http import HTTPDigestAuth
from pulsar.utils import exceptions
from pulsar.utils.httpurl import Headers


class GerritSession(http.HttpClient):
    def __init__(self, url, username, password, **kwargs):
        super(GerritSession, self).__init__(
            headers=Headers([('Content-Type', 'application/json')]),
            **kwargs
        )
        self.url = url
        self.auth = HTTPDigestAuth(username, password)

    def __getattribute__(self, name):
        if name in ('post', 'get', 'delete'):
            def method(url, **kwargs):
                return super(GerritSession, self).__getattribute__(name)(
                    '/'.join([self.url, url]), auth=self.auth, **kwargs)

            return method
        return super(GerritSession, self).__getattribute__(name)


class EnvDefault(argparse.Action):  # pylint: disable=R0903
    """# From Russell Heilling: http://stackoverflow.com/a/10551190"""

    def __init__(self, envvar, required=True, default=None, **kwargs):
        # Overriding default with environment variable if available
        if envvar in os.environ:
            default = os.environ[envvar]
        if required and default:
            required = False
        super(EnvDefault, self).__init__(default=default, required=required,
                                         **kwargs)


def parse_args():
    parser = argparse.ArgumentParser(
        description='A CLI tool to remove yourself from the list of'
                    'reviewers.',
    )
    parser.add_argument('--verbose', action="store_true",
                        help="Make output verbose")
    parser.add_argument('--url', required=True, action=EnvDefault,
                        envvar="GERRIT_URL", help='Gerrit URL')
    parser.add_argument('--username', required=True, action=EnvDefault,
                        envvar="GERRIT_USERNAME", help='Gerrit username')
    parser.add_argument('--password', required=True, action=EnvDefault,
                        envvar="GERRIT_PASSWORD", help='Gerrit password')
    parser.add_argument('--concurrency', type=int, default=4,
                        help='Maximum concurrent requests', metavar='N')

    return parser.parse_args()


async def list_changes(session, **params):
    url = '/a/changes/'
    if params:
        url += "?{}".format(urllib.parse.urlencode(params))

    response = await session.get(url)
    try:
        response.raise_for_status()
    except exceptions.HttpRequestException as exc:
        logging.error('HTTP request error: %d', exc.response.status_code)
        raise

    changes = json.loads(response.text()[4:])
    logging.info("Will remove reviewer from %d changes", len(changes))
    return changes


async def remove_reviewer(session, semaphore, change_id, account_id):
    url = '/a/changes/{}/reviewers/{}'.format(change_id, account_id)
    async with semaphore:
        response = await session.delete(url, data={'notify': 'NONE'})
    response.raise_for_status()
    logging.info("Removed '%s' from review '%s': %d", account_id, change_id,
                 response.status_code)


async def remove_from_all_reviews(session, max_concurrency, **kwargs):
    semaphore = asyncio.Semaphore(max_concurrency)
    changes = await list_changes(session, **kwargs)
    to_do = [remove_reviewer(session, semaphore, change['change_id'], 'self')
             for change in changes]
    if to_do:
        await asyncio.wait(to_do)


def configure_logging(verbose):
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(asctime)s:%(message)s',
        level=log_level
    )


def main():
    args = parse_args()
    configure_logging(args.verbose)
    session = GerritSession(args.url, args.username, args.password)

    filter = {
        'q': 'reviewer:self AND status:open AND age:1mon',
    }

    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(remove_from_all_reviews(
            session, args.concurrency, **filter)
        )
    except KeyboardInterrupt as e:
        logging.warning("Caught keyboard interrupt. Canceling task...")
        loop.stop()
    except Exception:
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == 'main':
    main()
