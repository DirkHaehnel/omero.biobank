#!/bin/bash

TOOL="../../../tools/snp_manager --loglevel DEBUG"

if [ "$1" == "--clean" ]; then
    rm -fv *.log *marker_definitions.tsv *.fastq marker_alignment.tsv segment_extractor.tsv dbsnp_index*.db *.dump affy_marker_definitions_reannot.tsv al.tsv al_patched.tsv
    exit 0
fi

echo "Testing convert_dbsnp"
${TOOL} --logfile convert_dbsnp.log convert_dbsnp -d ./ -o dbsnp_marker_definitions.tsv

echo "Testing convert_affy"
${TOOL} --logfile convert_affy.log convert_affy -i affyTest.csv -o affy_marker_definitions.tsv

echo "Testing convert_ill"
${TOOL} --logfile convert_ill.log convert_ill -i illTest.csv -o ill_marker_definitions.tsv

echo "Testing markers_to_fastq"
${TOOL} --logfile markers_to_fastq.log markers_to_fastq -i markerDefinitionsTest.tsv -o reads.fastq

echo "Testing convert_sam"
${TOOL} --logfile convert_sam_to_ma.log convert_sam -i reads.sam -o marker_alignment.tsv --reftag hg18
${TOOL} --logfile convert_sam_to_se.log convert_sam -i reads.sam -o segment_extractor.tsv --reftag hg18 --output-format segment_extractor

echo "Testing build_index"
${TOOL} --logfile build_index.log build_index -i extracted_segments.tsv -o ./ --reftag hg18
python dump_db.py dbsnp_index_hg18_251.db

echo "Testing lookup_index"
${TOOL} --logfile lookup_index.log lookup_index -i test_extracted_segments.tsv --index-file dbsnp_index_hg18_251.db -O affy_marker_definitions_mod.tsv -o affy_marker_definitions_reannot.tsv --align-file affy_marker_alignments.tsv

echo "Testing patch_alignments"
python generate_alignments.py affy_marker_definitions.tsv al.tsv hg18
${TOOL} --logfile patch_alignments.log patch_alignments -a al.tsv -d affy_marker_definitions.tsv -o al_patched.tsv --reftag hg18