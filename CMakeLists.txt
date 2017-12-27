cmake_minimum_required(VERSION 2.8.6)

project(girder_worker NONE)

include(CTest)
enable_testing()

find_program(PYTHON_EXECUTABLE python)

option(PYTHON_STYLE_TESTS "Run Python style tests with flake8" ON)
option(PYTHON_COVERAGE "Run tests with coverage.py" OFF)
option(PYTHON_BRANCH_COVERAGE "Use branch-level coverage instead of line-level" OFF)
option(SPHINX_DOCTEST "Run tests inside sphinx documentation" ON)

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE coverage)
endif()

if(PYTHON_STYLE_TESTS)
  find_program(FLAKE8_EXECUTABLE flake8)
endif()

if(SPHINX_DOCTEST)
  find_program(SPHINX_BUILD_EXECUTABLE "sphinx-build")
endif()

if(BUILD_TESTING)
  include(girder_worker/core/tests/PythonTests.cmake)
  add_subdirectory(girder_worker/core/tests)
endif()
