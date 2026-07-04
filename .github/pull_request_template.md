## Summary

-

## Validation

- [ ] `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pixi run python -m pytest tests -q`
- [ ] `pixi run p0-release-readiness`
- [ ] `pixi run -e docs docs-build`
- [ ] Docs updated if public behavior changed

## Public-Release Checklist

- [ ] No credentials, private paths, private endpoints, or unpublished artifacts
- [ ] No heavyweight robot/model/demo assets added to core runtime
- [ ] Runtime vs companion-repo boundary is clear
