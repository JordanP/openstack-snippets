from ospurge import utils
from ospurge.resources import base


class FloatingIPs(base.ServiceResource):
    PRIORITY = 9

    def check_prerequisite(self):
        # We can't delete a FIP if it attached
        utils.call_until_true(
            lambda: self.cloud.list_servers() == []
        )

    def list(self):
        return self.cloud.list_floating_ips()

    def delete(self, resource):
        self.cloud.delete_floating_ip(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Floating IP (id='{}')".format(resource['id'])


class RouterInterfaces(base.ServiceResource):
    PRIORITY = 15

    def check_prerequisite(self):
        utils.call_until_true(
            lambda: self.cloud.list_servers() == []
        )

    def list(self):
        return self.cloud.list_ports(
            filters={'device_owner': 'network:router_interface'})

    def delete(self, resource):
        self.cloud.remove_router_interface({'id': resource['device_id']},
                                           port_id=resource['id'])

    @staticmethod
    def to_string(resource):
        return "Router Interface (id='{}', router_id='{}')".format(
            resource['id'], resource['device_id'])


class Routers(base.ServiceResource):
    PRIORITY = 16

    def list(self):
        return self.cloud.list_routers()

    def delete(self, resource):
        self.cloud.delete_router(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Router (id='{}', name='{}')".format(
            resource['id'], resource['name'])


class ListPortsMixin(object):
    def list_non_dhcp_ports(self):
        ports = self.cloud.list_ports(
            filters={'tenant_id': self.cleanup_project_id}
        )
        return [p for p in ports if p['device_owner'] != 'network:dhcp']


class Ports(base.ServiceResource, ListPortsMixin):
    PRIORITY = 17

    def list(self):
        return self.list_non_dhcp_ports()

    def delete(self, resource):
        self.cloud.delete_port(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Port (id='{}', network_id='{})'".format(
            resource['id'], resource['network_id']
        )


class Networks(base.ServiceResource, ListPortsMixin):
    PRIORITY = 18

    def check_prerequisite(self):
        utils.call_until_true(
            lambda: self.list_non_dhcp_ports() == []
        )

    def list(self):
        return self.cloud.list_networks()

    def delete(self, resource):
        self.cloud.delete_network(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Network (id='{}', name='{}')".format(
            resource['id'], resource['name'])


class SecurityGroups(base.ServiceResource):
    PRIORITY = 18

    def list(self):
        return [
            sg for sg in self.cloud.list_security_groups()
            if sg['name'] != 'default'
            ]

    def delete(self, resource):
        self.cloud.delete_security_group(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Security Group (id='{}', name='{}')".format(
            resource['id'], resource['name']
        )
