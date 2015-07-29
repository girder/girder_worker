cmake_minimum_required(VERSION 2.8.6)

project(Romanesco NONE)

include(CTest)
enable_testing()

find_program(PYTHON_EXECUTABLE python)

option(PYTHON_STYLE_TESTS "Run Python style tests with flake8" ON)
option(PYTHON_COVERAGE "Run tests with coverage.py" OFF)
option(PYTHON_BRANCH_COVERAGE "Use branch-level coverage instead of line-level" OFF)

if(PYTHON_COVERAGE)
  find_program(PYTHON_COVERAGE_EXECUTABLE coverage)
endif()

if(PYTHON_STYLE_TESTS)
  find_program(FLAKE8_EXECUTABLE flake8)
  find_program(PEP8_EXECUTABLE pep8)
endif()

if(BUILD_TESTING)
  include(tests/PythonTests.cmake)
  add_subdirectory(tests)
endif()

# Look for plugin.cmake in plugin dirs, include if they exist
file(GLOB pluginDirs "${PROJECT_SOURCE_DIR}/plugins/*")
foreach(pluginDir ${pluginDirs})
  if(EXISTS "${pluginDir}/plugin.cmake")
    get_filename_component(pluginName "${pluginDir}" NAME)
    message(STATUS "Including plugin.cmake from \"${pluginName}\"")
    include("${pluginDir}/plugin.cmake")
  endif()
endforeach()
