"""Tests for hub reference string parser."""

import pytest
from retriever.error import ErrCode, HubError
from retriever.hub._ref import ModuleRef, parse_ref


class TestParseRef:
    def test_org_and_name(self):
        ref = parse_ref("company-abc/lidar-slam")
        assert ref == ModuleRef(org="company-abc", name="lidar-slam")

    def test_with_attribute(self):
        ref = parse_ref("company-abc/lidar-slam:LidarSlamFlow")
        assert ref == ModuleRef(
            org="company-abc", name="lidar-slam", attribute="LidarSlamFlow"
        )

    def test_with_version(self):
        ref = parse_ref("company-abc/lidar-slam@1.0.0")
        assert ref == ModuleRef(
            org="company-abc", name="lidar-slam", version="1.0.0"
        )

    def test_with_attribute_and_version(self):
        ref = parse_ref("company-abc/lidar-slam:LidarSlamFlow@0.1.0")
        assert ref == ModuleRef(
            org="company-abc",
            name="lidar-slam",
            attribute="LidarSlamFlow",
            version="0.1.0",
        )

    def test_underscores_in_org_and_name(self):
        ref = parse_ref("my_org/my_module")
        assert ref.org == "my_org"
        assert ref.name == "my_module"

    def test_underscore_attribute(self):
        ref = parse_ref("org/mod:_PrivateExport")
        assert ref.attribute == "_PrivateExport"

    def test_empty_string_raises(self):
        with pytest.raises(HubError) as exc_info:
            parse_ref("")
        assert exc_info.value.code == ErrCode.HUB_INVALID_REF

    def test_missing_slash_raises(self):
        with pytest.raises(HubError) as exc_info:
            parse_ref("no-slash-here")
        assert exc_info.value.code == ErrCode.HUB_INVALID_REF

    def test_missing_name_raises(self):
        with pytest.raises(HubError) as exc_info:
            parse_ref("org/")
        assert exc_info.value.code == ErrCode.HUB_INVALID_REF

    def test_double_slash_raises(self):
        with pytest.raises(HubError) as exc_info:
            parse_ref("org//name")
        assert exc_info.value.code == ErrCode.HUB_INVALID_REF

    def test_attribute_starting_with_digit_raises(self):
        with pytest.raises(HubError) as exc_info:
            parse_ref("org/name:123Bad")
        assert exc_info.value.code == ErrCode.HUB_INVALID_REF
