# © 2020 James R. Barlow: github.com/jbarlow83
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.


import logging
import os

from ocrmypdf import hookimpl
from ocrmypdf._exec import tesseract
from ocrmypdf._exec import gcv
from ocrmypdf.cli import numeric, str_to_int
from ocrmypdf.helpers import clamp
from ocrmypdf.pluginspec import OcrEngine
from ocrmypdf.subprocess import check_external_program

log = logging.getLogger(__name__)


@hookimpl
def add_options(parser):
	tess = parser.add_argument_group("GCV_Tesseract", "Advanced control of GCV-Tesseract OCR")
	tess.add_argument(
		'--tesseract-config',
		action='append',
		metavar='CFG',
		default=[],
		help="Additional Tesseract configuration files -- see documentation",
	)
	tess.add_argument(
		'--tesseract-pagesegmode',
		action='store',
		type=int,
		metavar='PSM',
		choices=range(0, 14),
		help="Set Tesseract page segmentation mode (see tesseract --help)",
	)
	tess.add_argument(
		'--tesseract-oem',
		action='store',
		type=int,
		metavar='MODE',
		choices=range(0, 4),
		help=(
			"Set Tesseract 4.0+ OCR engine mode: "
			"0 - original Tesseract only; "
			"1 - neural nets LSTM only; "
			"2 - Tesseract + LSTM; "
			"3 - default."
		),
	)
	tess.add_argument(
		'--tesseract-thresholding',
		action='store',
		type=str_to_int(tesseract.TESSERACT_THRESHOLDING_METHODS),
		default='auto',
		metavar='METHOD',
		help=(
			"Set Tesseract 5.0+ input image thresholding mode. This may improve OCR "
			"results on low quality images or those that contain high constrast color. "
			"legacy-otsu is the Tesseract default; adaptive-otsu is an improved Otsu "
			"algorithm with improved sort for background color changes; sauvola is "
			"based on local standard deviation."
		),
	)
	tess.add_argument(
		'--tesseract-timeout',
		default=180.0,
		type=numeric(float, 0),
		metavar='SECONDS',
		help='Give up on OCR after the timeout, but copy the preprocessed page '
		'into the final output',
	)
	tess.add_argument(
		'--user-words',
		metavar='FILE',
		help="Specify the location of the Tesseract user words file. This is a "
		"list of words Tesseract should consider while performing OCR in "
		"addition to its standard language dictionaries. This can improve "
		"OCR quality especially for specialized and technical documents.",
	)
	tess.add_argument(
		'--user-patterns',
		metavar='FILE',
		help="Specify the location of the Tesseract user patterns file.",
	)


@hookimpl
def check_options(options):
	check_external_program(
		program='tesseract',
		package={'linux': 'tesseract-ocr'},
		version_checker=tesseract.version,
		need_version='4.0.0-beta.1',  # using backport for Travis CI
		version_parser=tesseract.TesseractVersion,
	)

	# Decide on what renderer to use
	if options.pdf_renderer == 'auto':
		if options.ocr_engine == 'tesseract':
			options.pdf_renderer = 'sandwich'
		elif options.ocr_engine == 'gcv':
			options.pdf_renderer = 'hocr'

	# if not tesseract.has_user_words() and (options.user_words or options.user_patterns):
	# 	log.warning(
	# 		"Tesseract 4.0 (which you have installed) ignores --user-words and "
	# 		"--user-patterns, so these arguments have no effect."
	# 	)
	# if not tesseract.has_thresholding() and options.tesseract_thresholding != 0:
	# 	log.warning(
	# 		"The installed version of Tesseract does not support changes to its "
	# 		"thresholding method. The --tesseract-threshold argument will be "
	# 		"ignored."
	# 	)
	if options.tesseract_pagesegmode in (0, 2):
		log.warning(
			"The --tesseract-pagesegmode argument you select will disable OCR. "
			"This may cause processing to fail."
		)


@hookimpl
def validate(pdfinfo, options):
	# Tesseract 4.x can be multithreaded, and we also run multiple workers. We want
	# to manage how many threads it uses to avoid creating total threads than cores.
	# Performance testing shows we're better off
	# parallelizing ocrmypdf and forcing Tesseract to be single threaded, which we
	# get by setting the envvar OMP_THREAD_LIMIT to 1. But if the page count of the
	# input file is small, then we allow Tesseract to use threads, subject to the
	# constraint: (ocrmypdf workers) * (tesseract threads) <= max_workers.
	# As of Tesseract 4.1, 3 threads is the most effective on a 4 core/8 thread system.
	if not os.environ.get('OMP_THREAD_LIMIT', '').isnumeric():
		tess_threads = clamp(options.jobs // len(pdfinfo), 1, 3)
		os.environ['OMP_THREAD_LIMIT'] = str(tess_threads)
	else:
		tess_threads = int(os.environ['OMP_THREAD_LIMIT'])
	log.debug("Using Tesseract OpenMP thread limit %d", tess_threads)


class GCVTesseractOcrEngine(OcrEngine):
	"""
	This is a combination of GCV and Tesseract based OCR engine. 
	Tesserarct will be used to get orientation and deskew of images, while GCV or Tesseract will be used for actual OCR.
	"""
	
	@staticmethod
	def version():
		return tesseract.version()

	@staticmethod
	def creator_tag(options):
		tag = '-PDF' if options.pdf_renderer == 'sandwich' else ''
		return f"GCV-Tesseract OCR{tag} {GCVTesseractOcrEngine.version()}"

	def __str__(self):
		return f"GCV-Tesseract OCR {GCVTesseractOcrEngine.version()}"

	@staticmethod
	def languages(options):
		return tesseract.get_languages()

	@staticmethod
	def get_orientation(input_file, options):
		return tesseract.get_orientation(
			input_file,
			engine_mode=options.tesseract_oem,
			timeout=options.tesseract_timeout,
		)

	@staticmethod
	def get_deskew(input_file, options) -> float:
		return tesseract.get_deskew(
			input_file,
			languages=options.languages,
			engine_mode=options.tesseract_oem,
			timeout=options.tesseract_timeout,
		)

	@staticmethod
	def generate_hocr(input_file, output_hocr, output_text, page_no, options):
		if options.ocr_engine == 'gcv':
			gcv.generate_hocr(
				input_file=input_file,
				output_hocr=output_hocr,
				output_text=output_text,
				languages=options.languages,
				page_no=page_no,
				timeout=options.tesseract_timeout,
			)
		elif options.ocr_engine == 'tesseract':
			tesseract.generate_hocr(
				input_file=input_file,
				output_hocr=output_hocr,
				output_text=output_text,
				languages=options.languages,
				engine_mode=options.tesseract_oem,
				tessconfig=options.tesseract_config,
				timeout=options.tesseract_timeout,
				pagesegmode=options.tesseract_pagesegmode,
				thresholding=options.tesseract_thresholding,
				user_words=options.user_words,
				user_patterns=options.user_patterns,
			)

	@staticmethod
	def generate_pdf(input_file, output_pdf, output_text, options):
		tesseract.generate_pdf(
			input_file=input_file,
			output_pdf=output_pdf,
			output_text=output_text,
			languages=options.languages,
			engine_mode=options.tesseract_oem,
			tessconfig=options.tesseract_config,
			timeout=options.tesseract_timeout,
			pagesegmode=options.tesseract_pagesegmode,
			thresholding=options.tesseract_thresholding,
			user_words=options.user_words,
			user_patterns=options.user_patterns,
		)


@hookimpl
def get_ocr_engine():
	return GCVTesseractOcrEngine()
