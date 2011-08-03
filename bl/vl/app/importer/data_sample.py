"""
Import of Data samples
======================

Will read in a tsv file with the following columns::

  study  label source device device_type scanner options
  ASTUDY foo01 v03909 v9309  Chip        v99020  celID=0009099090
  ASTUDY foo02 v03909 v99022 Scanner     v99022  conf1=...,conf2=...
  ....

In this example, the first line corresponds to a dataset obtained by
using chip v9309 on scanner v99020, while the second datasample has
been obtained using a technology directly using a scanner, e.g., an
Illumina HiSeq 2000. The '''scanner''' column is there as a
convenience to support a more detailed description of a chip based
acquisition.

The general strategy is to decide what data objects should be
instantiated by looking at the chip column and to its corresponding
maker,model,release.

The optional column '''scanner''', the vid of the scanner device, is
used in cases, such as affymetrix genotyping where it is relevant.

It is also possible to import DataSample(s) that are the results of
processing on other DataSample(s). This is an example::

  study  label source device device_type     options
  ASTUDY foo01 v03909 v99021 SoftwareProgram conf1=...,conf2=...
  ASTUDY foo02 v03909 v99021 SoftwareProgram conf1=...,conf2=...
  ....


"""

from core import Core, BadRecord
import csv, json
import itertools as it

#-----------------------------------------------------------------------------

def conf_affymetrix_cel_6(kb, r, a, options):
  conf = {'label' : r['label'],
          'status' : kb.DataSampleStatus.USABLE,
          'action' : a,
          'arrayType' : kb.AffymetrixCelArrayType.GENOMEWIDESNP_6,
          }
  if 'celID' in options:
    conf['celID'] = options['celID']
  return kb.factory.create(kb.AffymetrixCel, conf)

def conf_illumina_beadchip_1m_duo(kb, r, a, options):
  conf = {'label' : r['label'],
          'status' : kb.DataSampleStatus.USABLE,
          'action' : a,
          'assayType' : kb.IlluminaBeadChipAssayType.HUMAN1M-DUO
          }
  return kb.factory.create(kb.IlluminaBeadChip, conf)

def conf_illumina_beadchip_immuno(kb, r, a, options):
  conf = {'label' : r['label'],
          'status' : kb.DataSampleStatus.USABLE,
          'action' : a,
          'assayType' : kb.IlluminaBeadChipAssayType.IMMUNOCHIP
          }
  return kb.factory.create(kb.IlluminaBeadChip, conf)


data_sample_configurator = {
  ('Affymetrix', 'Genome-Wide Human SNP Array', '6.0') : conf_affymetrix_cel_6,
  ('Illumina', 'BeadChip', 'HUMAN1M-DUO') : conf_illumina_beadchip_1m_duo,
  ('Illumina', 'BeadChip', 'IMMUNOCHIP') : conf_illumina_beadchip_1m_duo,
  }

class Recorder(Core):
  def __init__(self, study_label=None,
               host=None, user=None, passwd=None, keep_tokens=1,
               batch_size=1000, operator='Alfred E. Neumann',
               action_setup_conf=None,
               logger=None):
    super(Recorder, self).__init__(host, user, passwd, keep_tokens,
                                   study_label, logger=logger)
    self.batch_size = batch_size
    self.action_setup_conf = action_setup_conf
    self.operator = operator
    self.preloaded_devices  = {}
    self.preloaded_scanners = {}
    self.preloaded_sources  = {}
    self.preloaded_data_samples = {}

  def record(self, records, otsv):
    def records_by_chunk(batch_size, records):
      offset = 0
      while len(records[offset:]) > 0:
        yield records[offset:offset+batch_size]
        offset += batch_size

    if len(records) == 0:
      self.logger.warn('no records')
      return

    study = self.find_study(records)
    self.source_klass = self.find_source_klass(records)
    self.device_klass = self.find_device_klass(records)

    self.preload_scanners()
    self.preload_devices()
    self.preload_sources()
    self.preload_data_samples()

    records = self.do_consistency_checks(records)
    if not records:
      self.logger.warn('no records')
      return

    for i, c in enumerate(records_by_chunk(self.batch_size, records)):
      self.logger.info('start processing chunk %d' % i)
      self.process_chunk(otsv, c, study)
      self.logger.info('done processing chunk %d' % i)

  def find_source_klass(self, records):
    return self.find_klass('source_type', records)

  def find_device_klass(self, records):
    return self.find_klass('device_type', records)

  def preload_devices(self):
    self.preload_by_type('devices', self.device_klass, self.preloaded_devices)

  def preload_scanners(self):
    self.preload_by_type('scanners', self.kb.Scanner, self.preloaded_scanners)

  def preload_sources(self):
    self.preload_by_type('sources', self.source_klass, self.preloaded_sources)

  def preload_data_samples(self):
    self.logger.info('start preloading data_samples')
    objs = self.kb.get_objects(self.DataSample)
    for o in objs:
      assert not o.label in self.preloaded_data_samples
      self.preloaded_data_samples[o.label] = o
    self.logger.info('done preloading data_samples')

  #----------------------------------------------------------------
  def do_consistency_checks(self, records):
    self.logger.info('start consistency checks')
    #--
    k_map = {}
    good_records = []
    for i, r in enumerate(records):
      reject = ' Rejecting import of row %d.' % i

      if r['label'] in self.preloaded_data_samples:
        f = 'there is a pre-existing DataSample with label %s.' + reject
        self.logger.warn(f % r['label'])
        continue

      if r['label'] in k_map:
        f = ('there is a pre-existing DataSample with label %s.(in this batch)'
             + reject)
        self.logger.error(f % r['label'])
        continue

      if r['source'] not in self.preloaded_sources:
        f = 'there is no known source for DataSample with label %s.' + reject
        self.logger.error(f % r['label'])
        continue

      if r['device'] not in self.preloaded_devices:
        f = 'there is no known device for DataSample with label %s.' + reject
        self.logger.error(f % r['label'])
        continue

      if r['scanner'] and r['scanner'] not in self.preloaded_scanners:
        f = 'there is no known scanner for DataSample with label %s.' + reject
        self.logger.error(f % r['label'])
        continue

      if r['options'] :
        try:
          kvs = r['options'].split(',')
          for kv in kvs:
            k,v = kv.split('=')
        except ValueError, e:
          f = 'illegal options string.' + reject
          self.logger.error(f)
          continue
      k_map[r['label']] = r
      good_records.append(r)
    self.logger.info('done consistency checks')
    #--
    return good_records

  def process_chunk(self, otsv, chunk, study):
    def get_options(r):
      options = {}
      if r['options']:
        kvs = r['options'].split(',')
        for kv in kvs:
          k, v = kv.split('=')
          options[k] = v
      return options
    #--
    actions = []
    for r in chunk:
      target = self.preloaded_sources[r['source']]
      device = self.preloaded_devices[r['device']]

      options = get_options(r)
      if isinstance(device, self.kb.Chip) and r['scanner']:
        options['scanner_label'] = self.preloaded_scanners[r['scanner']].label
      alabel = ('importer.data_sample.%s' % r['label'])

      asetup = self.kb.factory.create(self.kb.ActionSetup,
                                      {'label' : alabel,
                                       'conf' : json.dumps(options)})
      #--
      if issubclass(self.source_klass, self.kb.Vessel):
        a_klass = self.kb.ActionOnVessel
        acat = self.kb.ActionCategory.MEASUREMENT
      elif issubclass(self.source_klass, self.kb.DataSample):
        a_klass = self.kb.ActionOnDataSample
        acat = self.kb.ActionCategory.PROCESSING
      else:
        assert False

      conf = {'setup' : asetup,
              'device': device,
              'actionCategory' : acat,
              'operator' : self.operator,
              'context'  : study,
              'target' : target
              }
      actions.append(self.kb.factory.create(a_klass, conf))
    self.kb.save_array(actions)
    #--
    data_samples = []
    for a, r in it.izip(actions, chunk):
      device = a.device
      k = (device.maker, device.model, device.release)
      a.unload()# FIXME we need to do this, otherwise the next save will choke.
      d = data_sample_configurator[k](self.kb, r, a, get_options(r))
      data_samples.append(d)

    assert len(data_samples) == len(chunk)
    self.kb.save_array(data_samples)
    for d in data_samples:
      otsv.writerow({'study' : study.label,
                     'label' : d.label,
                     'type'  : d.get_ome_table(),
                     'vid'   : d.id })

def canonize_records(args, records):
  fields = ['study', 'scanner', 'source_type', 'device_type']
  for f in fields:
    if hasattr(args, f) and getattr(args,f) is not None:
      for r in records:
        r[f] = getattr(args, f)
  # specific hacks
  for r in records:
    if 'scanner' in r and 'device' not in r:
      r['device'] = r['scanner']
      r['device_type'] = 'Scanner'
    for t in ['options', 'scanner']:
      if not (t in r and r[t].upper() != 'NONE'):
        r[t] = None


def make_parser_data_sample(parser):
  parser.add_argument('--study', type=str,
                      help="""default study assumed as context for the
                      import action.  It will
                      over-ride the study column value, if any.""")
  parser.add_argument('--source-type', type=str,
                      choices=['Tube', 'PlateWell', 'DataSample'],
                      help="""default source type.  It will
                      over-ride the source_type column value, if any.
                      """)
  parser.add_argument('--device-type', type=str,
                      choices=['Device', 'Chip', 'Scanner', 'SoftwareProgram'],
                      help="""default source type.  It will
                      over-ride the source_type column value, if any")
  parser.add_argument('--scanner', type=str,
                      help="""default scanner vid.
                      It will over-ride the scanner column value, if
                      any. If a record does not provide a device, it will be
                      set to be a Scanner with this vid.
                      """)
  parser.add_argument('--batch-size', type=int,
                      help="""Size of the batch of objects
                      to be processed in parallel (if possible)""",
                      default=1000)

def import_data_sample_implementation(logger, args):

  action_setup_conf = self.find_action_setup_conf(args)

  recorder = Recorder(args.study,
                      host=args.host, user=args.user, passwd=args.passwd,
                      operator=args.operator,
                      action_setup_conf=action_setup_conf,
                      logger=logger)

  f = csv.DictReader(args.ifile, delimiter='\t')
  logger.info('start processing file %s' % args.ifile.name)
  records = [r for r in f]

  canonize_records(args, records)

  o = csv.DictWriter(args.ofile,
                     fieldnames=['study', 'label', 'type', 'vid'],
                     delimiter='\t')
  o.writeheader()
  recorder.record(records, o)

  logger.info('done processing file %s' % args.ifile.name)


help_doc = """
import new data sample definitions into a virgil system and attach
them to previously registered samples.
"""

def do_register(registration_list):
  registration_list.append(('data_sample', help_doc,
                            make_parser_data_sample,
                            import_data_sample_implementation))


