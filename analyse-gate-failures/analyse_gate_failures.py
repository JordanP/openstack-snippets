#!/usr/bin/env python3.5
import argparse
import collections
import datetime
import json

import requests

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
SINCE = datetime.date.today() - datetime.timedelta(days=30)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Print which jobs are responsible for Gate failures',
    )

    parser.add_argument('--project', required=True,
                        help='Project for which to analyse Gate failures.')

    return parser.parse_args()


# This represents a Gerrit comment
Comment = collections.namedtuple(
    'Comment', ['date', 'number', 'subject', 'message']
)


def get_changes_of_interest(project):
    """For a given project, get the Gerrit changes of interest.

    For a given project, get all the recent changes where at least one
    Gate failure happened.
    """
    search = ('reviewer:"Jenkins" AND comment:"Verified-2"'
              'AND project:"%s" AND since:%s' % (project, SINCE))

    # Include review messages in query
    query = ("https://review.openstack.org/changes/?q=%s&"
             "o=MESSAGES&o=DETAILED_ACCOUNTS" % search)
    r = requests.get(query)
    return json.loads(r.text[4:])


def get_all_gate_failures_for_change(change):
    """For a given change, yields all the gate failure comments."""
    for msg in change['messages']:
        if 'author' not in msg or msg['author']['name'] != 'Jenkins':
            continue

        if 'Verified-2' not in msg['message']:
            continue

        # https://review.openstack.org/Documentation/rest-api.html#timestamp
        date = msg['date'].split('.')[0]  # drop nanoseconds
        date = datetime.datetime.strptime(date, TIME_FORMAT)
        yield date, msg['message']


def get_all_gate_failures_for_project(project):
    """For a given project, returns all the gate failure comments."""
    gate_failure_comments = []

    for change in get_changes_of_interest(project):
        for date, message in get_all_gate_failures_for_change(change):
            gate_failure_comments.append(
                Comment(date, change['_number'], change['subject'], message)
            )

    return sorted(
        gate_failure_comments, key=lambda comment: comment.date, reverse=True
    )


def compute_stats_per_job(comment, stats):
    """Given a Gate failure comment, extract which job(s) failed."""
    for line in comment.message.splitlines():
        if line.startswith("* ") or line.startswith("- "):
            job = line.split(' ')[1]

            # If this is the first time we see this job then init the stats
            if job not in stats:
                stats[job] = {'ok': 0, 'ko': 0, 'ko_rate': 0}

            if " : SUCCESS" in line or " : FAILURE" in line:
                if " : SUCCESS" in line:
                    stats[job]['ok'] += 1
                elif " : FAILURE" in line:
                    stats[job]['ko'] += 1

                stats[job]['ko_rate'] = (stats[job]['ko'] / (
                    stats[job]['ko'] + stats[job]['ok'])) * 100


def main():
    args = parse_args()

    # Dict of job_name => job_statistics
    jobs_stats = collections.defaultdict(dict)

    gate_failure_comments = get_all_gate_failures_for_project(args.project)
    print("Jenkins left %d 'Verified-2' messages on project %s" % (
        len(gate_failure_comments), args.project))

    for gate_failure_comment in gate_failure_comments:
        compute_stats_per_job(gate_failure_comment, jobs_stats)

    print("Note: the statistics don't show the absolute failure rate of a "
          "given job, but the failure rate knowing there's a Gate failure "
          "(i.e we don't account for changes where everything went smooth)")
    print("Note: jobs that ran less than 10 times are not displayed here.")

    for job_name, job_stats in sorted(
            jobs_stats.items(), key=lambda x: x[1]['ko_rate'], reverse=True
    ):
        # If we don"t have enough data to display relevant stats.
        if job_stats.get('ok', 0) + job_stats.get('ko', 0) < 10:
            continue

        print("{job_name:60} {ko_rate:04.1f}% "
              "({ok}/{ko})".format(job_name=job_name, **jobs_stats[job_name]))


if __name__ == '__main__':
    main()
