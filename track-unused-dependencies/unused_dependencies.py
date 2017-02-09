#!/usr/bin/env python3
import contextlib
import json
import logging
import os
import random
import subprocess
import tempfile

import requests

logging.basicConfig(level=logging.INFO)

tracked_dependency = 'mox3'

gerrit_url = 'https://review.openstack.org/'
git_url = 'https://git.openstack.org/'
hound_search_api = 'http://codesearch.openstack.org/api/v1/search'


@contextlib.contextmanager
def working_directory(path):
    prev_cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev_cwd)


def is_in_openstack_namespace(project_name):
    # Only interested in openstack namespace (e.g. not retired stackforge, etc)
    return project_name.startswith('openstack/')


def get_requirements_for_project(project_name):
    if "openstack/deb-" in project_name:
        return None

    if "openstack/xstatic-" in project_name:
        return None

    requirements = []
    for dependencies_file in ('requirements.txt', 'test-requirements.txt'):
        url = git_url + "cgit/%s/plain/%s" % (project_name, dependencies_file)
        response = requests.get(url)
        if response.status_code != 200:
            logging.debug(
                "Project %s has no %s file: HTTP %d", project_name,
                dependencies_file, response.status_code
            )
        else:
            requirements.extend(response.text.splitlines())

    return requirements


def is_listed_as_dependency(tracked_dependency, project_name):
    requirements = get_requirements_for_project(project_name)

    if requirements is None:
        return False

    if any([req.startswith(tracked_dependency) for req in requirements]):
        logging.info(
            "Project %s has %s listed in its dependencies",
            project_name, tracked_dependency
        )
        return True
    else:
        logging.info(
            "Project %s doesn't have %s listed in its dependencies",
            project_name, tracked_dependency
        )
        return False


def is_actually_using_dependency(tracked_dependency, project_name,
                                 search_results):
    for project_name, project_search in search_results.items():
        for matches in project_search['Matches']:
            for match in matches['Matches']:
                if ('import %s' % tracked_dependency in match['Line'] or
                        'from %s' % tracked_dependency in match['Line']):
                    logging.info(
                        "Project %s actually uses %s: '%s' in %s",
                        project_name, tracked_dependency, match['Line'],
                        matches['Filename']
                    )
                    return True
    logging.info(
        "Project %s doesn't seem to use %s", project_name,
        tracked_dependency
    )
    return False


def remove_line_from_file(line, file):
    line_found = False
    new_file_content = []

    for l in open(file).readlines():
        if l.startswith(line):
            line_found = True
        else:
            new_file_content.append(l)

    if line_found:
        with open(file, 'w') as f:
            f.write(''.join(new_file_content))

    return line_found


def git_clone_project(project_name):
    if not os.path.exists(short_project_name):
        logging.info("Going to clone %s", project_name)
        subprocess.check_call([
            "git", "clone", git_url + project_name
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def git_commit(tracked_dependency):
    msg = ("Remove useless dependency on %s in requirements file\n\n"
           "%s is listed in the Python requirements file but "
           "it seems\nit's not actually used.") % (
            tracked_dependency, tracked_dependency)
    with tempfile.NamedTemporaryFile() as fp:
        fp.write(msg.encode())
        fp.flush()
        subprocess.check_call(["git", "commit", "-F", fp.name])


def remove_dependency_from_requirements_file(tracked_dependency, file):
    if os.path.exists(file):
        if remove_line_from_file(tracked_dependency, file):
            subprocess.check_call(["git", "add", file])
            return True
    return False


def run_tox(project_name):
    completed_process = subprocess.run(
        ['tox', '-l'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    for target in ('py27', 'py34', 'py35'):
        if target in completed_process.stdout.decode():
            logging.info("Running tox -e %s on project %s", target,
                         project_name)
            tox_run = subprocess.run(["tox", "-e", target])
            return tox_run.returncode == 0

r = requests.get(gerrit_url + 'projects/')
projects = sorted(filter(is_in_openstack_namespace, json.loads(r.text[4:])))


for project_name in random.sample(projects, len(projects)):
    if not is_listed_as_dependency(tracked_dependency, project_name):
        continue

    short_project_name = project_name.split('/')[1]  # openstack/ prefix
    search = requests.get(
        hound_search_api,
        params= {
            'repos': short_project_name,
            'q': tracked_dependency,
            'ctx': 0
        }
    ).json()['Results']

    if is_actually_using_dependency(tracked_dependency, project_name, search):
        continue

    git_clone_project(project_name)

    with working_directory(short_project_name):
        if not os.path.exists('.gitreview'):
            continue

        subprocess.check_call(["git", "review", "-s"])
        r1 = remove_dependency_from_requirements_file(
            tracked_dependency, 'requirements.txt'
        )
        r2 = remove_dependency_from_requirements_file(
            tracked_dependency, 'test-requirements.txt'
        )
        if r1 or r2:
            if run_tox(project_name):
                git_commit(tracked_dependency)
                logging.info("Going to call git review for project %s",
                             project_name)
                #subprocess.check_call(
                #    ["git", "review", "-t", "remove_mox3"])



# for d in $(echo */); do cd $d; git reset --hard origin/master; cd -; done





