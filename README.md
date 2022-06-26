<img src="docs/images/logo.svg" width="240" alt="OCRmyPDF">

[![Build Status](https://github.com/ocrmypdf/OCRmyPDF/actions/workflows/build.yml/badge.svg)](https://github.com/ocrmypdf/OCRmyPDF/actions/workflows/build.yml) [![PyPI version][pypi]](https://pypi.org/project/ocrmypdf/) ![Homebrew version][homebrew] ![ReadTheDocs][docs] ![Python versions][pyversions]

[pypi]: https://img.shields.io/pypi/v/ocrmypdf.svg "PyPI version"
[homebrew]: https://img.shields.io/homebrew/v/ocrmypdf.svg "Homebrew version"
[docs]: https://readthedocs.org/projects/ocrmypdf/badge/?version=latest "RTD"
[pyversions]: https://img.shields.io/pypi/pyversions/ocrmypdf "Supported Python versions"

This repository is a fork from [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) that adds support for Google Cloud Vision (GCV) APIs based OCR.

OCRmyPDF adds an OCR text layer to scanned PDF files, allowing them to be searched or copy-pasted.

```bash
export GOOGLE_APPLICATION_CREDENTIALS={path_to_gcv_api_key}

ocrmypdf                      # it's a scriptable command line program
   -l eng+fra                 # it supports multiple languages
   --rotate-pages             # it can fix pages that are misrotated
   --deskew                   # it can deskew crooked PDFs!
   --title "My PDF"           # it can change output metadata
   --jobs 4                   # it uses multiple cores by default
   --output-type pdfa         # it produces PDF/A by default
   --ocr-engine gcv           # it provides support for gcv and tesseract based OCR, uses gcv by default
   input_scanned.pdf          # takes PDF input (or images)
   output_searchable.pdf      # produces validated PDF output
```

If input file contains non-latin text, you can either use `--ocr-engine tesseract` with `--pdf-renderer auto`, or use GCV with no grafting:

```
ocrmypdf                      # it's a scriptable command line program
   -l rus                 # it supports multiple languages
   --title "My PDF"           # it can change output metadata
   --jobs 4                   # it uses multiple cores by default
   --ocr-engine gcv           # it provides support for gcv and tesseract based OCR, uses gcv by default
   --no-graft                 # Use hocr to pdf trnaform output directly, instead of text grafting by pikePDF which only supports Latin text.
   --fontname DejaVuSerif     # use custom font that supports non-latin text
   --fontfile fonts/DejaVuSerif.ttf # Provide path to TTF font file.
   input_scanned.pdf          # takes PDF input (or images)
   output_searchable.pdf      # produces validated PDF output
```

In this case, following to features may not work properly:
- PDF/A support
- Page rotation


[See the release notes for details on the latest changes](https://ocrmypdf.readthedocs.io/en/latest/release_notes.html).

## Main features

- Generates a searchable [PDF/A](https://en.wikipedia.org/?title=PDF/A) file from a regular PDF
- Places OCR text accurately below the image to ease copy / paste
- Keeps the exact resolution of the original embedded images
- When possible, inserts OCR information as a "lossless" operation without disrupting any other content
- Optimizes PDF images, often producing files smaller than the input file
- If requested, deskews and/or cleans the image before performing OCR
- Validates input and output files
- Distributes work across all available CPU cores
- Uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) engine or [Google Cloud Vision](https://cloud.google.com/vision) APIs to recognize more than [100 languages](https://github.com/tesseract-ocr/tessdata)
- Scales properly to handle files with thousands of pages
- Battle-tested on millions of PDFs

For details: please consult the [documentation](https://ocrmypdf.readthedocs.io/en/latest/).

## Motivation

Original [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) repo only provides support for Tesseract engine for OCR. We have extended that to add OCR support based on GCV APIs for document text annotations.
- All preprocessing (dskew and roatation etc.) is done using Tesseract.
- Can either use Tesseract or GCV APIs for OCR.

## Installation
Currenlty only installtion from source is supported. Follow [Installing HEAD revision from sources](docs/installation.rst#installing-head-revision-from-sources) for installation guide. 


## Languages

OCRmyPDF uses Tesseract for OCR, and relies on its language packs. For Linux users, you can often find packages that provide language packs:

```bash
# Display a list of all Tesseract language packs
apt-cache search tesseract-ocr

# Debian/Ubuntu users
apt-get install tesseract-ocr-chi-sim  # Example: Install Chinese Simplified language pack

# Arch Linux users
pacman -S tesseract-data-eng tesseract-data-deu # Example: Install the English and German language packs

# brew macOS users
brew install tesseract-lang
```

You can then pass the `-l LANG` argument to OCRmyPDF to give a hint as to what languages it should search for. Multiple languages can be requested.

OCRmyPDF supports Tesseract 4.0 and the beta versions of Tesseract 5.0. It will
automatically use whichever version it finds first on the `PATH` environment
variable. On Windows, if `PATH` does not provide a Tesseract binary, we use
the highest version number that is installed according to the Windows Registry.

## Documentation and support

Once OCRmyPDF is installed, the built-in help which explains the command syntax and options can be accessed via:

```bash
ocrmypdf --help
```

Our [documentation is served on Read the Docs](https://ocrmypdf.readthedocs.io/en/latest/index.html).

Please report issues on our [GitHub issues](https://github.com/ocrmypdf/OCRmyPDF/issues) page, and follow the issue template for quick response.

## Requirements

In addition to the required Python version (3.7+), OCRmyPDF requires external program installations of Ghostscript and Tesseract OCR. OCRmyPDF is pure Python, and runs on pretty much everything: Linux, macOS, Windows and FreeBSD.

## Experimental Features

Following arguments are experimental only and may have issues:
- `--fontname`
- `--fontfile`
- `--no-graft`

## Press & Media

- [Going paperless with OCRmyPDF](https://medium.com/@ikirichenko/going-paperless-with-ocrmypdf-e2f36143f46a)
- [Converting a scanned document into a compressed searchable PDF with redactions](https://medium.com/@treyharris/converting-a-scanned-document-into-a-compressed-searchable-pdf-with-redactions-63f61c34fe4c)
- [c't 1-2014, page 59](https://heise.de/-2279695): Detailed presentation of OCRmyPDF v1.0 in the leading German IT magazine c't
- [heise Open Source, 09/2014: Texterkennung mit OCRmyPDF](https://heise.de/-2356670)
- [heise Durchsuchbare PDF-Dokumente mit OCRmyPDF erstellen](https://www.heise.de/ratgeber/Durchsuchbare-PDF-Dokumente-mit-OCRmyPDF-erstellen-4607592.html)
- [Excellent Utilities: OCRmyPDF](https://www.linuxlinks.com/excellent-utilities-ocrmypdf-add-ocr-text-layer-scanned-pdfs/)
- [LinuxUser Texterkennung mit OCRmyPDF und Scanbd automatisieren](https://www.linux-community.de/ausgaben/linuxuser/2021/06/texterkennung-mit-ocrmypdf-und-scanbd-automatisieren/)

## Business enquiries

OCRmyPDF would not be the software that it is today without companies and users choosing to provide support for feature development and consulting enquiries. We are happy to discuss all enquiries, whether for extending the existing feature set, or integrating OCRmyPDF into a larger system.

## License

The OCRmyPDF software is licensed under the Mozilla Public License 2.0
(MPL-2.0). This license permits integration of OCRmyPDF with other code,
included commercial and closed source, but asks you to publish source-level
modifications you make to OCRmyPDF.

Some components of OCRmyPDF have other licenses, as noted in those files and the
``debian/copyright`` file. Most files in ``misc/`` use the MIT license, and the
documentation and test files are generally licensed under Creative Commons
ShareAlike 4.0 (CC-BY-SA 4.0).

## Disclaimer

The software is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
