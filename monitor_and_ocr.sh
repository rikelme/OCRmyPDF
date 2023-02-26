#!/bin/bash
input_file=$1
output_file=$(basename inputfile)_searchable.pdf
echo 'ocr-ing $input_file to $outputfile'
ocrmypdf --rotate-pages --rotate-pages-threshold 1 --redo-ocr --ocr-engine gcv --output-type pdfa -l eng,hrv,srp $input_file $output_file

