# Set this variable to the minimum coverage percentage to be considered passing
set(COVERAGE_MINIMUM_PASS 70)

if(PYTHON_COVERAGE)
  add_test(
    NAME py_coverage_reset
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" erase "--rcfile=${py_coverage_rc}"
  )
  add_test(
    NAME py_coverage_combine
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" combine "--rcfile=${py_coverage_rc}"
  )
  add_test(
    NAME py_coverage
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" report "--rcfile=${py_coverage_rc}" --fail-under=${COVERAGE_MINIMUM_PASS}
  )
  add_test(
    NAME py_coverage_html
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" html "--rcfile=${py_coverage_rc}" -d "${coverage_html_dir}"
            "--title=Worker Coverage Report"
  )
  add_test(
    NAME py_coverage_xml
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" xml "--rcfile=${py_coverage_rc}" -o "${PROJECT_BINARY_DIR}/coverage.xml"
  )
  set_property(TEST py_coverage PROPERTY DEPENDS py_coverage_combine)
  set_property(TEST py_coverage_html PROPERTY DEPENDS py_coverage)
  set_property(TEST py_coverage_xml PROPERTY DEPENDS py_coverage)
endif()

if(PYTHON_STYLE_TESTS)
  add_python_flake8_test(flake8_style_core "${PROJECT_SOURCE_DIR}/girder_worker")
  add_python_flake8_test(flake8_style_tests "${PROJECT_SOURCE_DIR}/girder_worker/core/tests")
endif()

add_test(
  NAME packaging
  WORKING_DIRECTORY "${PROJECT_BINARY_DIR}"
  COMMAND "${PROJECT_SOURCE_DIR}/girder_worker/core/tests/packaging_test.sh"
          "${PROJECT_SOURCE_DIR}" "${PROJECT_BINARY_DIR}"
)

add_python_test(format PLUGINS_ENABLED types)
add_python_test(graph PLUGINS_ENABLED types)
add_python_test(image PLUGINS_ENABLED types)
add_python_test(io PLUGINS_ENABLED types)
add_python_test(number PLUGINS_ENABLED types)
add_python_test(string PLUGINS_ENABLED types)
add_python_test(integer_list PLUGINS_ENABLED types)
add_python_test(integer PLUGINS_ENABLED types)
add_python_test(number_list PLUGINS_ENABLED types)
add_python_test(string_list PLUGINS_ENABLED types)
add_python_test(table PLUGINS_ENABLED types,r)
add_python_test(write_script PLUGINS_ENABLED types)
add_python_test(tree PLUGINS_ENABLED types,r)
add_python_test(workflow PLUGINS_ENABLED types)
add_python_test(pickle PLUGINS_ENABLED types)
add_python_test(spec PLUGINS_ENABLED types)
add_python_test(stream)
add_python_test(directory PLUGINS_ENABLED types)

add_docstring_test(girder_worker.core.specs.spec)
add_docstring_test(girder_worker.core.specs.task)
add_docstring_test(girder_worker.core.specs.port PLUGINS_ENABLED types)
add_docstring_test(girder_worker.core.specs.port_list)
add_docstring_test(girder_worker.core.specs.utils)

if(SPHINX_DOCTEST)
  add_test(
    NAME sphinx_doctest
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${SPHINX_BUILD_EXECUTABLE}" -b doctest docs "${PROJECT_BINARY_DIR}/docs"
  )
endif()

# Look for plugin.cmake in plugin dirs, include if they exist
file(GLOB pluginDirs "${PROJECT_SOURCE_DIR}/girder_worker/plugins/*")
foreach(pluginDir ${pluginDirs})
  if(EXISTS "${pluginDir}/plugin.cmake")
    get_filename_component(pluginName "${pluginDir}" NAME)
    message(STATUS "Including plugin.cmake from \"${pluginName}\"")
    include("${pluginDir}/plugin.cmake")
  endif()
endforeach()
