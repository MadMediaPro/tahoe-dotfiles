#pragma once

#include <QObject>
#include <QPointer>
#include <QRect>
#include <QScreen>
#include <qqmlregistration.h>
#include <KScreen/Types>

class ScreenHelper : public QObject
{
    Q_OBJECT
    QML_ELEMENT
    QML_SINGLETON

    Q_PROPERTY(QString primaryScreenName READ primaryScreenName NOTIFY primaryScreenChanged)
    Q_PROPERTY(QScreen* primaryScreen READ primaryScreen NOTIFY primaryScreenChanged)
    Q_PROPERTY(QRect primaryGeometry READ primaryGeometry NOTIFY primaryScreenChanged)

public:
    static ScreenHelper *instance();
    explicit ScreenHelper(QObject *parent = nullptr);
    ~ScreenHelper() override = default;

    QString primaryScreenName() const;
    QScreen *primaryScreen() const;
    QRect primaryGeometry() const;

    Q_INVOKABLE bool isPrimaryScreen(const QRect &geometry) const;
    Q_INVOKABLE bool isPrimaryScreenName(const QString &name) const;

public Q_SLOTS:
    void reloadConfig();

Q_SIGNALS:
    void primaryScreenChanged();

private:
    void updateWithConfig(const KScreen::ConfigPtr &config);

    QString m_primaryName;
    QRect m_primaryGeometry;
    QPointer<QScreen> m_primaryQScreen;
    KScreen::ConfigPtr m_currentConfig;
};
