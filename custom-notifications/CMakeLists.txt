cmake_minimum_required(VERSION 3.20)
project(plasma_applet_org_kde_plasma_notifications LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(ECM 6.0 REQUIRED NO_MODULE)
set(CMAKE_MODULE_PATH ${ECM_MODULE_PATH})

include(KDEInstallDirs)
include(KDECMakeSettings)
include(KDECompilerSettings NO_POLICY_SCOPE)
include(ECMQtDeclareLoggingCategory)
include(ECMQmlModule)

find_package(Qt6 REQUIRED COMPONENTS Core Gui Quick WaylandClient)
find_package(KF6 REQUIRED COMPONENTS Config CoreAddons GlobalAccel I18n Notifications Service KIO)
find_package(Plasma REQUIRED)
find_package(PlasmaQuick REQUIRED)
find_package(LibNotificationManager REQUIRED)
find_package(Wayland REQUIRED COMPONENTS Client)

set(PLASMA_WAYLAND_PROTOCOLS_DIR "${CMAKE_CURRENT_SOURCE_DIR}/protocols")
set(Wayland_DATADIR "/usr/share/wayland")

add_definitions(-DTRANSLATION_DOMAIN=\"plasma_applet_org.kde.plasma.notifications\")

set(notificationapplet_SRCS
    notificationapplet.cpp
    notificationwindow.cpp
    draghelper.cpp
    fileinfo.cpp
    filemenu.cpp
    globalshortcuts.cpp
    jobaggregator.cpp
    thumbnailer.cpp
    notificationapplet.h
    notificationwindow.h
    draghelper.h
    fileinfo.h
    filemenu.h
    globalshortcuts.h
    jobaggregator.h
    thumbnailer.h
)

plasma_add_applet(org.kde.plasma.notifications QML_ARGS DEPENDENCIES QtCore QtQuick org.kde.plasma.core)

target_sources(org.kde.plasma.notifications PRIVATE ${notificationapplet_SRCS})

ecm_target_qml_sources(org.kde.plasma.notifications SOURCES
    components/ActionContainer.qml
    components/Body.qml
    components/DraggableFileArea.qml
    components/EditContextMenu.qml
    components/FooterLoader.qml
    components/HeadingButtons.qml
    components/Icon.qml
    components/JobDetails.qml
    components/JobIconItem.qml
    components/JobItem.qml
    components/ModelInterface.qml
    components/NotificationHeader.qml
    components/NotificationReplyField.qml
    components/SpeedChart.qml
    components/Summary.qml
    components/ThumbnailStrip.qml
    PATH components
)

ecm_target_qml_sources(org.kde.plasma.notifications SOURCES
    delegates/BaseDelegate.qml
    delegates/DelegateHistoryGrouped.qml
    delegates/DelegateHistory.qml
    delegates/DelegatePopup.qml
    PATH delegates
)

set_source_files_properties(global/Globals.qml PROPERTIES QT_QML_SINGLETON_TYPE ON)

ecm_target_qml_sources(org.kde.plasma.notifications SOURCES
    global/Globals.qml
    global/PulseAudio.qml
    PATH global
)

ecm_target_qml_sources(org.kde.plasma.notifications SOURCES
    CompactRepresentation.qml
    DraggableDelegate.qml
    FullRepresentation.qml
    main.qml
    NotificationPopup.qml
)

qt_generate_wayland_protocol_client_sources(org.kde.plasma.notifications
    PRIVATE_CODE
    FILES
        "${PLASMA_WAYLAND_PROTOCOLS_DIR}/plasma-shell.xml"
        "${Wayland_DATADIR}/wayland.xml"
)

target_sources(org.kde.plasma.notifications PRIVATE
    ${CMAKE_CURRENT_BINARY_DIR}/wayland-plasma-shell-protocol.c
    ${CMAKE_CURRENT_BINARY_DIR}/wayland-wayland-protocol.c
)

target_link_libraries(org.kde.plasma.notifications PRIVATE
                      Qt::Gui
                      Qt::Quick
                      KF6::ConfigGui
                      KF6::I18n
                      Plasma::Plasma
                      Plasma::PlasmaQuick
                      KF6::CoreAddons
                      KF6::GlobalAccel
                      KF6::KIOGui
                      KF6::KIOWidgets
                      KF6::Notifications
                      KF6::Service
                      PW::LibNotificationManager
                      Wayland::Client
                      )

ecm_qt_declare_logging_category(org.kde.plasma.notifications
    HEADER notifications_debug.h
    IDENTIFIER PLASMA_APPLET_NOTIFICATIONS_DEBUG
    CATEGORY_NAME org.kde.plasma.notifications
    DESCRIPTION "plasma applet notification"
    EXPORT PLASMAWORKSPACE
)
