from ospurge import utils
from ospurge.resources import base
from ospurge.resources import glance


class Objects(base.ServiceResource, glance.ListImagesMixin):
    PRIORITY = 100

    def check_prerequisite(self):
        utils.call_until_true(
            lambda: self.list_images_by_owner() == []
        )

    def list(self):
        for container in self.cloud.list_containers():
            for obj in self.cloud.list_objects(container['name']):
                obj['container_name'] = container['name']
                yield obj

    def delete(self, resource):
        self.cloud.delete_object(resource['container_name'], resource['name'])

    def should_delete(self, resource):
        return True

    @staticmethod
    def to_string(resource):
        return "Object '{}' from Container '{}'".format(
            resource['name'], resource['container_name'])


class Containers(base.ServiceResource):
    PRIORITY = 101

    def list(self):
        return self.cloud.list_containers()

    def delete(self, resource):
        self.cloud.delete_container(resource['name'])

    def should_delete(self, resource):
        return True

    @staticmethod
    def to_string(resource):
        return "Container (name='{}')".format(resource['name'])
