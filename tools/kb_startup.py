#!/usr/bin/ipython -i

OME_HOST = 'localhost'
OME_USER = 'root'
OME_PASS = 'romeo'

import sys
from bl.vl.kb import KnowledgeBase

BaseProxy = KnowledgeBase(driver='omero')

class Proxy(BaseProxy):
  def get_objects_dict(self, klass):
    return dict((o.label, o) for o in super(Proxy, self).get_objects(klass))

kb = Proxy(OME_HOST, OME_USER, OME_PASS)

def cleanup():
  print "# disconnecting the kb"
  kb.disconnect()

sys.exitfunc = cleanup

print
print "### KB ENV PRELOADED ###"
print "# knowledge base: kb"
print "# extra method: kb.get_objects_dict"
print "########################"
