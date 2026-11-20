.PHONY: local local-build build

DESTINATION ?= public

local:
	@hugo server --buildDrafts

local-build:
	$(MAKE) build HUGO_FLAGS="--buildDrafts --environment development --baseURL http://localhost:8000/"

build:
	hugo --destination "$(DESTINATION)" $(HUGO_FLAGS)
	python3 scripts/build_x_index.py "$(DESTINATION)"
