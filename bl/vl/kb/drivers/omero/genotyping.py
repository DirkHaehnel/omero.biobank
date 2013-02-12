# BEGIN_COPYRIGHT
# END_COPYRIGHT

"""
Genotyping support
==================

Here, a SNP is defined by:

 * a SNP definition mask in the <FLANK>[A/B]<FLANK> format. Allele
   order is defined by the order within the square brackets. The mask
   is expected to be on the Illumina convention TOP strand, if the
   Illumina strand detection algorithm yields a result.

 * a 'source' string, e. g., 'Affymetrix', 'Illumina', 'ABI'

 * a 'context' string, e. g., 'TaqMan-SNP_Genotyping_Assays'

 * a 'release' string, e. g., '12-Nov-2010'

 * a 'label' string, unique within the (source, context, release) domain.

SNPs can have a dbSNP rs label that depends on a specific dbSNP
release and reference genome. The association of SNPs to their rs
labels (see the snp_manager app) is based on the comparison of the
aligment position of the SNP mask wrt a given reference genome and
that of dbSNP masks wrt the same genome. To keep track of this, each
SNP record has the following additional fields:

  * an 'rs_label' string. When none is known, this is set to the same
    value as that of the 'label' field

  * a 'dbSNP_build' long int

  * a 'ref_rs_genome' string
"""

import numpy as np
import itertools as it
from operator import itemgetter

import bl.vl.utils as vlu
import bl.vl.utils.snp as vlu_snp
from utils import assign_vid


BATCH_SIZE = 5000
VID_SIZE = vlu.DEFAULT_VID_LEN

# mset tables
ALIGN_TABLE = 'align'
GDO_TABLE = 'gdo'
MSET_TABLE = 'mset'
MS_TABLES = frozenset([ALIGN_TABLE, GDO_TABLE, MSET_TABLE])


class Marker(object):
  """
  Wraps the contents of a marker definition and associate information.
  """
  def __init__(self, vid, index=None, position=(0,0), flip=None, **kwargs):
    self.id = vid
    self.index = index
    self.position = position
    self.flip = flip
    for k, v in kwargs.iteritems():
      setattr(self, k, v)

  # this is here to make app.importer.map_vid happy
  @classmethod
  def get_ome_table(klass):
    return klass.__name__


class GenotypingAdapter(object):

  SNP_MARKER_DEFINITIONS_TABLE = 'snp_marker_definitions.h5'
  SNP_FLANK_SIZE = vlu_snp.SNP_FLANK_SIZE
  SNP_MASK_SIZE = 2 * SNP_FLANK_SIZE + len("[A/B]")

  SNP_MARKER_DEFINITIONS_COLS = [
    ('string', 'vid', "This marker's VID", VID_SIZE, None),
    ('string', 'source', "Origin of this marker's definition", 16, None),
    ('string', 'context', 'Context of definition', 16, None),
    ('string', 'release', 'Release within the context', 16, None),
    ('string', 'label', "This marker's label within the context", 48, None),
    ('string', 'rs_label', 'dbSNP id', 32, None),  # FIXME too small
    ('long', 'dbSNP_build', 'dbSNP build', None),
    ('string', 'ref_rs_genome', 'Reference rs alignment genome', 16, None),
    ('string', 'mask', "Illumina TOP mask in the <FLANK>[A/B]<FLANK> format",
     SNP_MASK_SIZE, None),
    ('string', 'op_vid', 'Last operation that modified this row',
     VID_SIZE, None),
    ]

  def __init__(self, kb):
    self.kb = kb

  #--- marker definitions ---
  def create_snp_marker_definitions_table(self):
    self.kb.create_table(self.SNP_MARKER_DEFINITIONS_TABLE,
                         self.SNP_MARKER_DEFINITIONS_COLS)

  def add_snp_marker_definitions(self, stream, op_vid, batch_size=BATCH_SIZE):
    vid_correspondence = []
    def add_vid_filter_and_op_vid(stream, op_vid):
      for x in stream:
        assign_vid(x)
        x['op_vid'] = op_vid
        vid_correspondence.append((x['label'], x['vid']))
        yield x
    i_s = add_vid_filter_and_op_vid(stream, op_vid)
    self.kb.add_table_rows_from_stream(self.SNP_MARKER_DEFINITIONS_TABLE,
                                       i_s, batch_size=batch_size)
    return vid_correspondence

  def get_snp_marker_definitions(self, selector=None, col_names=None,
                                 batch_size=BATCH_SIZE):
    return self.kb.get_table_rows(self.SNP_MARKER_DEFINITIONS_TABLE,
                                  selector, col_names, batch_size=batch_size)

  def get_snp_markers_by_source(self, source, context=None, release=None,
                                batch_size=BATCH_SIZE):
    selector = '(source=="%s")' % source
    if context:
      selector += '&(context=="%s")' % context
    # TODO handle the release-without-context case
    if release:
      selector += '&(release=="%s")' % release
    recs = self.get_snp_marker_definitions(
      selector=selector, col_names=['vid'], batch_size=batch_size
      )
    return [Marker(r['vid']) for r in recs]

  def get_snp_markers(self, labels=None, rs_labels=None, vids=None,
                      batch_size=BATCH_SIZE, col_names=None):
    """
    Return a list of Marker objects corresponding to the given list
    (labels, rs_labels or vids). Return an empty list if at least one
    of the items in the list does not correspond to any marker.

    The optional col_names param is a list of marker definition
    headers that will set corresponding attributes in the returned
    Marker objects.
    """
    if col_names is None:
      col_names = ['vid']
    elif 'vid' not in col_names:
      col_names.append('vid')
    if (labels is None) + (rs_labels is None) + (vids is None) != 2:
      raise ValueError('assign exactly one of labels, rs_labels or vids')
    if labels:
      field_name, requested = 'label', labels
    elif rs_labels:
      field_name, requested = 'rs_label', rs_labels
    else:
      field_name, requested = 'vid', vids
    recs = self.get_snp_marker_definitions(
      col_names=[field_name], batch_size=max(batch_size, len(requested))
      )
    by_field = dict((r[0], i) for i, r in enumerate(recs))
    del recs
    row_indices = []
    for x in requested:
      try:
        row_indices.append(by_field[x])
      except KeyError:
        return []
    recs = self.kb.get_table_slice(
      self.SNP_MARKER_DEFINITIONS_TABLE, row_indices, col_names, batch_size
      )
    mlist = []
    for r in recs:
      kwargs = dict((n, r[n]) for n in col_names if n != 'vid')
      mlist.append(Marker(r['vid'], **kwargs))
    return mlist

  #--- SNPMarkersSet ---
  @classmethod
  def snp_markers_set_table_name(klass, table_name_root, set_vid):
    assert(table_name_root in MS_TABLES)
    return '%s-%s.h5' % (table_name_root, set_vid)

  @classmethod
  def snp_markers_set_table_name_parse(klass, table_name):
    tag, set_vid = table_name.rsplit('.')[0].split('-', 1)
    if tag not in MS_TABLES:
      raise ValueError('tag %s from %s is illegal' % (tag, table_name))
    return tag, set_vid

  def _create_snp_markers_set_table(self, table_name_root, cols_def, set_vid):
    table_name = self.snp_markers_set_table_name(table_name_root, set_vid)
    self.kb.create_table(table_name, cols_def)
    return set_vid

  def _delete_snp_markers_set_table(self, table_name_root, set_vid):
    table_name = self.snp_markers_set_table_name(table_name_root, set_vid)
    self.kb.delete_table(table_name)

  def _fill_snp_markers_set_table(self, table_name_root, set_vid, i_s,
                                  batch_size):
    table_name = self.snp_markers_set_table_name(table_name_root, set_vid)
    return self.kb.add_table_rows_from_stream(table_name, i_s, batch_size)

  def _read_snp_markers_set_table(self, table_name_root, set_vid, selector,
                                  batch_size):
    table_name = self.snp_markers_set_table_name(table_name_root, set_vid)
    return self.kb.get_table_rows(table_name, selector, batch_size=batch_size)

  SNP_SET_COLS = [
    ('string', 'marker_vid', 'Marker VID', VID_SIZE, None),
    ('long', 'marker_indx', "Marker index within this set", None),
    ('bool', 'allele_flip', 'True if the A/B convention is reversed', None),
    ('string', 'op_vid', 'Last operation that modified this row',
     VID_SIZE, None),
    ]

  SNP_ALIGNMENT_COLS = [
    ('string', 'marker_vid', 'VID of the aligned marker', VID_SIZE, None),
    ('string', 'ref_genome', 'Reference alignment genome', 16, None),
    ('long', 'chromosome', '1-22, 23(X), 24(Y), 25(XY), 26(MT)', None),
    ('long', 'pos', "Position on the chromosome wrt 5'", None),
    ('long', 'global_pos', "Overall position in the genome", None),
    ('bool', 'strand', 'True if aligned on reference strand', None),
    ('string', 'allele', 'Allele found at this position (A/B)', 1, None),
    ('long', 'copies', "Number of alignments for this marker", None),
    ('string', 'op_vid', 'Last operation that modified this row',
     VID_SIZE, None),
    ]

  @classmethod
  def SNP_GDO_REPO_COLS(klass, N):
    cols = [
      ('string', 'vid', 'gdo VID', VID_SIZE, None),
      ('string', 'op_vid', 'Last operation that modified this row',
       VID_SIZE, None),
      ('string', 'probs', 'np.zeros((2,N), dtype=np.float32).tostring()',
       2*N*4, None),
      ('string', 'confidence', 'np.zeros((N,), dtype=np.float32).tostring()',
       N*4, None),
      ]
    return cols

  def create_snp_markers_set_tables(self, set_vid, N):
    """
    Create all tables needed by a SNPMarkersSet.
    """
    snp_gdo_repo_cols = self.SNP_GDO_REPO_COLS(N)
    for table, cols in ((MSET_TABLE, self.SNP_SET_COLS),
                        (ALIGN_TABLE, self.SNP_ALIGNMENT_COLS),
                        (GDO_TABLE, snp_gdo_repo_cols)):
      self._create_snp_markers_set_table(table, cols, set_vid)
      
  def delete_snp_markers_set_tables(self, set_vid):
    """
    Delete all tables related to a SNPMarkersSet.
    """
    for table in MS_TABLES:
      self._delete_snp_markers_set_table(table, set_vid)

  def define_snp_markers_set(self, set_vid, stream, op_vid,
                             batch_size=BATCH_SIZE):
    """
    Fill in a SNPMarkersSet definition table.
    """
    def add_op_vid(stream, N):
      for x in stream:
        x['op_vid'] = op_vid
        N[0] += 1
        yield x
    N = [0]
    i_s = add_op_vid(stream, N)
    by_idx_s = iter(sorted(i_s, key=itemgetter('marker_indx')))  # uses memory
    self._fill_snp_markers_set_table(MSET_TABLE, set_vid, by_idx_s,
                                     batch_size=batch_size)
    return N[0]

  def read_snp_markers_set(self, set_vid, selector=None, batch_size=BATCH_SIZE):
    return self._read_snp_markers_set_table(MSET_TABLE, set_vid, selector,
                                            batch_size=batch_size)

  def add_snp_markers_set_alignments(self, set_vid, stream, op_vid,
                                     batch_size=BATCH_SIZE):
    """
    Add alignment info to a SNPMarkersSet table.
    
    In the case of multiple hits, only the first copy encountered is
    added in the same order as it is found in the input stream;
    additional copies are temporarily stored and appended at the end.
    """
    tname = self.snp_markers_set_table_name(MSET_TABLE, set_vid)
    vids = [t[0] for t in
            self.kb.get_table_rows(tname, None, col_names=['marker_vid'])]
    vids_set = frozenset(vids)
    def add_vids(stream):
      multiple_hits = {}
      for x in stream:
        k = x['marker_vid']
        if k not in vids_set:
          continue
        x['op_vid'] = op_vid
        if x['copies'] > 1:
          if k in multiple_hits:
            multiple_hits[k].append(x)
            continue
          else:
            multiple_hits[k] = []
        yield x
      for v in multiple_hits.itervalues():
        for x in v:
          yield x
    i_s = add_vids(stream)
    by_vid = {}
    for i in xrange(len(vids)):
      r = i_s.next()
      by_vid[r['marker_vid']] = r
    try:
      records = [by_vid[v] for v in vids]
    except KeyError as e:
      raise ValueError("no alignment info for %s" % e.args[0])
    i_s = it.chain(iter(records), i_s)
    return self._fill_snp_markers_set_table(ALIGN_TABLE, set_vid, i_s,
                                            batch_size=batch_size)

  def read_snp_markers_set_alignments(self, set_vid, selector=None,
                                      batch_size=BATCH_SIZE):
    return self._read_snp_markers_set_table(ALIGN_TABLE, set_vid, selector,
                                            batch_size=batch_size)

  def add_gdo(self, set_vid, probs, confidence, op_vid):
    pstr = probs.tostring()
    cstr = confidence.tostring()
    assert len(pstr) == 2*len(cstr)
    table_name = self.snp_markers_set_table_name(GDO_TABLE, set_vid)
    row = {'op_vid': op_vid, 'probs':  pstr, 'confidence': cstr}
    assign_vid(row)
    row_indices = self.kb.add_table_row(table_name, row)
    assert len(row_indices) == 1
    return row['vid'], row_indices[0]

  def _unwrap_gdo(self, row, indices):
    def unpack(r, field):
      def normalize_size(string, size):
        return string + chr(0) * (size - len(string))
      p = np.fromstring(normalize_size(r[field], r.dtype[field].itemsize),
                        dtype=np.float32)
      return p
    r = {'vid': row['vid'], 'op_vid': row['op_vid']}
    p = unpack(row, 'probs')
    p.shape = (2, p.shape[0]/2)
    r['probs'] = p[:, indices] if indices is not None else p
    c = unpack(row, 'confidence')
    r['confidence'] = c[indices] if indices is not None else c
    return r

  def get_gdo(self, set_vid, vid, row_index, indices=None):
    table_name = self.snp_markers_set_table_name(GDO_TABLE, set_vid)
    rows = self.kb.get_table_rows_by_indices(table_name, [row_index])
    assert len(rows) == 1
    assert rows[0]['vid'] == vid
    return self._unwrap_gdo(rows[0], indices)

  def get_gdo_iterator(self, set_vid, indices=None, batch_size=100):
    def iterator(stream):
      for d in stream:
        yield self._unwrap_gdo(d, indices)
    table_name = self.snp_markers_set_table_name(GDO_TABLE, set_vid)
    return iterator(
      self.kb.get_table_rows_iterator(table_name, batch_size=batch_size)
      )
