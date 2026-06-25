REPORT_DIR = report
SLIDES_DIR = slides
RELEASE_DIR = release

PRES = slides
MAIN = report

LIBREOFFICE = libreoffice

# all: $(RELEASE_DIR)/$(MAIN).pdf $(RELEASE_DIR)/$(PRES).pdf

$(RELEASE_DIR)/$(MAIN).pdf: $(REPORT_DIR)/$(MAIN).pdf
	mkdir -p $(RELEASE_DIR)
	gs -sDEVICE=pdfwrite \
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
	cd $(REPORT_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(MAIN).tex > report_messages.log
	cd $(REPORT_DIR) && pdflatex -synctex=1 -interaction=nonstopmode --shell-escape $(MAIN).tex > report_messages.log

	cd $(REPORT_DIR) && rm report_messages.log

	
$(RELEASE_DIR)/$(PRES).pdf: $(SLIDES_DIR)/$(PRES).pptx
	$(LIBREOFFICE) --headless --convert-to pdf --outdir $(RELEASE_DIR) $<
	gs -sDEVICE=pdfwrite \
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
	  -sOutputFile=$(SLIDES_DIR)/pressed_$(PRES).pdf \
	  $@

	  mv $(SLIDES_DIR)/pressed_$(PRES).pdf $(RELEASE_DIR)
	  rm $(RELEASE_DIR)/$(PRES).pdf
	  mv $(RELEASE_DIR)/pressed_$(PRES).pdf $(RELEASE_DIR)/$(PRES).pdf

.PHONY: clean

clean:
	cd $(REPORT_DIR) && rm -f *.toc *.aux *.out *.gz *.log *.bcf *.blg *.bbl *.xml *.run.xml

delete_report:
	cd $(REPORT_DIR) && rm -f report.pdf
