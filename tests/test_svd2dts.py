###
# Created on 2023-04-05 15:04:46
# Copyright © 2023 Christopher West (cwest@thedigitaledge.co.uk)
# SPDX-License-Identifier: 0BSD
###
import os
from pathlib import Path

import pytest

import yaml
from pysvd2dts import svd2dts


@pytest.fixture
def svd(svd_file):
    svd = svd2dts.load_svd(svd_file)
    return svd


@pytest.fixture
def metadata(config_file):
    with open(config_file, "r") as stream:
        metadata = yaml.safe_load(stream)
    return metadata


@pytest.fixture
def bindings(bindings_path, metadata):
    svd2dts.generate_bindings_info(bindings_path, metadata)
    return metadata


def test_input_args_minimal():
    args = svd2dts.process_arguments(
        ["--debug", "arm_example.svd", "arm_example_conf.yaml"])
    assert args.svd_file == "arm_example.svd"
    assert args.config_file == "arm_example_conf.yaml"
    assert args.output_file is None
    assert args.debug is True


def test_input_args_short():
    args = svd2dts.process_arguments(
        ["arm_example.svd", "arm_example_conf.yaml", "--output-file", "arm_example.dts"])
    assert args.svd_file == "arm_example.svd"
    assert args.config_file == "arm_example_conf.yaml"
    assert args.output_file == "arm_example.dts"
    assert args.debug is False


def test_input_arguments_long():
    args = svd2dts.process_arguments(["--zephyr-path", "~/another_path/zephyrproject/zephyr",
                                      "arm_example.svd", "arm_example_conf.yaml"])
    assert args.svd_file == "arm_example.svd"
    assert args.config_file == "arm_example_conf.yaml"
    assert args.output_file is None
    assert args.debug is False
    assert args.zephyr_path == "~/another_path/zephyrproject/zephyr"


def test_load_svd():
    svd_file = "tests/test_svd2dts/arm_example.svd"
    assert os.path.exists(svd_file)
    svd_device = svd2dts.load_svd(svd_file)
    assert svd_device is not None


@pytest.mark.parametrize("svd_file", ["tests/test_svd2dts/arm_example.svd"])
def test_load_svd(svd):
    #
    assert svd is not None
    #
    assert len(svd.peripherals) > 0
    assert svd.peripherals[0].baseAddress == 0x40010000
    assert svd.peripherals[0].name == "TIMER0"
    #
    assert len(svd.peripherals[0].interrupts) > 0
    assert svd.peripherals[0].interrupts[0].name == "TIMER0"
    assert svd.peripherals[0].interrupts[0].value == 0

@pytest.mark.slow
@pytest.mark.parametrize("config_file", ["tests/test_svd2dts/arm_example_conf.yaml"])
@pytest.mark.parametrize("bindings_path", ["tests/test_svd2dts"])
def test_bindings(metadata, bindings):
    #
    assert bindings is not None
    assert len(bindings['drivers']) == 1
    assert bindings['drivers'][0]["series"] == "example"
    assert bindings['drivers'][0]["driver"] == "timer"
    assert bindings['drivers'][0]["name"] == "arm,example-timer"
    assert "tests/test_svd2dts/dts/bindings/arm,example-timer.yaml" in str(bindings['drivers'][0]["file_path"])


@pytest.mark.parametrize("svd_file", ["tests/test_svd2dts/arm_example.svd"])
@pytest.mark.parametrize("config_file", ["tests/test_svd2dts/arm_example_conf.yaml"])
@pytest.mark.parametrize("bindings_path", ["tests/test_svd2dts"])
def test_conversion(svd, metadata, bindings):
    #
    dtree = svd2dts.convert_svd_2_dts(svd, metadata)
    assert dtree is not None
