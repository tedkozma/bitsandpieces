#!/usr/bin/python3

# Ted Kozma
# Get node status in the F5 pool, enable or disable it
# 2017

import sys, bigsuds
import re

import logging
# import suds.client
from suds.client import Client
# logging.getLogger('suds.client').setLevel(logging.DEBUG)
logging.getLogger('suds.client').setLevel(logging.CRITICAL)

import configparser

from datetime import datetime
from optparse import OptionParser

parser = OptionParser(usage='%prog [options]', version='%prog 1.0.' + re.search('(\d+)', '$LastChangedRevision: 1 $').group(1))
#parser.add_option("-V", "--verbose", action="store_true", dest="Verbose", default=False, help="Toggles printing extra information to the console [default: %default]")
parser.add_option("-A", "--action", dest="action", default="status", help="Action to perform: status or enable or disable [default: status]")
parser.add_option("-H", "--host", dest="f5host", default="f5.fnlocal.net", help="F5 host")
parser.add_option("-N", "--node", dest="node", help="Node name (as listed in F5)")
parser.add_option("-p", "--port", dest="port", default='80', help="Port (as listed in F5)")
parser.add_option("-P", "--pool", dest="pool", help="Name of the F5 pool")
parser.add_option("-U", "--user", dest="user", help="F5 login user")
parser.add_option("-W", "--password", dest="password", help="F5 login password")

(options, args) = parser.parse_args()

if options.node is None or options.pool is None or options.user is None or options.password is None:
  print("Missing arguments")
  parser.print_help()
  exit(-1)

user = options.user
password = options.password
f5host = options.f5host
pool = options.pool
pool_member = options.node
port = options.port

# this will will shut up the complaints about self-signed certificate
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# for possible debugging
def dump(obj):
  for attr in dir(obj):
    print("obj.%s = %s" % (attr, getattr(obj, attr)))

def status(node):
  try:
    status = pl.get_member_session_status(['/Common/' + pool], [[{'address': node,'port': port}]])
  except:
    print("Unable to get the status of the node %s in pool %s" % (node, pool))
    print(sys.exc_info()[1])
    sys.exit(2)
  return status

def enable(node):
  try:
    response = pl.set_member_session_enabled_state(['/Common/' + pool], [[{'address': node, 'port': port}]], [['STATE_ENABLED']])
  except:
    print("Unable to enable the node %s in pool %s" % (node, pool))
    print(sys.exc_info()[1])
    sys.exit(2)
  return response

def disable(node):
  try:
    response = pl.set_member_session_enabled_state(['/Common/' + pool], [[{'address': node, 'port': port}]], [['STATE_DISABLED']])
  except:
    print("Unable to enable the node %s in pool %s" % (node, pool))
    print(sys.exc_info()[1])
    sys.exit(2)
  return response

### Main ###
if __name__ == "__main__":

  b =  bigsuds.BIGIP(hostname = f5host, username = user,password = password)
  pl = b.LocalLB.Pool

  if options.action == 'status':
    pass
  elif options.action == 'enable':
    print("Enabling node %s in pool %s ..." % (pool_member, pool))
    res = enable(pool_member)
  elif options.action == 'disable':
    print("Disabling node %s in pool %s ..." % (pool_member, pool))
    res = disable(pool_member)

  st = status(pool_member)
  print("Node: %s   pool: %s  status: %s" % (pool_member, pool, st[0][0]))

# vim: ts=2 et sw=2 autoindent
