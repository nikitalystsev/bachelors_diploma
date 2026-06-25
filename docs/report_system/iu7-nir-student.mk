REPORT_DIR = report
SLIDES_DIR = slides
RELEASE_DIR = release

PRES = slides
PRES_MAIN = prez
PRES_PRESSED = pressed_$(PRES_MAIN)
MAIN = report

ifeq ($(OS),Windows_NT)
GHOSTSCRIPT ?= gswin64c
else
GHOSTSCRIPT ?= gs
endif
BIBER ?= $(if $(wildcard /opt/homebrew/bin/biber),/opt/homebrew/bin/biber,biber)

all: $(RELEASE_DIR)/$(MAIN).pdf $(RELEASE_DIR)/$(PRES).pdf

$(RELEASE_DIR)/$(MAIN).pdf: $(REPORT_DIR)/$(MAIN).pdf
	mkdir -p $(RELEASE_DIR)
	$(GHOSTSCRIPT) -sDEVICE=pdfwrite \
	  -dCompatibilityLevel=1.4 \
	  -dNOPAUSE \
	  -dOptimize=true \
	  -dQUIET \
	  -dBATCH \
	  -dRemoveUnusedFonts=true \
	  -dRemoveUnusedImages=true \
	  -dOptimizeResources=true \
	  -dDetectDuplicateImages \
	  -dCompressFonts=true \
	  -dEmbedAllFonts=true \
	  -dSubsetFonts=true \
	  -dPreserveAnnots=true \
	  -dPreserveMarkedContent=true \
	  -dPreserveOverprintSettings=true \
	  -dPreserveHalftoneInfo=true \
	  -dPreserveOPIComments=true \
	  -dPreserveDeviceN=true \
	  -dMaxInlineImageSize=0 \
	  -sOutputFile=$@ \
	  $<

$(REPORT_DIR)/$(MAIN).pdf:
	cd $(REPORT_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(MAIN).tex > report_messages.log 2>&1 || { cat report_messages.log; exit 1; }
	cd $(REPORT_DIR) && $(BIBER) $(MAIN) > report_messages.log 2>&1 || { cat report_messages.log; exit 1; }
	cd $(REPORT_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(MAIN).tex > report_messages.log 2>&1 || { cat report_messages.log; exit 1; }
	cd $(REPORT_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(MAIN).tex > report_messages.log 2>&1 || { cat report_messages.log; exit 1; }

	cd $(REPORT_DIR) && rm -f report_messages.log

	
$(RELEASE_DIR)/$(PRES).pdf: $(SLIDES_DIR)/$(PRES_MAIN).pdf
	mkdir -p $(RELEASE_DIR)
	$(GHOSTSCRIPT) -sDEVICE=pdfwrite \
	  -dCompatibilityLevel=1.4 \
	  -dNOPAUSE \
	  -dOptimize=true \
	  -dQUIET \
	  -dBATCH \
	  -dRemoveUnusedFonts=true \
	  -dRemoveUnusedImages=true \
	  -dOptimizeResources=true \
	  -dDetectDuplicateImages \
	  -dCompressFonts=true \
	  -dEmbedAllFonts=true \
	  -dSubsetFonts=true \
	  -dPreserveAnnots=true \
	  -dPreserveMarkedContent=true \
	  -dPreserveOverprintSettings=true \
	  -dPreserveHalftoneInfo=true \
	  -dPreserveOPIComments=true \
	  -dPreserveDeviceN=true \
	  -dMaxInlineImageSize=0 \
	  -sOutputFile=$@ \
	  $<

$(SLIDES_DIR)/$(PRES_MAIN).pdf: $(SLIDES_DIR)/$(PRES_MAIN).tex
	cd $(SLIDES_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(PRES_MAIN).tex > slides_messages.log 2>&1 || { cat slides_messages.log; exit 1; }
	cd $(SLIDES_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(PRES_MAIN).tex > slides_messages.log 2>&1 || { cat slides_messages.log; exit 1; }
	cd $(SLIDES_DIR) && rm -f slides_messages.log
	cd $(SLIDES_DIR) && $(GHOSTSCRIPT) -sDEVICE=pdfwrite \
	  -dCompatibilityLevel=1.4 \
	  -dNOPAUSE \
	  -dOptimize=true \
	  -dQUIET \
	  -dBATCH \
	  -dOptimizeResources=true \
	  -dDetectDuplicateImages \
	  -dCompressFonts=true \
	  -dEmbedAllFonts=true \
	  -dSubsetFonts=true \
	  -sOutputFile=$(PRES_PRESSED).pdf \
	  $(PRES_MAIN).pdf
	cd $(SLIDES_DIR) && mv $(PRES_PRESSED).pdf $(PRES_MAIN).pdf

.PHONY: clean delete_report delete_prez

clean:
	cd $(REPORT_DIR) && rm -f *.toc *.aux *.out *.gz *.log *.bcf *.blg *.bbl *.xml *.run.xml
	cd $(SLIDES_DIR) && rm -f *.toc *.aux *.out *.gz *.log *.nav *.snm *.vrb *.synctex.gz $(PRES_PRESSED).pdf

delete_report:
	cd $(REPORT_DIR) && rm -f report.pdf

delete_prez:
	cd $(SLIDES_DIR) && rm -f prez.pdf
