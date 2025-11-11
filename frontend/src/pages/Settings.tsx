import { useEffect, useState } from 'react';

import { getCurrentApiBaseUrl, setApiBaseUrl } from '../api/client';
import { useTheme } from '../lib/theme';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';

const REFRESH_KEY = 'police-scanner-refresh-interval';

function Settings() {
  const { theme, setTheme } = useTheme();
  const [apiUrl, setApiUrlState] = useState('');
  const [refreshInterval, setRefreshInterval] = useState(30);
  const [statusMessage, setStatusMessage] = useState('');

  useEffect(() => {
    setApiUrlState(getCurrentApiBaseUrl());
    const storedInterval = typeof window !== 'undefined' ? window.localStorage.getItem(REFRESH_KEY) : null;
    if (storedInterval) {
      setRefreshInterval(Number(storedInterval));
    }
  }, []);

  const handleThemeToggle = (checked: boolean) => {
    setTheme(checked ? 'dark' : 'light');
    setStatusMessage(`Theme set to ${checked ? 'dark' : 'light'}.`);
  };

  const handleApiSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApiBaseUrl(apiUrl.trim());
    setStatusMessage('API base URL updated. Changes apply immediately.');
  };

  const handleRefreshChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    setRefreshInterval(value);
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(REFRESH_KEY, value.toString());
    }
    setStatusMessage('Auto-refresh interval updated.');
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Theme</CardTitle>
          <CardDescription>Switch between light and dark modes.</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
            <div>
              <p className="text-sm font-medium">Dark mode</p>
              <p className="text-xs text-muted-foreground">Toggle to enable the dark UI theme.</p>
            </div>
            <Switch checked={theme === 'dark'} onCheckedChange={handleThemeToggle} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>API Connection</CardTitle>
          <CardDescription>Configure the backend URL used for HTTP requests.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleApiSubmit}>
            <div className="space-y-2">
              <Label htmlFor="api-url">API Base URL</Label>
              <Input
                id="api-url"
                value={apiUrl}
                onChange={(event) => setApiUrlState(event.target.value)}
                placeholder="https://scanner.example.com"
              />
              <p className="text-xs text-muted-foreground">
                Defaults to <code>{import.meta.env.VITE_API_URL ?? '/api'}</code> if left blank.
              </p>
            </div>
            <Button type="submit">Save</Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Auto Refresh</CardTitle>
          <CardDescription>Control how frequently background queries refresh.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="refresh-interval">Refresh interval (seconds)</Label>
            <Input
              id="refresh-interval"
              type="number"
              min={10}
              max={600}
              value={refreshInterval}
              onChange={handleRefreshChange}
            />
          </div>
          <p className="text-xs text-muted-foreground">
            Pages will use this value as a hint for their polling frequency where applicable.
          </p>
        </CardContent>
        {statusMessage ? (
          <CardFooter>
            <p className="text-sm text-muted-foreground">{statusMessage}</p>
          </CardFooter>
        ) : null}
      </Card>
    </div>
  );
}

export default Settings;
