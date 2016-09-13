#!/usr/bin/env python
import argparse
import collections
import gzip
import logging
import os.path
import re
import sys
import traceback
import typing
import urllib.parse
import urllib.request

from misc import REPLACEMENTS_DICT


def readlines_from_log(log: str) -> typing.Iterator[str]:
    if os.path.isfile(log):
        logging.info("Reading gunzip archive from file: %s", log)
        f = gzip.GzipFile(filename=log)
    else:
        logging.info("Reading gunzip archive from URL: %s", log)
        req = urllib.request.Request(
            log, headers={'Accept-Encoding': 'gzip'}
        )
        page = urllib.request.urlopen(req)
        f = gzip.GzipFile(fileobj=page)
    return (
        str(line) for line in f
    )


def extract_urls(lines: typing.Iterable[str]):
    # Match IP based URLs.
    regex = r"(?P<verb>GET|POST|PUT|DELETE|PATCH|HEAD|COPY) (" \
            r"?P<url>https?://[0-9\.]{7,15}[^\s'\"]+)"
    regex = re.compile(regex)
    for line in lines:
        yield from regex.finditer(line)


def normalize_url(url: str) -> str:
    for regex, repl in REPLACEMENTS_DICT.items():
        url = regex.sub(repl, url)
    return url


def get_service_from_url(url: str) -> typing.Tuple[str, str]:
    parts = urllib.parse.urlparse(url)
    if parts.port == 5000 or '/identity_v2_admin/' in parts.path or \
                    '/identity/' in parts.path:
        return ('keystone', parts.path)
    elif parts.port == 8774:
        return ('nova', parts.path)
    elif parts.port == 8776:
        return ('cinder', parts.path)
    elif parts.port == 8080:
        return ('swift', parts.path)
    elif parts.port == 9292:
        return ('glance', parts.path)
    elif parts.port == 9696:
        return ('neutron', parts.path)
    else:
        raise ValueError('Unknown service: {}'.format(url))


def get_routes_by_service(matches) -> typing.Set:
    routes_by_service = collections.defaultdict(set)

    for match in matches:
        verb, url = match.group('verb'), normalize_url(match.group('url'))
        service, path = get_service_from_url(url)
        routes_by_service[service].add((verb, path))

    return routes_by_service


def configure_logging(verbose: bool):
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(asctime)s:%(message)s',
        level=log_level
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='A CLI tool to list all the OpenStack routes tested by '
                    'Tempest.'
    )
    parser.add_argument('--verbose', action="store_true",
                        help="Make output verbose")
    parser.add_argument(
        '--service', action='append',
        help="Only get the routes belonging to this service. Can be specified "
             "multiple times (--service nova --service swift)."
    )
    parser.add_argument('tempest_logfile',
                        help='URL or path to a Tempest log file')

    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.verbose)

    try:
        lines = readlines_from_log(args.tempest_logfile)
        routes_by_service = get_routes_by_service(extract_urls(lines))
        for service, routes in routes_by_service.items():
            if args.service is None or service in args.service:
                for route in routes:
                    print(route)
    except KeyboardInterrupt:
        logging.warning("Caught keyboard interrupt. Exiting...")
    except Exception:
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == 'main':
    main()
