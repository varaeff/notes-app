import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import TelegramSettingsCard from './TelegramSettingsCard.jsx';
import { LangProvider, useLang } from '../i18n.jsx';

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  };
}

function telegramSettings(overrides = {}) {
  return {
    is_connected: false,
    username: null,
    notifications_enabled: false,
    timezone: 'UTC',
    ...overrides,
  };
}

function renderCard() {
  return render(
    <LangProvider>
      <TelegramSettingsCard />
    </LangProvider>
  );
}

function LanguageSwitch() {
  const { setLang } = useLang();
  return (
    <div>
      <button type="button" onClick={() => setLang('en')}>
        EN
      </button>
      <button type="button" onClick={() => setLang('ru')}>
        RU
      </button>
    </div>
  );
}

function renderCardWithLanguageSwitch() {
  return render(
    <LangProvider>
      <LanguageSwitch />
      <TelegramSettingsCard />
    </LangProvider>
  );
}

function mockFetchQueue(responses) {
  vi.stubGlobal('fetch', vi.fn((url, options = {}) => {
    const next = responses.shift();
    if (!next) {
      throw new Error(`Unexpected request: ${options.method || 'GET'} ${url}`);
    }
    next.assert?.(url, options);
    return Promise.resolve(jsonResponse(next.body, next.status));
  }));
}

beforeEach(() => {
  localStorage.setItem('notes_token', 'test-token');
  Object.defineProperty(navigator, 'clipboard', {
    configurable: true,
    value: { writeText: vi.fn(() => Promise.resolve()) },
  });
  window.confirm = vi.fn(() => true);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  localStorage.clear();
});

describe('TelegramSettingsCard', () => {
  it('renders disconnected state after loading settings', async () => {
    mockFetchQueue([{ body: telegramSettings() }]);

    renderCard();

    expect(screen.getByText('Loading Telegram settings...')).toBeInTheDocument();
    expect(await screen.findByText('Telegram is not connected yet.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Connect Telegram' })).toBeInTheDocument();
  });

  it('shows generated code and connection controls', async () => {
    const user = userEvent.setup();
    mockFetchQueue([
      { body: telegramSettings() },
      {
        assert: (url, options) => {
          expect(url).toBe('/api/settings/telegram/link-code');
          expect(options.method).toBe('POST');
        },
        body: {
          code: '000042',
          expires_at: new Date(Date.now() + 60_000).toISOString(),
          bot_username: 'test_notes_bot',
        },
      },
    ]);

    renderCard();

    await user.click(await screen.findByRole('button', { name: 'Connect Telegram' }));

    expect(await screen.findByText('000042')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '@test_notes_bot' })).toHaveAttribute(
      'href',
      'https://t.me/test_notes_bot'
    );
    expect(screen.getByRole('button', { name: 'Check connection' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Generate new code' })).toBeInTheDocument();
  });

  it('polls settings and moves to connected state', async () => {
    const user = userEvent.setup();
    mockFetchQueue([
      { body: telegramSettings() },
      {
        body: {
          code: '483921',
          expires_at: new Date(Date.now() + 60_000).toISOString(),
          bot_username: 'test_notes_bot',
        },
      },
      { body: telegramSettings({ is_connected: true, username: 'alice' }) },
    ]);

    renderCard();

    await user.click(await screen.findByRole('button', { name: 'Connect Telegram' }));
    expect(await screen.findByText('483921')).toBeInTheDocument();

    expect(
      await screen.findByText('Connected as @alice.', {}, { timeout: 6000 })
    ).toBeInTheDocument();
  }, 10000);

  it('sends test notification in connected state', async () => {
    const user = userEvent.setup();
    mockFetchQueue([
      { body: telegramSettings({ is_connected: true, username: 'alice' }) },
      {
        assert: (url, options) => {
          expect(url).toBe('/api/settings/telegram/test');
          expect(options.method).toBe('POST');
        },
        body: { success: true, message: 'Test notification sent' },
      },
    ]);

    renderCard();

    expect(
      await screen.findByText('Connected as @alice.')
    ).toBeInTheDocument();
    expect(
      screen.queryByText('Connect Telegram to receive note reminders and verify delivery.')
    ).not.toBeInTheDocument();

    await user.click(await screen.findByRole('button', { name: 'Send test notification' }));

    expect(await screen.findByText('Test notification sent')).toBeInTheDocument();
  });

  it('retranslates success feedback when language changes', async () => {
    const user = userEvent.setup();
    mockFetchQueue([
      { body: telegramSettings({ is_connected: true, username: 'alice' }) },
      { body: { success: true, message: 'Test notification sent' } },
    ]);

    renderCardWithLanguageSwitch();

    await user.click(await screen.findByRole('button', { name: 'Send test notification' }));

    expect(await screen.findByText('Test notification sent')).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'RU' }));

    expect(await screen.findByText('Тестовое уведомление отправлено')).toBeInTheDocument();
    expect(screen.queryByText('Test notification sent')).not.toBeInTheDocument();
  });

  it('disconnects after confirmation', async () => {
    const user = userEvent.setup();
    mockFetchQueue([
      { body: telegramSettings({ is_connected: true, username: 'alice' }) },
      {
        assert: (url, options) => {
          expect(url).toBe('/api/settings/telegram/link');
          expect(options.method).toBe('DELETE');
        },
        body: telegramSettings(),
      },
    ]);

    renderCard();

    await user.click(await screen.findByRole('button', { name: 'Disconnect' }));

    expect(window.confirm).toHaveBeenCalledWith('Disconnect Telegram?');
    expect(await screen.findByText('Telegram disconnected.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Connect Telegram' })).toBeInTheDocument();
  });

  it('saves notification preferences and timezone', async () => {
    const user = userEvent.setup();
    mockFetchQueue([
      { body: telegramSettings({ is_connected: true, username: 'alice' }) },
      {
        assert: (url, options) => {
          expect(url).toBe('/api/settings/telegram');
          expect(options.method).toBe('PATCH');
          expect(JSON.parse(options.body)).toEqual({
            notifications_enabled: true,
            timezone: 'Asia/Tbilisi',
          });
        },
        body: telegramSettings({
          is_connected: true,
          username: 'alice',
          notifications_enabled: true,
          timezone: 'Asia/Tbilisi',
        }),
      },
    ]);

    renderCard();

    await user.click(await screen.findByLabelText('Enable reminder notifications'));
    await user.clear(screen.getByLabelText('Timezone'));
    await user.type(screen.getByLabelText('Timezone'), 'Asia/Tbilisi');
    await user.click(screen.getByRole('button', { name: 'Save preferences' }));

    await waitFor(() => {
      expect(screen.getByText('Telegram preferences saved.')).toBeInTheDocument();
    });
  });
});
