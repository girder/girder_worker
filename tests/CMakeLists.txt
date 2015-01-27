# Set this variable to the minimum coverage percentage to be considered passing
set(COVERAGE_MINIMUM_PASS 75)

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
            "--title=Girder Coverage Report"
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
  add_python_style_test(pep8_style_core "${PROJECT_SOURCE_DIR}/romanesco")
  add_python_style_test(pep8_style_core_tests "${PROJECT_SOURCE_DIR}/tests")
endif()

add_python_test(arbor)
add_python_test(geometry)
add_python_test(image)
add_python_test(number)
add_python_test(r)
add_python_test(string)
add_python_test(table)
add_python_test(tree)
add_python_test(workflow)
