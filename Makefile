.PHONY: test plan smoke discover nvme-lab-up nvme-lab-down clean

test:
	python3 -m pytest -v

discover:
	python3 -m qualidrive.cli.main discover

plan:
	python3 -m qualidrive.cli.main plan manifests/full_qualification.yaml

smoke:
	python3 -m qualidrive.cli.main run manifests/smoke.yaml --output-dir reports/smoke_run

nvme-lab-up:
	bash infra/qemu/setup_lab.sh

nvme-lab-down:
	bash infra/qemu/teardown_lab.sh

clean:
	rm -rf build/ dist/ *.egg-info reports/ .pytest_cache
