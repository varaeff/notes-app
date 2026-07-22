import { useLang } from "../i18n.jsx";
import {
  TelegramConnectedPanel,
  TelegramDisconnectedPanel,
  TelegramErrorPanel,
  TelegramFeedback,
  TelegramLinkCodePanel,
  TelegramLoadingPanel,
  TelegramSettingsHeader,
} from "./TelegramSettingsPanels.jsx";
import { useTelegramSettingsCard } from "../hooks/useTelegramSettingsCard.js";

export default function TelegramSettingsCard() {
  const { t } = useLang();
  const telegramSettings = useTelegramSettingsCard(t);
  const {
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
    reminderTime,
    browserTimezone,
    isUsingBrowserTimezone,
    hasSavedTimezoneMismatch,
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
    setReminderTime,
  } = telegramSettings;

  if (settings?.is_configured === false) {
    return null;
  }

  return (
    <section className="settings-card telegram-settings-card">
      <TelegramSettingsHeader
        t={t}
        isConnected={Boolean(settings?.is_connected)}
      />

      {viewState === "loading" && <TelegramLoadingPanel t={t} />}

      {viewState === "error" && (
        <TelegramErrorPanel
          t={t}
          error={error}
          onRetry={() => loadSettings()}
        />
      )}

      {viewState === "disconnected" && (
        <TelegramDisconnectedPanel
          t={t}
          isGenerating={isGenerating}
          onGenerateCode={generateCode}
        />
      )}

      {viewState === "waiting" && linkCode && (
        <TelegramLinkCodePanel
          t={t}
          linkCode={linkCode}
          remainingSeconds={remainingSeconds}
          isExpired={isExpired}
          copied={copied}
          isChecking={isChecking}
          isGenerating={isGenerating}
          onCopyCode={copyCode}
          onCheckConnection={checkConnection}
          onGenerateCode={generateCode}
          onCancelConnection={cancelConnection}
        />
      )}

      {viewState === "connected" && (
        <TelegramConnectedPanel
          t={t}
          settings={settings}
          notificationsEnabled={notificationsEnabled}
          timezone={timezone}
          reminderTime={reminderTime}
          browserTimezone={browserTimezone}
          isUsingBrowserTimezone={isUsingBrowserTimezone}
          hasSavedTimezoneMismatch={hasSavedTimezoneMismatch}
          isSaving={isSaving}
          isSendingTest={isSendingTest}
          isDisconnecting={isDisconnecting}
          onNotificationsEnabledChange={setNotificationsEnabled}
          onTimezoneChange={setTimezone}
          onReminderTimeChange={setReminderTime}
          onSavePreferences={savePreferences}
          onSendTestNotification={sendTestNotification}
          onDisconnect={disconnect}
        />
      )}

      <TelegramFeedback
        t={t}
        operationError={operationError}
        operationMessageKey={operationMessageKey}
      />
    </section>
  );
}
