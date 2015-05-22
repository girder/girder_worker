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
  add_python_flake8_test(flake8_style_gaia "${PROJECT_SOURCE_DIR}/gaia")
  add_python_pep8_test(pep8_style_core_tests "${PROJECT_SOURCE_DIR}/tests")
endif()

add_python_test(arbor)
add_python_test(docker)
add_python_test(geometry)
add_python_test(image)
add_python_test(io)
add_python_test(number)
add_python_test(r)
add_python_test(string)
add_python_test(table)
add_python_test(tree)
add_python_test(workflow)
add_python_test(pickle)

# imported from gaia
add_docstring_test(gaia.core.base)
add_docstring_test(gaia.core.task)
add_docstring_test(gaia.core.port)
add_docstring_test(gaia.core.operators)
add_docstring_test(gaia.esgf.search)
add_docstring_test(gaia.pandas.geopandas_writer)

add_python_test(version)
add_python_test(factory)
add_python_test(gaiaObject)
add_python_test(message)
add_python_test(stream)
add_python_test(port)
add_python_test(task)
add_python_test(geopandas)
add_python_test(esgf_search)
