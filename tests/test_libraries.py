###
# Created on 2023-04-05 09:04:95
# Copyright © 2023 Christopher West (cwest@thedigitaledge.co.uk)
# SPDX-License-Identifier: 0BSD
###
import pytest

from lxml import etree
import xml.etree.ElementTree as ET

import pysvd
from pydevicetree import Devicetree


@pytest.fixture
def device_tree(dts_file):
    dtree = Devicetree.parseFile(dts_file)
    return dtree


@pytest.fixture
def svd_schema(test_schema):
    xml_schema_file = etree.parse(test_schema)
    xml_schema = etree.XMLSchema(xml_schema_file)
    return xml_schema


@pytest.fixture
def svd_data(svd_file):
    xml_file = etree.parse(svd_file)
    return xml_file


@pytest.fixture
def svd_device(svd_file):
    node = ET.parse(svd_file).getroot()
    device = pysvd.element.Device(node)
    return device


@pytest.mark.slow
@pytest.mark.parametrize("dts_file", ["tests/test_libraries/zephyr_test.dts"])
def test_dts_file_soc(device_tree):
    #
    assert device_tree is not None
    assert device_tree.get_by_path("/interrupt-map-bitops-test/node@70000000e") is not None


@pytest.mark.parametrize("test_schema", ["tests/test_libraries/CMSIS-SVD.xsd"])
@pytest.mark.parametrize("svd_file", ["tests/test_libraries/arm_example.svd"])
def test_validate_svd_file(svd_schema, svd_data):
    assert svd_schema.validate(svd_data) == True


@pytest.mark.parametrize("svd_file", ["tests/test_libraries/arm_example.svd"])
def test_svd_file(svd_device):
    assert svd_device.cpu.name.value == "CM3"
