local:
	@hugo server --buildDrafts

local-build:
	@hugo --buildDrafts --environment development --baseURL http://localhost:8000/
