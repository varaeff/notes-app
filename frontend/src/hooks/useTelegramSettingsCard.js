import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { api } from "../api.js";
import { secondsUntil } from "../utils/telegramSettings.js";

const POLLING_DELAY_MS = 4000;

export function useTelegramSettingsCard(t) {
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
  const [timezone, setTimezone] = useState("UTC");
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

    if (
      !linkCode ||
      settings?.is_connected ||
      secondsUntil(linkCode.expires_at) <= 0
    ) {
      return undefined;
    }

    let cancelled = false;

    const poll = async () => {
      try {
        const nextSettings = await loadSettings({ silent: true });
        if (cancelled) return;
        if (nextSettings.is_connected) {
          setOperationMessageKey("settings.telegram.connectedAfterPolling");
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

  useEffect(
    () => () => {
      if (pollingTimeoutRef.current) {
        window.clearTimeout(pollingTimeoutRef.current);
      }
      if (copyTimeoutRef.current) {
        window.clearTimeout(copyTimeoutRef.current);
      }
    },
    [],
  );

  const viewState = useMemo(() => {
    if (isLoading) return "loading";
    if (error && !settings) return "error";
    if (settings?.is_connected) return "connected";
    if (linkCode) return "waiting";
    return "disconnected";
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
        setOperationMessageKey("settings.telegram.connectedAfterPolling");
      } else {
        setOperationMessageKey("settings.telegram.notConnectedYet");
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
      setOperationError(t("settings.telegram.copyFailed"));
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
      setOperationMessageKey("settings.telegram.preferencesSaved");
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
      setOperationMessageKey("settings.telegram.testSent");
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
    if (!window.confirm(t("settings.telegram.confirmDisconnect"))) return;

    clearFeedback();
    setIsDisconnecting(true);

    try {
      const nextSettings = await api.disconnectTelegram();
      setSettings(nextSettings);
      setLinkCode(null);
      setOperationMessageKey("settings.telegram.disconnected");
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

  return {
    settings,
    linkCode,
    remainingSeconds,
    viewState,
    error,
    operationError,
    operationMessageKey,
    copied,
    isExpired,
    isGenerating,
    isChecking,
    isSaving,
    isSendingTest,
    isDisconnecting,
    notificationsEnabled,
    timezone,
    loadSettings,
    generateCode,
    checkConnection,
    copyCode,
    savePreferences,
    sendTestNotification,
    disconnect,
    cancelConnection,
    setNotificationsEnabled,
    setTimezone,
  };
}
