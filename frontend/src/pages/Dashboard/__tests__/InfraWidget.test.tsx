import { describe, it, expect, vi, beforeEach } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { renderWithProviders } from '../../../test/test-utils';
import apiClient from '../../../api/client';
import InfraWidget from '../InfraWidget';

vi.mock('../../../api/client', () => ({
  default: {
    post: vi.fn(),
  },
}));

describe('InfraWidget', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders button with label', () => {
    renderWithProviders(<InfraWidget />);
    expect(screen.getByText('Apagar Dream Machine')).toBeInTheDocument();
  });

  it('shows loading state while request is in flight', async () => {
    vi.mocked(apiClient.post).mockImplementation(
      () => new Promise(() => {}),
    );

    renderWithProviders(<InfraWidget />);
    const user = userEvent.setup();

    await user.click(screen.getByText('Apagar Dream Machine'));
    expect(await screen.findByText('Apagando...')).toBeInTheDocument();
  });

  it('shows success feedback on successful shutdown', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({
      data: { status: 'ok', message: 'Shutdown command sent to Dream Machine' },
    });

    renderWithProviders(<InfraWidget />);
    const user = userEvent.setup();
    await user.click(screen.getByText('Apagar Dream Machine'));

    await waitFor(() => {
      expect(screen.getByText('Shutdown command sent to Dream Machine')).toBeInTheDocument();
    });
  });

  it('shows error feedback on API failure', async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { detail: 'Failed to connect' } },
    });

    renderWithProviders(<InfraWidget />);
    const user = userEvent.setup();
    await user.click(screen.getByText('Apagar Dream Machine'));

    await waitFor(() => {
      expect(screen.getByText('Failed to connect')).toBeInTheDocument();
    });
  });
});
