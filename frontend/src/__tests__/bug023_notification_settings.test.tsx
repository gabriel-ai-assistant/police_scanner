/**
 * BUG-023: Verify NotificationSettings page renders correctly.
 *
 * Requires: vitest, @testing-library/react, jsdom
 *   npm i -D vitest @testing-library/react @testing-library/jest-dom jsdom
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import NotificationSettings from '@/pages/NotificationSettings';

describe('BUG-023: NotificationSettings page', () => {
  it('renders the page title', () => {
    render(<NotificationSettings />);
    expect(screen.getByText('Notification Settings')).toBeInTheDocument();
  });

  it('renders Push Notifications section', () => {
    render(<NotificationSettings />);
    expect(screen.getByText('Push Notifications')).toBeInTheDocument();
  });

  it('renders Email Notifications section', () => {
    render(<NotificationSettings />);
    expect(screen.getByText('Email Notifications')).toBeInTheDocument();
  });

  it('has disabled switches (placeholder UI)', () => {
    render(<NotificationSettings />);
    const switches = screen.getAllByRole('switch');
    switches.forEach((sw) => {
      expect(sw).toBeDisabled();
    });
  });

  it('shows "coming soon" messages', () => {
    render(<NotificationSettings />);
    expect(screen.getByText(/coming soon/i)).toBeInTheDocument();
  });
});
