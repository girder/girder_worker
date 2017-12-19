include(CMakeParseArguments)

set(py_coverage_rc "${PROJECT_BINARY_DIR}/girder_worker/core/tests/girder_worker.coveragerc")
set(flake8_config "${PROJECT_SOURCE_DIR}/girder_worker/core/tests/flake8.cfg")
set(coverage_html_dir "${PROJECT_SOURCE_DIR}/docs/_build/html/py_coverage")
set(py_testdir "${PROJECT_SOURCE_DIR}/girder_worker/core/tests")

if(PYTHON_BRANCH_COVERAGE)
  set(_py_branch_cov True)
else()
  set(_py_branch_cov False)
endif()

configure_file(
  "${PROJECT_SOURCE_DIR}/girder_worker/core/tests/girder_worker.coveragerc.in"
  "${py_coverage_rc}"
  @ONLY
)

function(add_python_flake8_test name input)
  add_test(
    NAME ${name}
    WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
    COMMAND "${FLAKE8_EXECUTABLE}" "--config=${flake8_config}" "${input}"
  )
endfunction()

function(add_python_test case)
  set(name "${case}")

  set(_multival_args "")
  set(_args PLUGIN PLUGINS_ENABLED)
  cmake_parse_arguments(fn "${_options}" "${_args}" "${_multival_args}" ${ARGN})


  if (fn_PLUGIN)
    set(name "plugins.${fn_PLUGIN}.${case}")
    set(module girder_worker.plugins.${fn_PLUGIN}.tests.${case}_test)
  else()
    set(module girder_worker.core.tests.${case}_test)
  endif()

  if(PYTHON_COVERAGE)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" run --parallel-mode "--rcfile=${py_coverage_rc}"
              -m unittest -v ${module}
    )
  else()
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" -m unittest -v ${module}
    )
  endif()

  if(PYTHON_COVERAGE)
    set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
    set_property(TEST py_coverage_combine APPEND PROPERTY DEPENDS ${name})
  endif()

  if(fn_PLUGINS_ENABLED)
    set_property(TEST ${name} PROPERTY ENVIRONMENT
      "WORKER_PLUGINS_ENABLED=${fn_PLUGINS_ENABLED}"
    )
  else()
    set_property(TEST ${name} PROPERTY ENVIRONMENT
      "WORKER_PLUGINS_ENABLED="
    )
  endif()
endfunction()

function(add_docstring_test module)
  cmake_parse_arguments(fn "" "PLUGINS_ENABLED" "${_multival_args}" ${ARGN})

  set(name doctest:${module})
  if(PYTHON_COVERAGE)
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_COVERAGE_EXECUTABLE}" run --parallel-mode "--rcfile=${py_coverage_rc}"
              "${py_testdir}/docstring_test.py" -v ${module}
    )
  else()
    add_test(
      NAME ${name}
      WORKING_DIRECTORY "${PROJECT_SOURCE_DIR}"
      COMMAND "${PYTHON_EXECUTABLE}" "${py_testdir}/docstring_test.py" -v ${module}
    )
  endif()
  if(PYTHON_COVERAGE)
    set_property(TEST ${name} APPEND PROPERTY DEPENDS py_coverage_reset)
    set_property(TEST py_coverage_combine APPEND PROPERTY DEPENDS ${name})
  endif()
  if(fn_PLUGINS_ENABLED)
    set_property(TEST ${name} PROPERTY ENVIRONMENT
      "WORKER_PLUGINS_ENABLED=${fn_PLUGINS_ENABLED}"
    )
  else()
    set_property(TEST ${name} PROPERTY ENVIRONMENT
      "WORKER_PLUGINS_ENABLED="
    )
  endif()
endfunction()
