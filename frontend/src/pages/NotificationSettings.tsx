import { useState } from 'react';

import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Switch } from '../components/ui/switch';

function NotificationSettings() {
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [emailAddress, setEmailAddress] = useState('');
  const [keywordAlerts, setKeywordAlerts] = useState(true);
  const [statusMessage, setStatusMessage] = useState('');

  const handleSave = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    // TODO: persist notification settings via API
    setStatusMessage('Notification settings saved.');
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Notification Channels</CardTitle>
          <CardDescription>Choose how you want to receive alerts.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
            <div>
              <p className="text-sm font-medium">Email notifications</p>
              <p className="text-xs text-muted-foreground">Receive alerts via email.</p>
            </div>
            <Switch checked={emailEnabled} onCheckedChange={setEmailEnabled} />
          </div>

          {emailEnabled && (
            <div className="space-y-2 pl-2">
              <Label htmlFor="email-address">Email address</Label>
              <Input
                id="email-address"
                type="email"
                value={emailAddress}
                onChange={(e) => setEmailAddress(e.target.value)}
                placeholder="you@example.com"
              />
            </div>
          )}

          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
            <div>
              <p className="text-sm font-medium">Push notifications</p>
              <p className="text-xs text-muted-foreground">Receive browser push notifications.</p>
            </div>
            <Switch checked={pushEnabled} onCheckedChange={setPushEnabled} />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Alert Preferences</CardTitle>
          <CardDescription>Configure what triggers notifications.</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={handleSave}>
            <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
              <div>
                <p className="text-sm font-medium">Keyword alerts</p>
                <p className="text-xs text-muted-foreground">
                  Get notified when transcripts match your keyword groups.
                </p>
              </div>
              <Switch checked={keywordAlerts} onCheckedChange={setKeywordAlerts} />
            </div>

            <Button type="submit">Save Preferences</Button>
          </form>
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

export default NotificationSettings;
