from ospurge.resources import base


class Servers(base.ServiceResource):
    PRIORITY = 5

    def list(self):
        return self.cloud.list_servers()

    def delete(self, resource):
        self.cloud.delete_server(resource['id'])

    @staticmethod
    def to_string(resource):
        return "VM (id='{}', name='{}')".format(
            resource['id'], resource['name'])
