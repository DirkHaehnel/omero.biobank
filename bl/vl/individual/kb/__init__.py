"""
Interfaces for the application-side view of the object model.

Individual kb drivers should implement these interfaces.
"""

import sys
#--
#
# The actual KnowledgeBase front-end
#
#--
driver_table = { 'omero' : 'bl.vl.individual.kb.drivers.omero' }

def KnowledgeBase(driver):
  try:
    __import__(driver_table[driver])
    driver_module = sys.modules[driver_table[driver]]
  except KeyError, e:
    print 'Driver %s is unknown' % driver
    assert(False)
  return driver_module.driver

#--
#
# Interface definitions
#
#--

class KBError(Exception):
  pass


class Individual(object):

  def __init__(self):
    raise NotImplementedError

class Enrollment(object):

  def __init__(self):
    raise NotImplementedError



class ActionOnIndividual(object):

  def __init__(self):
    raise NotImplementedError


