#include "screenhelper.h"

#include <QGuiApplication>
#include <QDebug>
#include <KScreen/Config>
#include <KScreen/GetConfigOperation>
#include <KScreen/ConfigMonitor>
#include <KScreen/Output>

static ScreenHelper *s_instance = nullptr;

ScreenHelper *ScreenHelper::instance()
{
    if (!s_instance) {
        s_instance = new ScreenHelper(qApp);
    }
    return s_instance;
}

ScreenHelper::ScreenHelper(QObject *parent)
    : QObject(parent)
{
    s_instance = this;
    reloadConfig();
}

void ScreenHelper::reloadConfig()
{
    auto op = new KScreen::GetConfigOperation();
    connect(op, &KScreen::GetConfigOperation::finished, this, [this](KScreen::ConfigOperation *op) {
        auto config = qobject_cast<KScreen::GetConfigOperation *>(op)->config();
        if (config) {
            updateWithConfig(config);
            if (m_currentConfig != config) {
                if (m_currentConfig) {
                    KScreen::ConfigMonitor::instance()->removeConfig(m_currentConfig);
                }
                m_currentConfig = config;
                KScreen::ConfigMonitor::instance()->addConfig(config);
                connect(KScreen::ConfigMonitor::instance(), &KScreen::ConfigMonitor::configurationChanged,
                        this, &ScreenHelper::reloadConfig, Qt::UniqueConnection);
            }
        }
    });
}

void ScreenHelper::updateWithConfig(const KScreen::ConfigPtr &config)
{
    if (!config) {
        return;
    }

    auto primaryOutput = config->primaryOutput();
    if (!primaryOutput) {
        const auto outputs = config->connectedOutputs();
        uint32_t minPriority = std::numeric_limits<uint32_t>::max();
        for (const auto &out : outputs) {
            if (out->isEnabled() && out->priority() < minPriority) {
                minPriority = out->priority();
                primaryOutput = out;
            }
        }
    }

    if (!primaryOutput) {
        return;
    }

    QString newName = primaryOutput->name();
    QPoint pos = primaryOutput->pos();
    QSize size = primaryOutput->size();
    qreal scale = primaryOutput->scale();
    if (scale <= 0) {
        scale = 1.0;
    }

    QRect newGeom(pos.x(), pos.y(), qRound(size.width() / scale), qRound(size.height() / scale));

    QScreen *matchedScreen = nullptr;
    for (QScreen *s : QGuiApplication::screens()) {
        if (s->name() == newName) {
            matchedScreen = s;
            break;
        }
    }

    bool changed = (m_primaryName != newName || m_primaryQScreen != matchedScreen);
    m_primaryName = newName;
    m_primaryGeometry = newGeom;
    m_primaryQScreen = matchedScreen;

    qWarning() << "[KScreen Primary Screen detected]" << newName << "geom:" << newGeom << "qscreen:" << (matchedScreen ? matchedScreen->name() : QStringLiteral("none"));

    if (changed) {
        Q_EMIT primaryScreenChanged();
    }
}

QString ScreenHelper::primaryScreenName() const
{
    if (!m_primaryName.isEmpty()) {
        return m_primaryName;
    }
    QScreen *s = QGuiApplication::primaryScreen();
    return s ? s->name() : QString();
}

QScreen *ScreenHelper::primaryScreen() const
{
    if (m_primaryQScreen) {
        return m_primaryQScreen.data();
    }
    if (!m_primaryName.isEmpty()) {
        for (QScreen *s : QGuiApplication::screens()) {
            if (s->name() == m_primaryName) {
                return s;
            }
        }
    }
    return QGuiApplication::primaryScreen();
}

QRect ScreenHelper::primaryGeometry() const
{
    if (m_primaryGeometry.isValid() && !m_primaryGeometry.isEmpty()) {
        return m_primaryGeometry;
    }
    QScreen *s = primaryScreen();
    return s ? s->geometry() : QRect();
}

bool ScreenHelper::isPrimaryScreen(const QRect &geometry) const
{
    QScreen *pScreen = primaryScreen();
    if (pScreen && pScreen->geometry() == geometry) {
        return true;
    }
    if (m_primaryGeometry.isValid()) {
        if (std::abs(m_primaryGeometry.x() - geometry.x()) <= 5 &&
            std::abs(m_primaryGeometry.y() - geometry.y()) <= 5) {
            return true;
        }
    }
    return false;
}

bool ScreenHelper::isPrimaryScreenName(const QString &name) const
{
    return primaryScreenName() == name;
}
