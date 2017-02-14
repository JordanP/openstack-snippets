#!/usr/bin/python3
"""
This script demonstrates a race condition with HTTP/1.1 keepalive
"""
import decimal
import json
import subprocess
import time
import threading

import requests
requests.packages.urllib3.disable_warnings()

CREDS = json.loads(subprocess.check_output(
    "openstack --os-cloud devstack token issue -f json".split(),
).decode())
URL = 'https://10.0.1.44:8774/v2/%s/servers/detail' % (CREDS['project_id'])


def decimal_range(x, y, jump):
    x = decimal.Decimal(x)
    y = decimal.Decimal(y)
    jump = decimal.Decimal(jump)
    while x < y:
        yield float(x)
        x += jump


def get(exit):
    for delay in decimal_range(4.95, 4.96, 0.005):
        session = requests.Session()

        if exit.is_set():
            return

        for i in range(10):

            if exit.is_set():
                return

            time.sleep(delay)
            headers = {
                'User-Agent': 'timeout-race/%s' % i,
                'X-Auth-Token': CREDS['id']
            }
            try:
                session.get(URL, verify=False, headers=headers)
            except Exception as e:
                print(e)
                exit.set()


threads = []
exit = threading.Event()
for i in range(50):
    threads.append(threading.Thread(target=get,args=(exit,)))

for thread in threads:
    thread.start()

for thread in threads:
    thread.join()
