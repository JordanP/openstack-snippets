#!/usr/bin/env python
import argparse
import collections
import re

import requests


def create_argument_parser():
    """
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Profile a Tempest run per OpenStack service."
    )
    parser.add_argument(
        "console_log",
        help="URL to a console.html.gz file"
    )
    return parser


def get_log_lines(log_url):
    """
    Get the text content of an URL

    :param log_url: URL to GET
    :type log_url: str
    :rtype: list[str]
    """
    response = requests.get(log_url)
    return response.content.decode().split('\n')


def get_test_names_and_durations(log_lines):
    """
    Extract test names and test durations from the logs

    :type log_lines: list[str]
    :rtype list[(str, float)]
    """
    name_and_duration = re.compile(r'(tempest\..*) \[(\d+\.\d+)s\]')
    for line in log_lines:
        match = name_and_duration.search(line)
        if match:
            yield match.group(1), float(match.group(2))


def get_service_name_from_test_name(test_name):
    """
    Given a test name, returns which OpenStack service is primarily tested.

    This is based partly on the location of the test in Tempest structure,
    partly on the knowledge of the test itself.

    :type test_name: str
    :rtype: str
    """
    nova_scenarios = [
        '.test_server_advanced_ops.',
        '.test_shelve_instance.',
        '.test_server_basic_ops.'
    ]
    cinder_scenarios = [
        '.test_snapshot_pattern.',
        '.test_stamp_pattern.',
        '.test_volume_boot_pattern.',
    ]
    if '.api.volume.' in test_name:
        return 'cinder'
    if '.api.compute.' in test_name:
        return 'nova'
    if any([scenario in test_name for scenario in nova_scenarios]):
        return 'nova'
    if any([scenario in test_name for scenario in cinder_scenarios]):
        return 'cinder'
    return 'other'


def main():
    """Print the run duration of all Cinder and Nova tests in Tempest."""
    parser = create_argument_parser()
    options = parser.parse_args()

    timings = collections.defaultdict(float)

    log_lines = get_log_lines(options.console_log)
    for name, duration in get_test_names_and_durations(log_lines):
        timings[get_service_name_from_test_name(name)] += duration

    print(timings)


if __name__ == "__main__":
    main()
