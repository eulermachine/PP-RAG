cmake_minimum_required(VERSION 3.14)
project(pprag_core2_v2)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_POSITION_INDEPENDENT_CODE ON)

# 优化编译选项
set(CMAKE_CXX_FLAGS_RELEASE "-O3 -march=native -DNDEBUG -fPIC")

# 查找pybind11
find_package(pybind11 CONFIG)
if(NOT pybind11_FOUND)
    include(FetchContent)
    FetchContent_Declare(
        pybind11
        GIT_REPOSITORY https://github.com/pybind/pybind11.git
        GIT_TAG v2.11.1
    )
    FetchContent_MakeAvailable(pybind11)
endif()

# 查找SEAL
find_package(SEAL 4.1 CONFIG)
if(SEAL_FOUND)
    message(STATUS "Found SEAL: ${SEAL_DIR}")
    add_definitions(-DUSE_SEAL)
else()
    message(STATUS "SEAL not found, building without HE support")
endif()

# 查找OpenMP
find_package(OpenMP)
if(OpenMP_CXX_FOUND)
    message(STATUS "Found OpenMP")
endif()

# 创建Python模块 - Variant 2版本
pybind11_add_module(pprag_core2 ../src/core/bench_wrapper2.cpp)

# 链接库
if(SEAL_FOUND)
    target_link_libraries(pprag_core2 PRIVATE SEAL::seal)
endif()

if(OpenMP_CXX_FOUND)
    target_link_libraries(pprag_core2 PRIVATE OpenMP::OpenMP_CXX)
endif()

install(TARGETS pprag_core2 DESTINATION .)
