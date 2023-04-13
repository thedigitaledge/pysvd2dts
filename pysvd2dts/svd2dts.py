#!/usr/bin/env python3
###
# Created on 2023-04-05 09:04:04
# Copyright © 2023 Christopher West (cwest@thedigitaledge.co.uk)
# SPDX-License-Identifier: 0BSD
###
import argparse
import logging
import os
import re
import sys
import xml.etree.ElementTree as ET
from argparse import Namespace
from pathlib import Path

import yaml
from pydevicetree import Devicetree, Node, Property
from pydevicetree.ast import CellArray, PropertyValues, StringList
from pysvd.element import Device

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def convert_svd_2_dts(svd_device: Device, device_meta: dict) -> Devicetree:
    """ Converts a CMSIS System View Description (svd) file to a devicetree file (dts)

    :param svd_device: Input svd object
    :type svd_device: Device
    :param device_meta: Device metadata dictionary
    :type device_meta: dict
    :return: Returns a fully populated devicetree
    :rtype: Devicetree

    .. seealso:: `<https://www.keil.com/pack/doc/CMSIS/SVD/html/svd_format_pg.html>`_
    .. seealso:: `<https://docs.zephyrproject.org/latest/build/dts/index.html>`_
    """

    # ## Create device tree
    logger.info("Convert SVD file to Devicetree")
    soc_children = list()
    for peripheral in svd_device.peripherals:

        # # Dont use peripheral if it's derived from other one
        device_name = peripheral.name.lower()
        logger.debug(f"Processing {device_name}")
        #
        label = device_name
        peri = re.search("\d+$", label)
        if peri is None:
            name = device_name
        else:
            name = f"{device_name}".removesuffix(peri.group(0))

        skip = False
        for items in device_meta["peripherals"]["skip"]:
            if items == name:
                skip = True
        if skip == True:
            logger.debug(f"Skipping device: '{name}'")
            continue

        # ##
        if ("map" in device_meta["peripherals"] and
                name in device_meta["peripherals"]["map"]):
            #
            new_name = device_meta["peripherals"]["map"][name]
            logger.debug(f"Changing name: '{name}'➔'{new_name}'")
            #
            new_label = label.replace(name, device_meta["peripherals"]["map"][name])
            logger.debug(f"Renaming: '{label}'➔'{new_label}'")
            #
            name = new_name
            label = new_label

        # ## Setting up leaf
        leaf_children = []
        leaf_directives = []
        leaf_properties = []
        # # Setting leaf compatibilities
        compat = next(
            (item for item in device_meta["drivers"] if item["driver"] == name), None)
        if compat is not None:
            driver_name = compat["name"]
            logger.debug(f"Found compatible driver: '{name}'='{driver_name}'")
            compatible = Property('compatible', StringList([driver_name]))
        else:
            logger.warning(f"Could not find diver for '{name}'")
            compatible = Property('compatible', StringList(["NONE"]))
        leaf_properties.append(compatible)
        # # Setting leaf registered
        address = peripheral.baseAddress
        size = 0
        for addrs in peripheral.addressBlocks:
            size += addrs.size
        leaf_properties.append(Property('reg', CellArray([address, size])))
        # # Setting leaf interrupts
        if len(peripheral.interrupts) > 0:
            priority = 0
            if len(peripheral.interrupts) == 1:
                interrupt = CellArray(
                    [peripheral.interrupts[0].value, priority])
            else:
                cell_array = list()
                for prop in peripheral.interrupts:
                    cell_array.append(CellArray([prop.value, priority]))
                #
                interrupt = PropertyValues(cell_array)
            leaf_properties.append(Property('interrupts', interrupt))
        # # Setting leaf properties
        leaf_properties.append(Property('status', StringList(['disabled'])))

        # ##
        if ("rename" in device_meta["peripherals"] and
                name in device_meta["peripherals"]["rename"]):
            #
            new_name = device_meta["peripherals"]["rename"][name]
            logger.debug(f"Replacing name: '{name}'➔'{new_name}'")
            #
            new_label = label.replace(name, device_meta["peripherals"]["rename"][name])
            logger.debug(f"Replacing label: '{label}'➔'{new_label}'")
            #
            name = new_name
            label = new_label
        #
        logger.debug(f"Creating new soc node: '{name}@{address}'")
        leaf = Node(name=name, address=address, children=leaf_children, label=label,
                    directives=leaf_directives, properties=leaf_properties)
        soc_children.append(leaf)

    # #
    logger.debug("Creating soc object")
    #
    soc_properties = [
        Property('#address-cells', CellArray([1])),
        Property('#size-cells', CellArray([1])),
    ]
    if "soc_compatible" in device_meta:
        soc_compt = Property('compatible', StringList(device_meta["soc_compatible"]))
    else:
        soc_compt = Property('compatible', StringList(["NONE"]))
    soc_properties.append(soc_compt)
    #
    soc_directives = []
    soc = Node(name="soc", label=None, address=None, properties=soc_properties,
               directives=soc_directives, children=soc_children)

    # #
    logger.debug("Creating root object")
    root_properties = list()
    #
    if "compatible" in device_meta:
        compat = Property('compatible', StringList([device_meta["compatible"]]))
    else:
        compat = Property('compatible', StringList(["NONE"]))
    root_properties.append(compat)
    #
    if "model" in device_meta:
        model = Property('model', StringList([device_meta["model"]]))
    else:
        model = Property('model', StringList(["NONE"]))
    root_properties.append(model)
    #
    root_directives = []
    root_children = [soc]
    root = Node(name="/", label=None, address=None, properties=root_properties,
                directives=root_directives, children=root_children)
    # #
    logger.info("Creating devicetree")
    device_tree = Devicetree(elements=[root])
    return device_tree


def load_svd(svd_file: Path) -> Device:
    """ Loads an SVD file and coverts it to a 'Devicetree' object

    :param svd_file: CMSIS-SVD file
    :type svd_file: Path
    :return: SVD file as a doctree object
    :rtype: Devicetree
    """
    # ## Load SVD file
    logger.debug(f"Loading svd file '{svd_file}'")
    node = ET.parse(svd_file).getroot()
    device = Device(node)
    logger.debug(f"Successfully loading svd file")
    return device


def generate_bindings_info(zephyr_path: Path, metadata: dict):
    # ##
    exclude_filter = ["common"]
    binding_path = Path(zephyr_path) / "dts/bindings"
    chip_series = metadata["chip_series"]
    manufacture = metadata["manufacture"]

    # ## Device Binding path
    binding_path = binding_path.resolve()
    if not os.path.exists(binding_path):
        raise NotADirectoryError()

    file_list = list()
    chip_series = chip_series if type(chip_series) == list else [chip_series]
    for series in chip_series:
        search_bindings = f"{manufacture},{series}*.yaml"
        logger.debug(f"Searching for bindings: '{search_bindings}'")
        for file in binding_path.rglob(search_bindings):
            for key in exclude_filter:
                if key not in str(file):
                    logger.debug(f"Found device bindings: '{file.stem}'")
                    file_list.append(file)

    # ## Create driver meta data
    drivers = list()
    for file in file_list:
        # ##
        for series in chip_series:
            driver_file_name = file.stem
            manufacture, dts_label = driver_file_name.split(',')

            if "-" in dts_label and dts_label.startswith(series):
                driver_series, driver = dts_label.split("-", 1)
            else:
                driver = dts_label
                driver_series = series
            #
            logger.debug(
                f"Creating new driver '{driver}'➔'{driver_file_name}'")
            drivers.append(
                {"series": driver_series, "driver": driver, "name": driver_file_name,
                 "file_path": file})
    # #
    metadata["drivers"] = drivers


def process_arguments(input_args: list[str]) -> Namespace:
    """ Processing the input arguments.

    :param input_args: List of command line arguments as strings
    :type input_args: list[str]
    :returns: An argparser namespace of processed arguments
    :rtype: Namespace

    .. seealso:: `argparser <https://docs.python.org/3/library/argparse.html>`_
    """
    # ##
    parser = argparse.ArgumentParser()
    parser.add_argument("svd_file")
    parser.add_argument("config_file", default=None)
    parser.add_argument("-o", "--output-file", default=None)
    parser.add_argument("-z", "--zephyr-path", default=None)
    parser.add_argument("--debug", action="store_true")
    # ##
    args = parser.parse_args(input_args)
    return args


def main():
    """ Converts the SVD file to a Devicetree file

    :raises FileNotFoundError: Raises when the configuration file cannot be found
    :raises NotADirectoryError: When the Zephyr folder cannot be located
    :raises FileNotFoundError: Raises when the configuration file cannot be found
    """
    # ## Process and validated input arguments
    args = process_arguments(sys.argv[1:])
    # # Set logging level
    if args.debug:
        # Create output to stdio
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        # Update main logging level
        logger.setLevel(logging.DEBUG)

    # # Check file exists
    if args.config_file is None or not os.path.exists(args.config_file):
        raise FileNotFoundError("Chip configuration not supplied")
    else:
        config_file = Path(args.config_file)
    # # Check bindings path exists
    if not os.path.exists(args.zephyr_path):
        raise NotADirectoryError("Zephyr bindings location doesn't exist")
    else:
        zephyr_path = Path(args.zephyr_path)
    # # Check if SVD file exists
    if not os.path.exists(args.svd_file):
        raise FileNotFoundError("Cannot open SVD file")
    else:
        svd_file = Path(args.svd_file)
    # # Set output file name
    if args.output_file is None:
        output_file = svd_file.parents / f"{svd_file.stem}.dts"
    else:
        output_file = Path(args.output_file)

    # ## Load yaml configuration
    logger.info(f"Opening configuration file: '{config_file}'")
    with open(config_file, "r") as stream:
        metadata = yaml.safe_load(stream)

    # ## Generate list of device bindings
    # # Extract drivers
    logger.info(f"Locating bindings: '{zephyr_path}'")
    generate_bindings_info(zephyr_path, metadata)

    # ## Load SVD file
    logger.info(f"Loading svd file to object")
    svd_device = load_svd(svd_file)

    # ## Convert SVD object to devicetree object
    logger.info("Converting SVD object to Devicetree object")
    device_tree = convert_svd_2_dts(svd_device, metadata)

    # ## Writing devicetree object to file
    logger.info(f"Writing devicetree object to file: '{output_file}'")
    # # Write devicetree object to output file
    with open(output_file, 'w') as dts:
        dts.write(device_tree.to_dts())


if __name__ == "__main__":
    main()
