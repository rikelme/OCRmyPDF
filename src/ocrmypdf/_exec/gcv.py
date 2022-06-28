"""Interface to GCV API"""

import logging
import io
import json
from os import fspath
from pathlib import Path
from typing import List
from enum import Enum
from langcodes import Language
from PIL import Image

from google.cloud import vision
from google.cloud.vision import types
from google.protobuf.json_format import MessageToJson

from string import Template
from xml.sax.saxutils import escape

log = logging.getLogger(__name__)
gcv_client = vision.ImageAnnotatorClient()

MAPPED_LANGS = {'en', 'zh', 'fr', 'pt', 'es'}

class GCVAnnotation:

	templates = {
		'ocr_page': Template("""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="$lang" lang="$lang">
  <head>
	<title>$title</title>
	<meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
	<meta name='ocr-system' content='gcv2hocr.py' />
	<meta name='ocr-langs' content='$lang' />
	<meta name='ocr-number-of-pages' content='1' />
	<meta name='ocr-capabilities' content='ocr_page ocr_carea ocr_line ocrx_word ocrp_lang'/>
  </head>
  <body>
	<div class='ocr_page' id='$htmlid' lang='$lang' title='bbox 0 0 $page_width $page_height'>$content
	</div>
  </body>
</html>
	"""),
	'ocr_line': Template("""
				<span class='ocr_line' id='$htmlid' title='bbox $x0 $y0 $x1 $y1; baseline $baseline'>$content
				</span>"""),
	'ocrx_word': Template("""
					<span class='ocrx_word' id='$htmlid' title='bbox $x0 $y0 $x1 $y1'>$content</span>"""),
	'ocr_carea': Template("""
		<div class='ocr_carea' id='$htmlid' lang='$lang' title='bbox $x0 $y0 $x1 $y1'>$content
		</div>"""),
	'ocr_par': Template("""
			<p class='ocr_par' id='$htmlid' lang='$lang' title='bbox $x0 $y0 $x1 $y1'>$content
			</p>"""),
	}

	def __init__(self,
				 htmlid=None,
				 ocr_class=None,
				 lang='unknown',
				 baseline="0 0",
				 page_height=None,
				 page_width=None,
				 content=[],
				 box=None,
				 title=''):
		self.title = title
		self.htmlid = htmlid
		self.baseline = baseline
		self.page_height = page_height
		self.page_width = page_width
		self.lang = lang
		self.ocr_class = ocr_class
		self.content = content
		if box is not None:
			self._update_box(box)
	
	def _update_box(self, box):
		self.x0 = box[0]['x']
		self.y0 = box[0]['y']
		self.x1 = box[2]['x']
		self.y1 = box[2]['y']

	def maximize_bbox(self, p=False):
		self.x0 = min([w.x0 for w in self.content])
		self.y0 = min([w.y0 for w in self.content])
		self.x1 = max([w.x1 for w in self.content])
		self.y1 = max([w.y1 for w in self.content])

	def __repr__(self):
		return "<%s [%s %s %s %s]>%s</%s>" % (self.ocr_class, self.x0, self.y0,
											  self.x1, self.y1, self.content,
											  self.ocr_class)
	def render(self):
		if type(self.content) == type([]):
			content = "".join(map(lambda x: x.render(), self.content))
		else:
			content = escape(self.content)
		
		return self.__class__.templates[self.ocr_class].substitute(self.__dict__, content=content)

def make_content_box(ocr_class=None, box=None, id=None):
	return GCVAnnotation(
					ocr_class=ocr_class,
					htmlid=id,
					content=[],
					box=box)

def iso_lang_convert(langs):
	"""
	Convert ISO 639-2 language codes to ISO 639-1 codes if possible
	"""
	langs_filtered = []
	try:
		for l in langs:
			l_alpha3 = Language.get(l)
			if l_alpha3.is_valid():
				# remove part after - in mapped languages
				lang = str(l_alpha3)
				l_name = lang.split('-')[0] 
				if l_name in MAPPED_LANGS:
					lang = l_name
				langs_filtered.append(lang)
	except:
		pass
	return langs_filtered

class BreakType(Enum):
	""" Google's Enum for detected breaks in symbol.property.detected_break """
	UNKNOWN = 0
	SPACE = 1
	SURE_SPACE = 2 # IS_PREFIX_FIELD_NUMBER 2
	EOL_SURE_SPACE = 3
	HYPHEN = 4
	LINE_BREAK = 5

def hocr_from_response(resp, page_no=1):
	
	count_dict = {'page': page_no, 'block': 0, 'par': 0, 'line': 0, 'word': 0}
	class_dict = {'page': 'ocr_page', 'block': 'ocr_carea', 'par': 'ocr_par', 'line': 'ocr_line', 'word': 'ocrx_word'}

	for pageObj in resp.full_text_annotation.pages:
		page_box = [{"x": 0, "y": 0}, None, {"x": pageObj.width, "y": pageObj.height}, None]
		page = make_content_box(class_dict['page'], page_box, f'page_{page_no}')

		page.page_height = pageObj.height
		page.page_width = pageObj.width

		breaks = []
		
		for block in pageObj.blocks:

			block_box = json.loads(MessageToJson(block.bounding_box))['vertices']
			count_dict['block'] += 1
			block_id = f'block_{page_no}_' + str(count_dict['block'])
			cur_block = make_content_box(class_dict['block'], block_box, block_id)
			for paragraph in block.paragraphs:
				
				par_box = json.loads(MessageToJson(paragraph.bounding_box))['vertices']
				count_dict['par'] += 1
				par_id = f'par_{page_no}_' + str(count_dict['par'])
				cur_par = make_content_box(class_dict['par'], par_box, par_id)

				count_dict['line'] += 1
				line_id = f'line_{page_no}_' + str(count_dict['line'])
				cur_line = make_content_box(class_dict['line'], None, line_id)
				new_line = None # for multiple line is para
				for wordObj in paragraph.words:
					word_box = json.loads(MessageToJson(wordObj.bounding_box))['vertices']
					count_dict['word'] += 1
					symbols = []
					
					for symbol in wordObj.symbols:
						symbols.append(symbol.text)

						# # add box position a and d of first symbol to line box
						# if line_box[0] is None or line_box[3] is None:
						# 	symbol_box = symbol['bounding_box']['vertices']
						# 	line_box = symbol_box

						property = symbol.property
						detected_break = property.detected_break.type # , None) if property else None
						if detected_break is not None:
							# detectedBreak = detectedBreak.type
							breaks.append(detected_break)
								
							# add best guesses for word breaks
							# print(detectedBreak)
							# if detectedBreak == 'SPACE':
							# 	# symbols.append(' ')
							# 	pass
							# elif detectedBreak == 'SURE_SPACE':
							# 	# symbols.append(' ')
							# 	pass
							if detected_break == BreakType.EOL_SURE_SPACE.value:
								# Make a new line
								# symbols.append(' ')
								# pass

								# symbol_box = symbol['boundingBox']['vertices']
								# line_box[1] = symbol_box[1]
								# line_box[2] = symbol_box[2]
								count_dict['line'] += 1
								line_id = f'line_{page_no}_' + str(count_dict['line'])
								new_line = make_content_box(class_dict['line'], None, line_id)
							elif detected_break == BreakType.HYPHEN.value:
								symbols.append('-')
							# elif detectedBreak == 'LINE_BREAK':
							# 	# symbols.append(' ')
							# 	pass
					
					word_text = ''.join(symbols)

					word_id = f'word_{page_no}_' + str(count_dict['word'])
					word = GCVAnnotation(htmlid=word_id, ocr_class='ocrx_word',
										content=escape(word_text), box=word_box)
					
					cur_line.content.append(word)
					#update if there is a EOL break
					if new_line is not None:
						cur_line.maximize_bbox()
						cur_par.content.append(cur_line)
						cur_line = new_line
						new_line = None
				cur_line.maximize_bbox()
				cur_par.content.append(cur_line)
				cur_par.maximize_bbox()
				cur_block.content.append(cur_par)
			
			cur_block.maximize_bbox()
			page.content.append(cur_block)
		page.maximize_bbox()
		hocr = page.render().encode('utf-8') if str == bytes else page.render()
		text = resp.full_text_annotation.text
		return hocr, text


def page_timedout(timeout):
	if timeout == 0:
		return
	log.warning("[GCV] took too long to OCR - skipping")


def _generate_null_hocr(output_hocr, output_text, image, page_no):
	"""Produce a .hocr file that reports no text detected on a page that is
	the same size as the input image."""
	with Image.open(image) as im:
		w, h = im.size

	page = GCVAnnotation(htmlid=f'page_{page_no}', ocr_class='ocr_page', page_height=h, page_width=w)
	hocr = page.render().encode('utf-8') if str == bytes else page.render()
	output_hocr.write_text(hocr, encoding='utf-8')
	output_text.write_text('[skipped page]', encoding='utf-8')

class GCVLoggerAdapter(logging.LoggerAdapter):
	def process(self, msg, kwargs):
		kwargs['extra'] = self.extra
		return '[GCV] %s' % (msg), kwargs

def generate_hocr(
	*,
	input_file: Path,
	output_hocr: Path,
	output_text: Path,
	languages: List[str],
	page_no: int,
	timeout: float,
):
	"""Generate a hOCR file using GCV OCR, which must be converted to PDF."""
	prefix = output_hocr.with_suffix('')

	# Reminder: test suite tesseract test plugins will break after any changes
	# to the number of order parameters here

	try:
		with io.open(fspath(input_file), 'rb') as image_file:
			content = image_file.read()
	
		image = types.Image(content=content)
		if languages:
			languages = iso_lang_convert(languages)
		response = gcv_client.document_text_detection(image=image, image_context={"language_hints": languages})
		# response_json = json.loads(MessageToJson(response))
		hocr, text_desc = hocr_from_response(response, page_no)
		output_hocr.write_text(hocr, encoding='utf-8')
		output_text.write_text(text_desc, encoding='utf-8')

	except Exception as e:
		# if b'Image too large' in e or b'Empty page!!' in e:
		log.warning(f'GCV Failed to prodcue OCR results for page number {page_no}. Ignore if the page is empty.')
		_generate_null_hocr(output_hocr, output_text, input_file, page_no)
		return

	else:
		# The sidecar text file will get the suffix .txt; rename it to
		# whatever caller wants it named
		if prefix.with_suffix('.txt').exists():
			prefix.with_suffix('.txt').replace(output_text)


def use_skip_page(output_pdf, output_text):
	output_text.write_text('[skipped page]', encoding='utf-8')

	# A 0 byte file to the output to indicate a skip
	output_pdf.write_bytes(b'')
