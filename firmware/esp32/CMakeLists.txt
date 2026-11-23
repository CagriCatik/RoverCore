# RoverCore VCU firmware, ESP-IDF project (target esp32s3, ESP32-S3-DevKitC-1 N16R8 v1.1).
# The application logic lives in ../app (target-independent, host-tested), the board I/O in ../bsp/esp32s3.
cmake_minimum_required(VERSION 3.16)
include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(rovercore_vcu)
