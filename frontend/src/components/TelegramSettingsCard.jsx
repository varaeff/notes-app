import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { api } from '../api.js';
import { useLang } from '../i18n.jsx';

const POLLING_DELAY_MS = 4000;

function secondsUntil(expiresAt) {
  if (!expiresAt) return 0;
  return Math.max(0, Math.ceil((new Date(expiresAt).getTime() - Date.now()) / 1000));
}

function formatRemaining(seconds) {
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes}:${String(rest).padStart(2, '0')}`;
}

function getBotUrl(botUsername) {
  return `https://t.me/${botUsername}`;
}

export default function TelegramSettingsCard() {
  const { t } = useLang();

  const [settings, setSettings] = useState(null);
  const [linkCode, setLinkCode] = useState(null);
  const [remainingSeconds, setRemainingSeconds] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isChecking, setIsChecking] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isSendingTest, setIsSendingTest] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(false);
  const [timezone, setTimezone] = useState('UTC');
  const [error, setError] = useState(null);
  const [operationError, setOperationError] = useState(null);
  const [operationMessageKey, setOperationMessageKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const pollingTimeoutRef = useRef(null);
  const copyTimeoutRef = useRef(null);

  const loadSettings = useCallback(async ({ silent = false } = {}) => {
    if (!silent) {
      setIsLoading(true);
      setError(null);
    }

    try {
      const nextSettings = await api.getTelegramSettings();
      setSettings(nextSettings);
      if (nextSettings.is_connected) {
        setLinkCode(null);
      }
      return nextSettings;
    } catch (err) {
      if (!silent) {
        setError(err.message);
      }
      throw err;
    } finally {
      if (!silent) {
        setIsLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    let active = true;

    loadSettings().catch(() => {
      if (!active) return;
    });

    return () => {
      active = false;
    };
  }, [loadSettings]);

  useEffect(() => {
    if (!settings) return;

    setNotificationsEnabled(settings.notifications_enabled);
    setTimezone(settings.timezone);
  }, [settings]);

  useEffect(() => {
    if (!linkCode) {
      setRemainingSeconds(0);
      return undefined;
    }

    const updateRemaining = () => {
      setRemainingSeconds(secondsUntil(linkCode.expires_at));
    };

    updateRemaining();
    const timerId = window.setInterval(updateRemaining, 1000);

    return () => window.clearInterval(timerId);
  }, [linkCode]);

  useEffect(() => {
    if (pollingTimeoutRef.current) {
      window.clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    if (!linkCode || settings?.is_connected || secondsUntil(linkCode.expires_at) <= 0) {
      return undefined;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const nextSettings = await loadSettings({ silent: true });
        if (cancelled) return;
        if (nextSettings.is_connected) {
          setOperationMessageKey('settings.telegram.connectedAfterPolling');
          return;
        }
      } catch {
        if (cancelled) return;
      }

      if (!cancelled && secondsUntil(linkCode.expires_at) > 0) {
        pollingTimeoutRef.current = window.setTimeout(poll, POLLING_DELAY_MS);
      }
    };

    pollingTimeoutRef.current = window.setTimeout(poll, POLLING_DELAY_MS);

    return () => {
      cancelled = true;
      if (pollingTimeoutRef.current) {
        window.clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
  }, [linkCode, loadSettings, settings?.is_connected]);

  useEffect(() => () => {
    if (pollingTimeoutRef.current) {
      window.clearTimeout(pollingTimeoutRef.current);
    }
    if (copyTimeoutRef.current) {
      window.clearTimeout(copyTimeoutRef.current);
    }
  }, []);

  const viewState = useMemo(() => {
    if (isLoading) return 'loading';
    if (error && !settings) return 'error';
    if (settings?.is_connected) return 'connected';
    if (linkCode) return 'waiting';
    return 'disconnected';
  }, [error, isLoading, linkCode, settings]);

  const clearFeedback = () => {
    setOperationError(null);
    setOperationMessageKey(null);
  };

  const generateCode = async () => {
    clearFeedback();
    setIsGenerating(true);

    try {
      const nextCode = await api.createTelegramLinkCode();
      setLinkCode(nextCode);
      setCopied(false);
      setOperationMessageKey(null);
    } catch (err) {
      setOperationError(err.message);
    } finally {
      setIsGenerating(false);
    }
  };

  const checkConnection = async () => {
    clearFeedback();
    setIsChecking(true);

    try {
      const nextSettings = await loadSettings({ silent: true });
      if (nextSettings.is_connected) {
        setOperationMessageKey('settings.telegram.connectedAfterPolling');
      } else {
        setOperationMessageKey('settings.telegram.notConnectedYet');
      }
    } catch (err) {
      setOperationError(err.message);
    } finally {
      setIsChecking(false);
    }
  };

  const copyCode = async () => {
    if (!linkCode) return;

    try {
      await navigator.clipboard.writeText(linkCode.code);
      setCopied(true);
      if (copyTimeoutRef.current) {
        window.clearTimeout(copyTimeoutRef.current);
      }
      copyTimeoutRef.current = window.setTimeout(() => setCopied(false), 1500);
    } catch {
      setOperationError(t('settings.telegram.copyFailed'));
    }
  };

  const savePreferences = async (event) => {
    event.preventDefault();
    clearFeedback();
    setIsSaving(true);

    try {
      const nextSettings = await api.updateTelegramSettings({
        notifications_enabled: notificationsEnabled,
        timezone,
      });
      setSettings(nextSettings);
      setOperationMessageKey('settings.telegram.preferencesSaved');
    } catch (err) {
      setOperationError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const sendTestNotification = async () => {
    clearFeedback();
    setIsSendingTest(true);

    try {
      await api.sendTelegramTestNotification();
      setOperationMessageKey('settings.telegram.testSent');
    } catch (err) {
      setOperationError(err.message);
      if (err.status === 409) {
        await loadSettings({ silent: true }).catch(() => {});
      }
    } finally {
      setIsSendingTest(false);
    }
  };

  const disconnect = async () => {
    if (!window.confirm(t('settings.telegram.confirmDisconnect'))) return;

    clearFeedback();
    setIsDisconnecting(true);

    try {
      const nextSettings = await api.disconnectTelegram();
      setSettings(nextSettings);
      setLinkCode(null);
      setOperationMessageKey('settings.telegram.disconnected');
    } catch (err) {
      setOperationError(err.message);
    } finally {
      setIsDisconnecting(false);
    }
  };

  const cancelConnection = () => {
    clearFeedback();
    setLinkCode(null);
  };

  const isExpired = Boolean(linkCode) && remainingSeconds <= 0;

  return (
    <section className="settings-card telegram-settings-card">
      <div className="telegram-settings-header">
        <div>
          <h2>{t('settings.telegram.title')}</h2>
          {!settings?.is_connected && (
            <p className="settings-hint">{t('settings.telegram.hint')}</p>
          )}
        </div>
        {settings?.is_connected && (
          <span className="telegram-status connected">{t('settings.telegram.connected')}</span>
        )}
      </div>

      {viewState === 'loading' && (
        <div className="telegram-panel muted">{t('settings.telegram.loading')}</div>
      )}

      {viewState === 'error' && (
        <div className="telegram-panel">
          <div className="error">{error || t('settings.telegram.loadFailed')}</div>
          <button className="btn" type="button" onClick={() => loadSettings()}>
            {t('settings.telegram.retry')}
          </button>
        </div>
      )}

      {viewState === 'disconnected' && (
        <div className="telegram-panel">
          <p>{t('settings.telegram.disconnectedHint')}</p>
          <button
            className="btn btn-primary"
            type="button"
            onClick={generateCode}
            disabled={isGenerating}
          >
            {isGenerating ? t('settings.telegram.generating') : t('settings.telegram.connect')}
          </button>
        </div>
      )}

      {viewState === 'waiting' && linkCode && (
        <div className="telegram-panel">
          <div className="telegram-code-row">
            <div>
              <span className="telegram-label">{t('settings.telegram.code')}</span>
              <strong className="telegram-code">{linkCode.code}</strong>
            </div>
            <button className="btn" type="button" onClick={copyCode}>
              {copied ? t('settings.telegram.copied') : t('settings.telegram.copy')}
            </button>
          </div>

          <p>
            {t('settings.telegram.sendCodeTo')}{' '}
            <a href={getBotUrl(linkCode.bot_username)} target="_blank" rel="noreferrer">
              @{linkCode.bot_username}
            </a>
          </p>

          <div className="telegram-meta">
            {isExpired
              ? t('settings.telegram.codeExpired')
              : t('settings.telegram.expiresIn', { time: formatRemaining(remainingSeconds) })}
          </div>

          <div className="telegram-actions">
            <button className="btn" type="button" onClick={checkConnection} disabled={isChecking}>
              {isChecking ? t('settings.telegram.checking') : t('settings.telegram.check')}
            </button>
            <button
              className="btn"
              type="button"
              onClick={generateCode}
              disabled={isGenerating}
            >
              {isGenerating ? t('settings.telegram.generating') : t('settings.telegram.regenerate')}
            </button>
            <button className="btn btn-ghost" type="button" onClick={cancelConnection}>
              {t('settings.telegram.cancel')}
            </button>
          </div>
        </div>
      )}

      {viewState === 'connected' && (
        <div className="telegram-panel">
          <p>
            {settings.username
              ? t('settings.telegram.connectedAs', { username: settings.username })
              : t('settings.telegram.connectedNoUsername')}
          </p>

          <form className="telegram-preferences" onSubmit={savePreferences}>
            <label className="telegram-checkbox">
              <input
                type="checkbox"
                checked={notificationsEnabled}
                onChange={(event) => setNotificationsEnabled(event.target.checked)}
              />
              {t('settings.telegram.notificationsEnabled')}
            </label>
            <label>
              {t('settings.telegram.timezone')}
              <input
                value={timezone}
                onChange={(event) => setTimezone(event.target.value)}
                placeholder="UTC"
              />
            </label>
            <div className="telegram-actions telegram-connected-actions">
              <button className="btn" type="submit" disabled={isSaving}>
                {isSaving ? t('settings.telegram.saving') : t('settings.telegram.save')}
              </button>
              <button
                className="btn"
                type="button"
                onClick={sendTestNotification}
                disabled={isSendingTest}
              >
                {isSendingTest ? t('settings.telegram.sendingTest') : t('settings.telegram.sendTest')}
              </button>
              <button
                className="btn btn-danger"
                type="button"
                onClick={disconnect}
                disabled={isDisconnecting}
              >
                {isDisconnecting ? t('settings.telegram.disconnecting') : t('settings.telegram.disconnect')}
              </button>
            </div>
          </form>
        </div>
      )}

      {operationError && <div className="error">{operationError}</div>}
      {operationMessageKey && <div className="success">{t(operationMessageKey)}</div>}
    </section>
  );
}
