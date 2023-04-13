.. _readme:

README
######

This program create a Zephyr Devicetree file (dts) from a CMSIS System View Description format (SVD).

To run this program you will need to get a SVD file, which is normally supplied as part of a chips SDK.
Create a configuration file, see `Configuration File`_ below for more information.


License
#######

This program is released under the 0BSD clause as specified in the LICENSE file in the root of this project.


Configuration File
##################

The configuration file supplies meta data for the generated device tree.

The example below is used for the nRF52840 development kit.

.. include:: examples/nrf52840dk_conf.yaml


Examples
########

The following example is the minimum information needed to run pysvd2dts
which will generate a file "arm_example.dts".

.. code-block:: console

   pysvd2dts arm_example.svd arm_example_conf.yaml


The following example set all the options to generate a file call "nrf52840_gen.dts".

.. code-block:: console

   pysvd2dts --debug --zephyr-path ~/zephyrproject/zephyr \
      --output-file nrf52840_gen.dts nrf52840.svd examples/nrf52840dk_conf.yaml

