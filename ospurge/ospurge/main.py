#!/usr/bin/env python
import argparse
import copy
import importlib
import logging
import operator
import pkgutil
import sys
import traceback

import os_client_config
import ospurge.resources.base
import shade


def configure_logging(verbose: bool):
    log_level = logging.INFO if verbose else logging.WARNING
    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(asctime)s:%(message)s',
        level=log_level
    )
    logging.getLogger(
        'requests.packages.urllib3.connectionpool').setLevel(logging.WARNING)


def create_argument_parser():
    """
    :rtype: argparse.ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="Purge resources from an Openstack project."
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Makes output verbose"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="List project's resources"
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--purge-project", metavar="ID_OR_NAME",
        help="ID or Name of project to purge. This option requires "
             "to authenticate with admin credentials."
    )
    group.add_argument(
        "--purge-own-project", action="store_true",
        help="Purge resources of the project used to authenticate. Useful "
             "if you don't have the admin credentials of the cloud."
    )
    return parser


def replace_project_info_from_config(config, new_project_id):
    """
    :type config: dict
    :type new_project_id: str
    :rtype: dict
    """
    new_conf = copy.deepcopy(config)
    new_conf.pop('cloud', None)
    new_conf['auth'].pop('project_name', None)
    new_conf['auth'].pop('project_id', None)

    new_conf['auth']['project_id'] = new_project_id

    return new_conf


class CredentialsManager(object):
    def __init__(self, options, cloud_config):
        """
        :type options: argparse.Namespace
        :type cloud_config: os_client_config.config.OpenStackConfig
        """
        self.options = options
        self.revoke_role_after_purge = False

        if options.purge_own_project:
            self.cloud = shade.OpenStackCloud(
                cloud_config=cloud_config.get_one_cloud(argparse=options)
            )

        else:
            self.operator_cloud = shade.OperatorCloud(
                cloud_config=cloud_config.get_one_cloud(argparse=options)
            )

            project = self.operator_cloud.get_project(options.purge_project)
            if not project:
                raise Exception(
                    "Unable to find project '{}'".format(options.purge_project)
                )

            if self.operator_cloud.grant_role(
                    'Member', project=project['id'],
                    user=self.operator_cloud.keystone_session.get_user_id(),
            ):
                self.revoke_role_after_purge = True

            self.cloud = shade.OpenStackCloud(
                cloud_config=cloud_config.get_one_cloud(
                    **replace_project_info_from_config(
                        self.operator_cloud.cloud_config.config,
                        project['id']
                    )
                )
            )

        self.project_id = self.cloud.keystone_session.get_project_id()
        auth_args = self.cloud.cloud_config.get_auth_args()
        logging.warning(
            "Going to list and/or delete resources from project %s",
            auth_args.get('project_name') or auth_args.get('project_id')
        )


def get_all_resource_classes():
    iter_modules = pkgutil.iter_modules(
        ['ospurge/resources'], prefix='ospurge.resources.'
    )
    for (_, name, ispkg) in iter_modules:
        if not ispkg:
            importlib.import_module(name)

    return ospurge.resources.base.ServiceResource.__subclasses__()


def main():
    parser = create_argument_parser()

    cloud_config = os_client_config.OpenStackConfig()
    cloud_config.register_argparse_arguments(parser, sys.argv)

    options = parser.parse_args()
    configure_logging(options.verbose)

    creds_manager = CredentialsManager(
        options=options, cloud_config=cloud_config
    )
    resource_managers = [
        cls(creds_manager) for cls in get_all_resource_classes()
        ]
    resource_managers.sort(key=operator.methodcaller('priority'))

    for resource_manager in resource_managers:
        resource_manager.check_prerequisite()
        for resource in resource_manager.list():
            if resource_manager.should_delete(resource):
                logging.info(
                    "Going to delete %s", resource_manager.to_string(resource)
                )
                resource_manager.delete(resource)

    try:
        pass
    except KeyboardInterrupt:
        logging.warning("Caught keyboard interrupt. Canceling task...")
    except Exception:
        logging.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
