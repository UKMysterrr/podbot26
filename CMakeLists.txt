cmake_minimum_required(VERSION 3.15)

project(PODBot LANGUAGES CXX)

set(PODBOT_SOURCES
    podbot/dlls/bot.cpp
    podbot/dlls/bot_chat.cpp
    podbot/dlls/bot_client.cpp
    podbot/dlls/bot_combat.cpp
    podbot/dlls/bot_globals.cpp
    podbot/dlls/bot_sounds.cpp
    podbot/dlls/compress.cpp
    podbot/dlls/dll.cpp
    podbot/dlls/engine.cpp
    podbot/dlls/h_export.cpp
    podbot/dlls/linkfunc.cpp
    podbot/dlls/log.cpp
    podbot/dlls/util.cpp
    podbot/dlls/waypoint.cpp
)

add_library(PODBot SHARED ${PODBOT_SOURCES})

target_include_directories(PODBot PRIVATE
    podbot
    podbot/dlls
    podbot/engine
    podbot/common
    podbot/pm_shared
)

set_target_properties(PODBot PROPERTIES
    CXX_STANDARD 98
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS YES
)

if(WIN32)
    if(MSVC)
        set_property(TARGET PODBot PROPERTY MSVC_RUNTIME_LIBRARY
            "MultiThreaded$<$<CONFIG:Debug>:Debug>")
    endif()
    target_sources(PODBot PRIVATE podbot/dlls/podbot.def)
    target_link_libraries(PODBot PRIVATE
        user32
        gdi32
        winspool
        comdlg32
        advapi32
        shell32
        ole32
        oleaut32
        uuid
    )
    set_target_properties(PODBot PROPERTIES OUTPUT_NAME PODBot)
elseif(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    if(NOT CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
        message(FATAL_ERROR "The Linux PODBot target requires GCC or Clang.")
    endif()

    target_compile_definitions(PODBot PRIVATE
        stricmp=strcasecmp
        strcmpi=strcasecmp
    )
    target_compile_options(PODBot PRIVATE -m32 -march=i486)
    target_link_options(PODBot PRIVATE -m32)
    target_link_libraries(PODBot PRIVATE ${CMAKE_DL_LIBS})

    set_target_properties(PODBot PROPERTIES
        PREFIX ""
        OUTPUT_NAME HPB_bot_i486
        SUFFIX ".so"
    )
else()
    message(FATAL_ERROR "PODBot game DLL builds are supported on Windows and Linux only.")
endif()
