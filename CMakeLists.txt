cmake_minimum_required(VERSION 3.15)
project(HandCricketAI)

find_package(pybind11 REQUIRED)

pybind11_add_module(handcricket_ai engine.cpp)