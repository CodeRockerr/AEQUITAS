cmake_minimum_required(VERSION 3.18)
project(aequitas_kernels LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# scikit-build-core provides Python; fall back for manual builds
find_package(Python REQUIRED COMPONENTS Interpreter Development.Module)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(aequitas_kernels kernels.cpp)

target_compile_options(aequitas_kernels PRIVATE
  $<$<CONFIG:Release>:-O3>
  # NOTE: -march=native gives the best numbers on your own machine but
  # produces non-portable binaries. The Docker image builds with the
  # portable default; benchmark runs may use -march=native locally.
)

install(TARGETS aequitas_kernels DESTINATION .)
