import sys

from cinder import objects
from oslo_config import cfg
from cinder import version
from cinder.common import config
from cinder import rpc

CONF = cfg.CONF


objects.register_all()
CONF(sys.argv[1:], project='cinder',
     version=version.version_string(),
     default_config_files=['/etc/cinder/cinder.conf', '/etc/cinder/api-paste.ini'])
config.set_middleware_defaults()
rpc.init(CONF)

import cinder.api.v2.router
router = cinder.api.v2.router.APIRouter()

print(router.map)
