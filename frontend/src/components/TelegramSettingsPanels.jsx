import { formatRemaining, getBotUrl } from "../utils/telegramSettings.js";

export function TelegramSettingsHeader({ t, isConnected }) {
  return (
    <div className="telegram-settings-header">
      <div>
        <h2>{t("settings.telegram.title")}</h2>
        {!isConnected && (
          <p className="settings-hint">{t("settings.telegram.hint")}</p>
        )}
      </div>
      {isConnected && (
        <span className="telegram-status connected">
          {t("settings.telegram.connected")}
        </span>
      )}
    </div>
  );
}

export function TelegramLoadingPanel({ t }) {
  return (
    <div className="telegram-panel muted">{t("settings.telegram.loading")}</div>
  );
}

export function TelegramErrorPanel({ t, error, onRetry }) {
  return (
    <div className="telegram-panel">
      <div className="error">{error || t("settings.telegram.loadFailed")}</div>
      <button className="btn" type="button" onClick={onRetry}>
        {t("settings.telegram.retry")}
      </button>
    </div>
  );
}

export function TelegramDisconnectedPanel({ t, isGenerating, onGenerateCode }) {
  return (
    <div className="telegram-panel">
      <p>{t("settings.telegram.disconnectedHint")}</p>
      <button
        className="btn btn-primary"
        type="button"
        onClick={onGenerateCode}
        disabled={isGenerating}
      >
        {isGenerating
          ? t("settings.telegram.generating")
          : t("settings.telegram.connect")}
      </button>
    </div>
  );
}

export function TelegramLinkCodePanel({
  t,
  linkCode,
  remainingSeconds,
  isExpired,
  copied,
  isChecking,
  isGenerating,
  onCopyCode,
  onCheckConnection,
  onGenerateCode,
  onCancelConnection,
}) {
  return (
    <div className="telegram-panel">
      <div className="telegram-code-row">
        <div>
          <span className="telegram-label">{t("settings.telegram.code")}</span>
          <strong className="telegram-code">{linkCode.code}</strong>
        </div>
        <button className="btn" type="button" onClick={onCopyCode}>
          {copied ? t("settings.telegram.copied") : t("settings.telegram.copy")}
        </button>
      </div>

      <p>
        {t("settings.telegram.sendCodeTo")}{" "}
        <a
          href={getBotUrl(linkCode.bot_username)}
          target="_blank"
          rel="noreferrer"
        >
          @{linkCode.bot_username}
        </a>
      </p>

      <div className="telegram-meta">
        {isExpired
          ? t("settings.telegram.codeExpired")
          : t("settings.telegram.expiresIn", {
              time: formatRemaining(remainingSeconds),
            })}
      </div>

      <div className="telegram-actions">
        <button
          className="btn"
          type="button"
          onClick={onCheckConnection}
          disabled={isChecking}
        >
          {isChecking
            ? t("settings.telegram.checking")
            : t("settings.telegram.check")}
        </button>
        <button
          className="btn"
          type="button"
          onClick={onGenerateCode}
          disabled={isGenerating}
        >
          {isGenerating
            ? t("settings.telegram.generating")
            : t("settings.telegram.regenerate")}
        </button>
        <button
          className="btn btn-ghost"
          type="button"
          onClick={onCancelConnection}
        >
          {t("settings.telegram.cancel")}
        </button>
      </div>
    </div>
  );
}

export function TelegramConnectedPanel({
  t,
  settings,
  notificationsEnabled,
  timezone,
  isSaving,
  isSendingTest,
  isDisconnecting,
  onNotificationsEnabledChange,
  onTimezoneChange,
  onSavePreferences,
  onSendTestNotification,
  onDisconnect,
}) {
  return (
    <div className="telegram-panel">
      <p>
        {settings.username
          ? t("settings.telegram.connectedAs", { username: settings.username })
          : t("settings.telegram.connectedNoUsername")}
      </p>

      <form className="telegram-preferences" onSubmit={onSavePreferences}>
        <label className="telegram-checkbox">
          <input
            type="checkbox"
            checked={notificationsEnabled}
            onChange={(event) =>
              onNotificationsEnabledChange(event.target.checked)
            }
          />
          {t("settings.telegram.notificationsEnabled")}
        </label>
        <label>
          {t("settings.telegram.timezone")}
          <input
            value={timezone}
            onChange={(event) => onTimezoneChange(event.target.value)}
            placeholder="UTC"
          />
        </label>
        <div className="telegram-actions telegram-connected-actions">
          <button className="btn" type="submit" disabled={isSaving}>
            {isSaving
              ? t("settings.telegram.saving")
              : t("settings.telegram.save")}
          </button>
          <button
            className="btn"
            type="button"
            onClick={onSendTestNotification}
            disabled={isSendingTest}
          >
            {isSendingTest
              ? t("settings.telegram.sendingTest")
              : t("settings.telegram.sendTest")}
          </button>
          <button
            className="btn btn-danger"
            type="button"
            onClick={onDisconnect}
            disabled={isDisconnecting}
          >
            {isDisconnecting
              ? t("settings.telegram.disconnecting")
              : t("settings.telegram.disconnect")}
          </button>
        </div>
      </form>
    </div>
  );
}

export function TelegramFeedback({ t, operationError, operationMessageKey }) {
  return (
    <>
      {operationError && <div className="error">{operationError}</div>}
      {operationMessageKey && (
        <div className="success">{t(operationMessageKey)}</div>
      )}
    </>
  );
}
