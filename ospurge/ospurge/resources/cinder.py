from ospurge import utils
from ospurge.resources import base


class Snapshots(base.ServiceResource):
    PRIORITY = 10

    def list(self):
        return self.cloud.list_volume_snapshots()

    def delete(self, resource):
        self.cloud.delete_volume_snapshot(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Snapshot (id='{}', name='{}')".format(
            resource['id'], resource['name'])


class Volumes(base.ServiceResource):
    PRIORITY = 15

    def check_prerequisite(self):
        utils.call_until_true(
            lambda: self.cloud.list_volume_snapshots() == []
        )

    def list(self):
        return self.cloud.list_volumes()

    def should_delete(self, resource):
        attr = 'os-vol-tenant-attr:tenant_id'
        return resource[attr] == self.cleanup_project_id

    def delete(self, resource):
        self.cloud.delete_volume(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Volume (id='{}', name='{}')".format(
            resource['id'], resource['name'])
