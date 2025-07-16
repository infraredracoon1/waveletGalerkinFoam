# Makefile for waveletGalerkinFoam Navier-Stokes proof project
# Usage: make REPO_NAME=waveletGalerkinFoam
# Creates repository, compiles manuscript, generates BKM plot, compiles OpenFOAM solver
# Contact: infraredracoon@gmail.com

# Default repository name
REPO_NAME ?= waveletGalerkinFoam

# Directories
SRC_DIR = src
DATA_DIR = data
DOCS_DIR = docs
SCRIPTS_DIR = scripts
BUILD_DIR = build

# Files
TEX_FILE = manuscript.tex
PDF_FILE = manuscript.pdf
CSV_FILE = bkm_integral.csv
JSON_FILE = chartjs_config.json
PLOT_SCRIPT = postProcess.py
PLOT_OUTPUT = bkm_plot.png
README_FILE = README.md
CPP_FILES = $(SRC_DIR)/computeWaveletCoefficients.H $(SRC_DIR)/computeBetaJ.H $(SRC_DIR)/projectDivergenceFree.H
MAIN_CPP = $(SRC_DIR)/main.C
SIM_DATA = $(DATA_DIR)/beta_j_results.csv

# Tools
PDFLATEX = pdflatex
PYTHON = python3
WMAKE = wmake
GIT = git

# Default target
all: init tex chart cpp readme sim_data

# Initialize repository structure
init:
	@echo "Initializing repository $(REPO_NAME)"
	@mkdir -p $(REPO_NAME)/$(SRC_DIR) $(REPO_NAME)/$(DATA_DIR) $(REPO_NAME)/$(DOCS_DIR) $(REPO_NAME)/$(SCRIPTS_DIR) $(REPO_NAME)/$(BUILD_DIR)
	@cp $(TEX_FILE) $(REPO_NAME)/
	@cp $(CSV_FILE) $(REPO_NAME)/$(DATA_DIR)/
	@cp $(JSON_FILE) $(REPO_NAME)/$(DOCS_DIR)/
	@cp $(PLOT_SCRIPT) $(REPO_NAME)/$(SCRIPTS_DIR)/
	@cp $(CPP_FILES) $(REPO_NAME)/$(SRC_DIR)/
	@cp $(MAIN_CPP) $(REPO_NAME)/$(SRC_DIR)/
	@cp $(README_FILE) $(REPO_NAME)/
	@echo "Repository structure created in $(REPO_NAME)"

# Compile LaTeX manuscript
tex:
	@echo "Compiling LaTeX document: $(TEX_FILE)"
	@cd $(REPO_NAME) && $(PDFLATEX) -output-directory $(BUILD_DIR) $(TEX_FILE)
	@cd $(REPO_NAME) && $(PDFLATEX) -output-directory $(BUILD_DIR) $(TEX_FILE) # Run twice for references
	@mv $(REPO_NAME)/$(BUILD_DIR)/$(PDF_FILE) $(REPO_NAME)/
	@echo "Generated $(REPO_NAME)/$(PDF_FILE)"

# Generate BKM integral plot
chart:
	@echo "Generating BKM plot: $(PLOT_OUTPUT)"
	@cd $(REPO_NAME)/$(SCRIPTS_DIR) && $(PYTHON) $(PLOT_SCRIPT)
	@mv $(REPO_NAME)/$(SCRIPTS_DIR)/$(PLOT_OUTPUT) $(REPO_NAME)/$(DOCS_DIR)/
	@echo "Generated $(REPO_NAME)/$(DOCS_DIR)/$(PLOT_OUTPUT)"

# Compile OpenFOAM solver
cpp:
	@echo "Compiling OpenFOAM solver"
	@cd $(REPO_NAME)/$(SRC_DIR) && $(WMAKE) main.C
	@echo "Compiled solver in $(REPO_NAME)/$(SRC_DIR)"

# Copy README
readme:
	@echo "Copying README: $(README_FILE)"
	@cp $(README_FILE) $(REPO_NAME)/
	@echo "Placed $(README_FILE) in $(REPO_NAME)"

# Check for simulation data (placeholder)
sim_data:
	@echo "Checking for simulation data: $(SIM_DATA)"
	@if [ -f $(SIM_DATA) ]; then \
		cp $(SIM_DATA) $(REPO_NAME)/$(DATA_DIR)/; \
		echo "Copied $(SIM_DATA) to $(REPO_NAME)/$(DATA_DIR)"; \
	else \
		echo "Warning: $(SIM_DATA) not found. Run solver to generate."; \
		touch $(REPO_NAME)/$(DATA_DIR)/beta_j_results.csv; \
		echo "# Placeholder: Run main.C to generate beta_j_results.csv" > $(REPO_NAME)/$(DATA_DIR)/beta_j_results.csv; \
	fi

# Initialize Git repository
git_init:
	@echo "Initializing Git repository"
	@cd $(REPO_NAME) && $(GIT) init
	@cd $(REPO_NAME) && $(GIT) add .
	@cd $(REPO_NAME) && $(GIT) commit -m "Initial commit for waveletGalerkinFoam"
	@echo "Git repository initialized in $(REPO_NAME)"

# Clean generated files
clean:
	@echo "Cleaning repository $(REPO_NAME)"
	@rm -rf $(REPO_NAME)/$(BUILD_DIR)
	@rm -f $(REPO_NAME)/$(PDF_FILE)
	@rm -f $(REPO_NAME)/$(DOCS_DIR)/$(PLOT_OUTPUT)
	@rm -f $(REPO_NAME)/$(DATA_DIR)/beta_j_results.csv
	@echo "Cleaned generated files"

# Phony targets
.PHONY: all init tex chart cpp readme sim_data git_init clean
