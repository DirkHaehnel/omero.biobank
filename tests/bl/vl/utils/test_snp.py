import os, unittest, time
import itertools as it

import bl.vl.utils.snp as usnp

TOP_PAIRS = [
  ("GTCCCACACGTAGTTCGCCAGCCAGTAGATGATGGGGTTGCAGCCGCTGACAAACTGCAG[A/G]TGCTTGGCCTTGGTGGACTTCTCGGCCACGAGGAAGACAACGAAGCTGGCCGGCACGAAG",
   "GTCCCACACGTAGTTCGCCAGCCAGTAGATGATGGGGTTGCAGCCGCTGACAAACTGCAG[A/G]TGCTTGGCCTTGGTGGACTTCTCGGCCACGAGGAAGACAACGAAGCTGGCCGGCACGAAG"),
  ("ACATGCCCCACTCAGCGCCACCCCCGTCCTCCCCTCCCAGGTTGCCTAGCTGTCCCCAGC[T/C]TGGGCCTCCCCGAGGGCCAGACACTCACCAGCATTATTCATCCACAGTCTCCCAGGATCA",
   "TGATCCTGGGAGACTGTGGATGAATAATGCTGGTGAGTGTCTGGCCCTCGGGGAGGCCCA[A/G]GCTGGGGACAGCTAGGCAACCTGGGAGGGGAGGACGGGGGTGGCGCTGAGTGGGGCATGT"),
  ("AGCCCTCTGGGGACTTGCAGGGGTAGGTGTAAAGGTGGCAGTACTGGGGCTGGGCTGGGG[A/G]CCAGTTTCTAGCACCACACTCTGAGCCAAGGGGGTCCTGGGGATGAGGCTAGAGTCCCGT",
   "AGCCCTCTGGGGACTTGCAGGGGTAGGTGTAAAGGTGGCAGTACTGGGGCTGGGCTGGGG[A/G]CCAGTTTCTAGCACCACACTCTGAGCCAAGGGGGTCCTGGGGATGAGGCTAGAGTCCCGT"),
  ("GCCTCGACCCCTTTGCCCTATATTAGAAGTGAGATTCAGGGGTTGTGAGCTTAAGAGACA[C/G]TTCCTGATTTGTCAATGACAGATAAGGATAACTGATGCCCAGGAATACACCCACACCTCC",
   "GGAGGTGTGGGTGTATTCCTGGGCATCAGTTATCCTTATCTGTCATTGACAAATCAGGAA[C/G]TGTCTCTTAAGCTCACAACCCCTGAATCTCACTTCTAATATAGGGCAAAGGGGTCGAGGC"),
  ("GCATACACCCCACCTCGGGACAACAGAGCCTCGTGTCTGGGGTGAGGAGAAAAGTGTGAG[A/T]CCTAACCATTAGTTTTACCCCGAGGGTCCTTGCCACCAGCCCACAGAGAGGACGGGATGG",
   "GCATACACCCCACCTCGGGACAACAGAGCCTCGTGTCTGGGGTGAGGAGAAAAGTGTGAG[A/T]CCTAACCATTAGTTTTACCCCGAGGGTCCTTGCCACCAGCCCACAGAGAGGACGGGATGG"),
  ("ACGAGGATCTGGTCAGCATTGACCACAGTTGAGAGCCTGAGAAGTCAAAGATCAGTCGCC[T/C]ACTACCCCACCCAAAGCGGGCCACATCACCAGCCGCCCCAGGCCTGTAGTCCTGTACCTG",
   "CAGGTACAGGACTACAGGCCTGGGGCGGCTGGTGATGTGGCCCGCTTTGGGTGGGGTAGT[A/G]GGCGACTGATCTTTGACTTCTCAGGCTCTCAACTGTGGTCAATGCTGACCAGATCCTCGT"),
  ("GATTTGAGTCCCAGGTTGTGTCCCAGGCTAGATATGAAAACACAAACAAGTCTCTTAACT[C/G]TTTAAGACTTCAGTTTCTTGGCTGGGCACAGTGGCTCACACCTGTAACCCCAGCACTTTG",
   "CAAAGTGCTGGGGTTACAGGTGTGAGCCACTGTGCCCAGCCAAGAAACTGAAGTCTTAAA[C/G]AGTTAAGAGACTTGTTTGTGTTTTCATATCTAGCCTGGGACACAACCTGGGACTCAAATC"),
  ("CAGCTCACAGACGACAAGAACAAAGCCAGACCCGTGGGCTCGCACTCAGCTCTCCCCTCC[C/G]CATCTCCCACACCAGGACCTGTGGCTTCCTCCCTACTTCCTGCCTGGTCCGTCCCTTTCC",
   "GGAAAGGGACGGACCAGGCAGGAAGTAGGGAGGAAGCCACAGGTCCTGGTGTGGGAGATG[C/G]GGAGGGGAGAGCTGAGTGCGAGCCCACGGGTCTGGCTTTGTTCTTGTCGTCTGTGAGCTG"),
  ("GCATGGAGTAGCACCCTTCGTGGAGGGTGGAGGAGTTGAGATTCCAGGTTGTGAGCCCAG[T/G]GAGCCCCTGACCCAGGTGGGAACTGACCCCTGGGGCCCCAGCATGGCTGTCTTGCACAGT",
   "ACTGTGCAAGACAGCCATGCTGGGGCCCCAGGGGTCAGTTCCCACCTGGGTCAGGGGCTC[A/C]CTGGGCTCACAACCTGGAATCTCAACTCCTCCACCCTCCACGAAGGGTGCTACTCCATGC"),
  ("CCCAGCAAGAAGAGCAAAGAACTCAGGTTTTGGGTGTCGGTGTCTCAAGATGTGTGGCAA[A/C]AGCTTCCTGTCTACCAAGCTCTGTGCATAGGAGGCGTGAGGACAAAGCTTTCTAGTTCAT",
   "CCCAGCAAGAAGAGCAAAGAACTCAGGTTTTGGGTGTCGGTGTCTCAAGATGTGTGGCAA[A/C]AGCTTCCTGTCTACCAAGCTCTGTGCATAGGAGGCGTGAGGACAAAGCTTTCTAGTTCAT"),
  ("CCTGAGAGTTTTGAGTGTGGCCTTGGGGCAAGTCATCTCCCTTAGGTGCAATTCTCTTGT[A/C]TGCAAAATGGGAATAGAGTTGTTCTCATTTGGCATTTTCTCTTATTGCGTTTAATTATTT",
   "CCTGAGAGTTTTGAGTGTGGCCTTGGGGCAAGTCATCTCCCTTAGGTGCAATTCTCTTGT[A/C]TGCAAAATGGGAATAGAGTTGTTCTCATTTGGCATTTTCTCTTATTGCGTTTAATTATTT"),
  ("TTTCTGTGATGGCTCCTTGCAGAGCAGGGCTAGCCTGTAAGCAATGCACTGAGAGTAGCC[A/G]AGAGTGTCCTTAGTTGCCTACTTGCTTTCTACTTTCCAAAATGTGGGCAGTGAAAGAACT",
   "TTTCTGTGATGGCTCCTTGCAGAGCAGGGCTAGCCTGTAAGCAATGCACTGAGAGTAGCC[A/G]AGAGTGTCCTTAGTTGCCTACTTGCTTTCTACTTTCCAAAATGTGGGCAGTGAAAGAACT"),
  ("GAAGTAGTTGCTGGCAATGTTTTCACTGTTGCTCCGACTGAGCATGAGCCTGTAGCGGTC[C/G]TCCTCCTGCCGAGATGCAGATGCCCGTGGTCACGTCCCCTTGTTTGTGCCCCTGGCACAG",
   "CTGTGCCAGGGGCACAAACAAGGGGACGTGACCACGGGCATCTGCATCTCGGCAGGAGGA[C/G]GACCGCTACAGGCTCATGCTCAGTCGGAGCAACAGTGAAAACATTGCCAGCAACTACTTC"),
  ("CTGGGGCCCTGACAGCCTGGGGCTGTGATCATGACTTGCCCAGGGGCCCGAGGGTGGAAA[T/C]GATGCTCTGGCTCCTTTGATTGCATAGAACAGGGGCCACTCAGGTTGACTCAAGAGCAGG",
   "CCTGCTCTTGAGTCAACCTGAGTGGCCCCTGTTCTATGCAATCAAAGGAGCCAGAGCATC[A/G]TTTCCACCCTCGGGCCCCTGGGCAAGTCATGATCACAGCCCCAGGCTGTCAGGGCCCCAG"),
  ("TTGGGGGACCCTGAGGGTGAGCACTGAATGTAGTGGGGTCCCTGGGAAGGGGGCCTGAAT[A/G]AAGAGATCCCCAAAGTTTGGGGATTTTCTAGGGGACTGGTGGTTGGTGTCTGTGGAGAGG",
   "TTGGGGGACCCTGAGGGTGAGCACTGAATGTAGTGGGGTCCCTGGGAAGGGGGCCTGAAT[A/G]AAGAGATCCCCAAAGTTTGGGGATTTTCTAGGGGACTGGTGGTTGGTGTCTGTGGAGAGG"),
]

class TestUSNP(unittest.TestCase):
  " "
  def __init__(self, name):
    super(TestUSNP, self).__init__(name)

  def setUp(self):
    pass

  def tearDown(self):
    pass

  def test_conjugate(self):
    pass

  def test_convert_to_top(self):
    for s,t in TOP_PAIRS:
      self.assertEqual(usnp.convert_to_top(s), t)


def suite():
  suite = unittest.TestSuite()
  suite.addTest(TestUSNP('test_convert_to_top'))
  return suite

if __name__ == '__main__':
  runner = unittest.TextTestRunner(verbosity=2)
  runner.run((suite()))

