PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)

.PHONY: check test validate validate-source validate-runtime validate-reference shellcheck

check:
	AGENT_SKILLFLEET_PYTHON="$(PYTHON)" bash bin/ci-validate

test:
	$(PYTHON) -m unittest discover -s tests -p 'test_*.py' -v

# Compatibility alias: validate is intentionally the complete pre-push/CI gate.
validate: check

validate-source:
	AGENT_SKILLFLEET_PYTHON="$(PYTHON)" bin/skill-validate --source

validate-runtime:
	AGENT_SKILLFLEET_PYTHON="$(PYTHON)" bin/skill-validate --runtime

validate-reference:
	AGENT_SKILLFLEET_PYTHON="$(PYTHON)" bin/skill-validate --reference

shellcheck:
	@command -v shellcheck >/dev/null 2>&1 || { echo "shellcheck is required for this explicit lint target" >&2; exit 1; }
	shellcheck bin/*
