/*
    SPDX-FileCopyrightText: 2018-2019 Kai Uwe Broulik <kde@privat.broulik.de>
    SPDX-FileCopyrightText: 2024 Marco Martin <mart@kde.org>

    SPDX-License-Identifier: GPL-2.0-only OR GPL-3.0-only OR LicenseRef-KDE-Accepted-GPL
*/

import QtQuick
import QtQuick.Layouts

import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami
import org.kde.kquickcontrolsaddons as KQuickControlsAddons

import org.kde.notificationmanager as NotificationManager
import plasma.applet.org.kde.plasma.notifications as Notifications

import "../components" as Components

BaseDelegate {
    id: delegateRoot

    Layout.preferredWidth: (footerLoader.item as Item)?.implicitWidth ?? -1

    body: bodyLabel
    icon: null
    footer: footerLoader.item as Item
    columns: 3

    Accessible.role: Accessible.Notification

    readonly property var effectiveAppIcon: {
        if (modelInterface.applicationIconSource && modelInterface.applicationIconSource !== "") {
            return modelInterface.applicationIconSource;
        }
        if (modelInterface.icon && modelInterface.icon !== "") {
            return modelInterface.icon;
        }
        return "preferences-desktop-notification";
    }

    // Kolom 0: Critical indicator (jika critical)
    Rectangle {
        id: criticalNotificationIndicator
        Layout.fillHeight: true
        Layout.preferredWidth: delegateRoot.modelInterface.urgency === NotificationManager.Notifications.CriticalUrgency ? 4 : 0
        Layout.rightMargin: delegateRoot.modelInterface.urgency === NotificationManager.Notifications.CriticalUrgency ? 6 : 0
        color: Kirigami.Theme.neutralTextColor
        visible: delegateRoot.modelInterface.urgency === NotificationManager.Notifications.CriticalUrgency
    }

    // Kolom 1: macOS Style App Icon (Sisi Kiri, 38x38px)
    Item {
        id: appIconContainer
        Layout.alignment: Qt.AlignTop
        Layout.preferredWidth: 38
        Layout.preferredHeight: 38
        Layout.topMargin: 2
        Layout.rightMargin: 8

        Kirigami.Icon {
            id: appIcon
            anchors.fill: parent
            source: delegateRoot.effectiveAppIcon
            smooth: true
        }
    }

    // Kolom 2: Konten Kanan (Title, Close Button, Body, Actions)
    ColumnLayout {
        id: contentColumn
        Layout.fillWidth: true
        Layout.alignment: Qt.AlignTop
        spacing: 3

        // Baris 1: Summary / Title + Close Button
        RowLayout {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            spacing: 4

            Components.Summary {
                id: summary
                Layout.fillWidth: true
                Layout.alignment: Qt.AlignVCenter
                modelInterface: delegateRoot.modelInterface
                maximumLineCount: 2
                font.weight: Font.DemiBold

                KQuickControlsAddons.MouseEventListener {
                    anchors.fill: parent
                    visible: delegateRoot.modelInterface.hasDefaultAction && !delegateRoot.hasBodyText
                    onClicked: delegateRoot.modelInterface.defaultActionInvoked();
                }
            }

            Components.HeadingButtons {
                id: headingButtons
                Layout.alignment: Qt.AlignTop | Qt.AlignRight
                modelInterface: delegateRoot.modelInterface
            }
        }

        // Baris 2: Body message
        KQuickControlsAddons.MouseEventListener {
            id: bodyMouseListener
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.maximumHeight: Kirigami.Units.gridUnit * delegateRoot.modelInterface.maximumLineCount
            implicitWidth: -1
            implicitHeight: scroll.implicitHeight
            visible: delegateRoot.hasBodyText
            onClicked: {
                if (delegateRoot.modelInterface.hasDefaultAction && !delegateRoot.hoveredLink) {
                    delegateRoot.modelInterface.defaultActionInvoked();
                }
            }
            PlasmaComponents3.ScrollView {
                id: scroll
                anchors.fill: parent
                contentWidth: bodyLabel.width

                PlasmaComponents3.ScrollBar.vertical.visible: delegateRoot.modelInterface.maximumLineCount > 0 && bodyLabel.implicitHeight > parent.Layout.maximumHeight
                PlasmaComponents3.ScrollBar.horizontal.visible: false

                Components.Body {
                    id: bodyLabel
                    width: scroll.width - scroll.PlasmaComponents3.ScrollBar.vertical.width
                    modelInterface: delegateRoot.modelInterface
                    Accessible.ignored: true
                }
            }
        }

        // Baris 3: Footer (Actions / Inline reply)
        Components.FooterLoader {
            id: footerLoader
            Layout.fillWidth: true
            modelInterface: delegateRoot.modelInterface
            iconContainerItem: appIcon
        }
    }
}
