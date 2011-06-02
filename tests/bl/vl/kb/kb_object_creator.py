import os, unittest, time
import itertools as it
from bl.vl.kb import KBError
from bl.vl.kb import KnowledgeBase as KB
import bl.vl.utils as vlu

import logging
logging.basicConfig(level=logging.WARN)
logger = logging.getLogger()

class KBObjectCreator(unittest.TestCase):
  def __init__(self, label):
    self.kb = 'THIS_IS_A_DUMMY'
    self.kill_list = 'THIS_IS_A_DUMMY'
    super(KBObjectCreator, self).__init__(label)

  def configure_object(self, o, conf):
    for k in conf.keys():
      logger.debug('o[%s] setting %s to %s' % (o.id, k, conf[k]))
      setattr(o, k, conf[k])
    conf['id'] = o.id

  def create_study(self):
    pars = {'label' : 'foobar_%f' % time.time(),
            'description' : 'this is a fake desc'}
    s = self.kb.factory.create(self.kb.Study, pars)
    pars['id'] = s.id
    return pars, s

  def create_device(self):
    conf = {'label' : 'foo-%f' % time.time(),
            'maker' : 'foomaker',
            'model' : 'foomodel',
            'release' : '%f' % time.time(),
            'physicalLocation' : 'HERE_THERE_EVERYWHERE'}
    device = self.kb.factory.create(self.kb.Device, conf)
    conf['id'] = device.id
    return conf, device

  def create_action_setup(self, action_setup=None):
    conf = {'label' : 'asetup-%f' % time.time(),
            'conf' : '{"param1": "foo"}'}
    action_setup = (action_setup if action_setup
                    else self.kb.factory.create(self.kb.ActionSetup,
                                                conf))
    conf['id'] = action_setup.id
    return conf, action_setup

  def create_action(self, action_klass=None, target=None):
    dev_conf, device = self.create_device()
    self.kill_list.append(device.save())
    #--
    asu_conf, asetup = self.create_action_setup()
    self.kill_list.append(asetup.save())
    #--
    stu_conf, study = self.create_study()
    self.kill_list.append(study.save())
    #--
    conf = {'setup' : asetup,
            'device': device,
            'actionCategory' : self.kb.ActionCategory.IMPORT,
            'operator' : 'Alfred E. Neumann',
            'context'  : study,
            'description' : 'description ...',
            'target' : target
            }
    action_klass = action_klass if action_klass else self.kb.Action
    action = self.kb.factory.create(action_klass, conf)
    return conf, action

  def create_action_on_vessel(self, vessel=None):
    if not vessel:
      vconf, vessel = self.create_vessel()
      self.kill_list.append(vessel.save())
    return self.create_action(action_klass=self.kb.ActionOnVessel,
                              target=vessel)

  def create_action_on_data_sample(self, data_sample=None):
    if not data_sample:
      vconf, data_sample = self.create_data_sample()
      self.kill_list.append(data_sample.save())
    return self.create_action(action_klass=self.kb.ActionOnDataSample,
                              target=data_sample)

  def create_action_on_data_collection_item(self, dc_item=None):
    if not dc_item:
      dcconf, dc_item = self.create_data_collection_item()
      self.kill_list.append(dc_item.save())
    return self.create_action(action_klass=self.kb.ActionOnDataCollectionItem,
                              target=dc_item)

  def create_action_on_action(self, action=None):
    if not action:
      aconf, action = self.create_action()
      self.kill_list.append(action.save())
    return self.create_action(action_klass=self.kb.ActionOnAction,
                              target=action)

  #----------------------------------------------------------------------
  def create_vessel_conf_helper(self, action=None):
    if not action:
      aconf, action = self.create_action()
      self.kill_list.append(action.save())
    #--
    conf = {
      'currentVolume' : 0.2,
      'initialVolume' : 0.2,
      'content'       : self.kb.VesselContent.BLOOD,
      'status'        : self.kb.VesselStatus.CONTENTUSABLE,
      'action'        : action
      }
    return conf

  def create_vessel(self, action=None):
    conf = self.create_vessel_conf_helper(action)
    v = self.kb.factory.create(self.kb.Vessel, conf)
    return conf, v

  def create_tube(self, action=None):
    conf = self.create_vessel_conf_helper(action)
    conf['label'] = 'tl-%s'  % time.time()
    v = self.kb.factory.create(self.kb.Tube, conf)
    return conf, v

  #----------------------------------------------------------------------
  def create_data_sample_conf_helper(self, action=None):
    if not action:
      aconf, action = self.create_action()
      self.kill_list.append(action.save())
    #--
    conf = {
      'status' : self.kb.DataSampleStatus.USABLE,
      'action' : action
      }
    return conf

  def create_data_sample(self, action=None):
    conf = self.create_data_sample_conf_helper(action)
    ds = self.kb.factory.create(self.kb.DataSample, conf)
    return conf, ds

  def create_affymetrix_cel(self, action=None):
    conf = self.create_data_sample_conf_helper(action)
    conf['arrayType'] = self.kb.AffymetrixCelArrayType.GenomeWideSNP_6
    ds = self.kb.factory.create(self.kb.AffymetrixCel, conf)
    return conf, ds

  def create_data_object(self, data_sample=None):
    if not data_sample:
      dconf, data_sample = self.create_data_sample()
      self.kill_list.append(data_sample.save())
    conf = {'sample' : data_sample}
    do = self.kb.factory.create(self.kb.DataObject, conf)
    return conf, do

  #----------------------------------------------------------------------
  def create_collection_conf_helper(self, action=None):
    if not action:
      aconf, action = self.create_action()
      self.kill_list.append(action.save())
    #--
    conf = {
      'label'  : 'col-%s' % time.time(),
      'action' : action
      }
    return conf

  def create_container(self, action=None):
    conf = self.create_collection_conf_helper(action)
    conf['barcode'] =  '9898989-%s' % time.time()
    c = self.kb.factory.create(self.kb.Container, conf)
    return conf, c

  def create_slotted_container(self, action=None):
    conf = self.create_collection_conf_helper(action)
    conf['numberOfSlots'] =  16
    conf['barcode'] =  '9898989-%s' % time.time()
    c = self.kb.factory.create(self.kb.SlottedContainer, conf)
    return conf, c

  def create_titer_plate(self, action=None):
    conf = self.create_collection_conf_helper(action)
    conf['rows'] =  8
    conf['columns'] =  12
    conf['barcode'] =  '9898989-%s' % time.time()
    c = self.kb.factory.create(self.kb.TiterPlate, conf)
    return conf, c

  def create_data_collection(self, action=None):
    conf = self.create_collection_conf_helper(action)
    c = self.kb.factory.create(self.kb.DataCollection, conf)
    return conf, c

  def create_data_collection_item(self, data_collection=None,
                                  data_sample=None):
    if not data_collection:
      dconf, data_collection = self.create_data_collection()
      self.kill_list.append(data_collection.save())
    if not data_sample:
      dconf, data_sample = self.create_data_sample()
      self.kill_list.append(data_sample.save())
    conf = {'dataSample' : data_sample,
            'dataCollection' : data_collection}
    dci = self.kb.factory.create(self.kb.DataCollectionItem, conf)
    return conf, dci

  #----------------------------------------------------------------------
  def create_snp_markers_set(self, action=None):
    conf = {'maker' : 'snp-foomaker',
            'model' : 'snp-foomodel',
            'release' : 'snp-rel-%f' % time.time(),
            'markersSetVID' : vlu.make_vid()}
    result = self.kb.SNPMarkersSet(maker=conf['maker'], model=conf['model'], release=conf['release'],
                                    set_vid=conf['markersSetVID'])
    sconf, res = self.create_result(result=result, action=action)
    conf.update(sconf)
    return conf, res

