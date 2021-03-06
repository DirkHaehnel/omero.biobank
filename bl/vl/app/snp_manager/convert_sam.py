# BEGIN_COPYRIGHT
# END_COPYRIGHT

"""
Parse a `SAM <http://samtools.sourceforge.net/>`_ file and output
alignment info in one of the following formats:

* tabular, suitable for processing by the marker alignment importer
* tabular, suitable for processing by the `Galaxy
  <http://galaxyproject.org/>`_ DNA extractor

Expects single-end BWA alignment data produced by the previous steps
in the workflow (see markers_to_fastq).
"""

import os
from contextlib import nested

from bl.core.seq.align.mapping import SAMMapping
from bl.core.utils import NullLogger
import bl.vl.utils.snp as vlu_snp
from common import MARKER_AL_FIELDS, CHR_CODES, DUMMY_AL_VALUES, \
     SeqNameSerializer


HELP_DOC = __doc__
OUTPUT_FORMATS = ["marker_alignment", "segment_extractor"]
DEFAULT_OUTPUT_FORMAT = OUTPUT_FORMATS[0]
DEFAULT_FLANK_SIZE = vlu_snp.SNP_FLANK_SIZE


def SamReader(f):
  for line in f:
    line = line.strip()
    if line == "" or line.startswith("@"):
      continue
    yield SAMMapping(line.split())


class SnpHitProcessor(object):

  HEADER = MARKER_AL_FIELDS

  def __init__(self, ref_tag, outf, outfmt=DEFAULT_OUTPUT_FORMAT,
               flank_size=DEFAULT_FLANK_SIZE, logger=None):
    self.logger = logger or NullLogger()
    self.ref_tag = ref_tag
    self.outf = outf
    self.outfmt = outfmt
    self.flank_size = flank_size
    self.current_id = None
    self.current_hits = []
    self.serializer = SeqNameSerializer()

  def process(self, hit):
    """
    Process a hit in the SAMMapping format, looking for a perfect
    (edit distance, i.e., NM tag value == 0) and unambiguous (mapping
    quality > 0) hit.
    """
    name = hit.get_name()
    id_, allele, snp_offset, _ = self.serializer.deserialize(name)
    if id_ != self.current_id:
      if self.current_id is not None:
        self.dump_current_hits()
      self.current_id = id_
      self.current_hits = []
    nm = hit.tag_value('NM')
    mapped = hit.is_mapped()
    if mapped and nm <= 0 and hit.qual > 0:
      snp_pos = hit.get_untrimmed_pos() + snp_offset
      chr_code = CHR_CODES.get(hit.tid, 'None')
      strand = '-' if hit.is_on_reverse() else '+'
      if self.outfmt == DEFAULT_OUTPUT_FORMAT:
        r = [id_, self.ref_tag, str(chr_code), str(snp_pos), strand, allele]
      else:
        if hit.tid is None:
          self.logger.error("%r: can't use null chr for %r output" %
                            (name, self.outfmt))
          return
        start = snp_pos - self.flank_size - 1
        end = snp_pos + self.flank_size
        r = [hit.tid, str(start), str(end), name, '0', strand]
      self.current_hits.append(r)
    else:
      self.logger.info("%r: mapped:%r; NM:%r; qual:%r" %
                       (name, mapped, nm, hit.qual))

  def dump_current_hits(self):
    nh = len(self.current_hits)
    if nh != 1:
      self.logger.warn("hit count for %s: %d != 1" % (self.current_id, nh))
    if nh == 0 and self.outfmt == DEFAULT_OUTPUT_FORMAT:
      self.current_hits.append([
        self.current_id,
        self.ref_tag,
        DUMMY_AL_VALUES["chromosome"],
        DUMMY_AL_VALUES["pos"],
        DUMMY_AL_VALUES["strand"],
        DUMMY_AL_VALUES["allele"],
        ])
    if self.outfmt == DEFAULT_OUTPUT_FORMAT:
      for hit in self.current_hits:
        hit.append(str(nh))
        assert hit[0] == self.current_id
        self.write_row(hit)
    else:
      if nh == 1:
        self.write_row(self.current_hits[0])

  def write_row(self, data):
    self.outf.write("\t".join(data)+"\n")

  def write_header(self):
    if self.outfmt == DEFAULT_OUTPUT_FORMAT:
      self.write_row(self.HEADER)

  def close_open_handles(self):
    self.outf.close()


def write_output(sam_reader, outf, reftag, outfmt, flank_size, logger=None):
  logger = logger or NullLogger()
  hit_processor = SnpHitProcessor(reftag, outf, outfmt, flank_size, logger)
  hit_processor.write_header()
  for i, m in enumerate(sam_reader):
    hit_processor.process(m)
  hit_processor.dump_current_hits()  # last pair
  return i+1


def make_parser(parser):
  parser.add_argument('-i', '--input-file', metavar='FILE', required=True,
                      help='input SAM file')
  parser.add_argument('-o', '--output-file', metavar='FILE', required=True,
                      help='output file')
  parser.add_argument('--reftag', metavar='STRING', required=True,
                      help='reference genome tag')
  parser.add_argument('--output-format', metavar='STRING',
                      choices=OUTPUT_FORMATS, default=DEFAULT_OUTPUT_FORMAT,
                      help='possible values: %r' % (OUTPUT_FORMATS,))
  parser.add_argument('--flank-size', metavar='INT', type=int,
                      default=DEFAULT_FLANK_SIZE,
                      help='size of the flanks to extract around the SNP.' +
                      ' Has no effect with marker alignment output')


def main(logger, args):
  with nested(open(args.input_file), open(args.output_file, 'w')) as (f, outf):
    bn = os.path.basename(args.input_file)
    logger.info("processing %r" % bn)
    reader = SamReader(f)
    count = write_output(reader, outf, args.reftag, args.output_format,
                         args.flank_size, logger=logger)
  logger.info("SAM records processed from %r: %d" % (bn, count))


def do_register(registration_list):
  registration_list.append(('convert_sam', HELP_DOC, make_parser, main))
