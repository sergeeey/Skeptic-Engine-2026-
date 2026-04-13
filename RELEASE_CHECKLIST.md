# RELEASE Checklist — v0.2.0

## Pre-Release Verification

- [ ] All tests pass: `pytest tests/ -v --tb=short`
- [ ] Ruff clean: `ruff check src/ tests/`
- [ ] Mypy clean: `mypy src/`
- [ ] Smoke test: `python experiments/mrm_bench_v01/run_smoke_test.py`
- [ ] CLI works: `skeptic-toolkit --help`
- [ ] Demo notebook: verify `demo_colab.ipynb` runs end-to-end

## Package Build

- [ ] `python -m build` succeeds
- [ ] `twine check dist/*` passes
- [ ] `pip install .` works in fresh venv
- [ ] `skeptic-toolkit --help` works after pip install
- [ ] `pip install ".[dev]"` installs all dev dependencies

## Version Bump

- [ ] `__version__ = "0.2.0"` in `src/skeptic_toolkit/__init__.py`
- [ ] `__version__ = "0.2.0"` in `src/skeptic_mrm/__init__.py`
- [ ] `version = "0.2.0"` in `pyproject.toml`
- [ ] Changelog entry in `CHANGELOG.md`

## Documentation

- [x] README updated with unified narrative
- [x] REPORT updated with H27-H33 results
- [ ] API docs generated (if applicable)
- [ ] `demo_colab.ipynb` updated with new experiments

## External Releases

- [ ] **PyPI upload**: `twine upload dist/*`
- [ ] **Zenodo v0.2**: upload post-H33 code + report
- [ ] **bioRxiv preprint v03**: manuscript with H31+H32+H33

## Post-Release

- [ ] Tag release: `git tag v0.2.0 && git push origin v0.2.0`
- [ ] GitHub Release notes
- [ ] Update demo_colab.ipynb if needed
- [ ] Send pitch emails (Bradshaw, Bik, Nuijten)

---

## Status: 🟢 READY FOR PUBLISHING

**Completed:**
- ✅ README 2.0 with unified narrative
- ✅ REPORT updated with H27-H33
- ✅ 302 tests passing
- ✅ ruff + mypy green
- ✅ Version bumped to 0.2.0
- ✅ Build succeeds (wheel + sdist)
- ✅ Twine check PASSED

**Remaining (external actions required):**
- ⏳ PyPI upload: `twine upload dist/skeptic_engine-0.2.0*`
- ⏳ Zenodo v0.2: upload post-H33 code + report
- ⏳ bioRxiv preprint v03: manuscript with H31+H32+H33
- ⏳ Tag release: `git tag v0.2.0 && git push origin v0.2.0`
- ⏳ Send pitch emails (Bradshaw, Bik, Nuijten)
