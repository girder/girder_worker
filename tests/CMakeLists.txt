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
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" combine
  )
  add_test(
    NAME py_coverage
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" report --fail-under=${COVERAGE_MINIMUM_PASS}
  )
  add_test(
    NAME py_coverage_html
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" html -d "${coverage_html_dir}"
            "--title=Romanesco Coverage Report"
  )
  add_test(
    NAME py_coverage_xml
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" xml -o "${PROJECT_BINARY_DIR}/coverage.xml"
  )
  set_property(TEST py_coverage PROPERTY DEPENDS py_coverage_combine)
  set_property(TEST py_coverage_html PROPERTY DEPENDS py_coverage)
  set_property(TEST py_coverage_xml PROPERTY DEPENDS py_coverage)
endif()

if(PYTHON_STYLE_TESTS)
  add_python_pep8_test(pep8_style_core "${PROJECT_SOURCE_DIR}/romanesco")
  add_python_flake8_test(flake8_style_core "${PROJECT_SOURCE_DIR}/romanesco/specs")
  add_python_pep8_test(pep8_style_core_tests "${PROJECT_SOURCE_DIR}/tests")
endif()

add_python_test(format)
add_python_test(graph)
add_python_test(image)
add_python_test(io)
add_python_test(number)
add_python_test(string)
add_python_test(table PLUGINS_ENABLED r,vtk)
add_python_test(tree PLUGINS_ENABLED r,vtk)
add_python_test(workflow)
add_python_test(pickle)
add_python_test(spec)
add_python_test(directory)

add_docstring_test(romanesco.specs.spec)
add_docstring_test(romanesco.specs.task)
add_docstring_test(romanesco.specs.port)
add_docstring_test(romanesco.specs.port_list)
add_docstring_test(romanesco.format)

# Look for plugin.cmake in plugin dirs, include if they exist
file(GLOB pluginDirs "${PROJECT_SOURCE_DIR}/romanesco/plugins/*")
foreach(pluginDir ${pluginDirs})
  if(EXISTS "${pluginDir}/plugin.cmake")
    get_filename_component(pluginName "${pluginDir}" NAME)
    message(STATUS "Including plugin.cmake from \"${pluginName}\"")
    include("${pluginDir}/plugin.cmake")
  endif()
endforeach()
