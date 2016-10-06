from ospurge.resources import base


class ListImagesMixin(object):
    def list_images_by_owner(self):
        images = self.cloud.list_images()
        return [i for i in images if i['owner'] == self.cleanup_project_id]


class Images(base.ServiceResource, ListImagesMixin):
    PRIORITY = 30

    def list(self):
        return self.list_images_by_owner()

    def should_delete(self, resource):
        return resource['owner'] == self.cleanup_project_id

    def delete(self, resource):
        self.cloud.delete_image(resource['id'])

    @staticmethod
    def to_string(resource):
        return "Image (id='{}', name='{}')".format(
            resource['id'], resource['name'])
