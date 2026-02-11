import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Switch } from '../components/ui/switch';
import { Label } from '../components/ui/label';

function NotificationSettings() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Notification Settings</h1>
        <p className="text-muted-foreground">
          Configure how and when you receive alerts from your subscribed feeds.
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Push Notifications</CardTitle>
          <CardDescription>
            Receive browser push notifications for keyword matches.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
            <div>
              <Label className="text-sm font-medium">Enable push notifications</Label>
              <p className="text-xs text-muted-foreground">
                Get notified when keywords are detected in your subscribed feeds.
              </p>
            </div>
            <Switch disabled />
          </div>
          <p className="text-xs text-muted-foreground italic">
            Push notifications are coming soon. Subscribe to feeds and configure keyword groups to get started.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Email Notifications</CardTitle>
          <CardDescription>
            Receive email digests and alerts.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
            <div>
              <Label className="text-sm font-medium">Daily digest</Label>
              <p className="text-xs text-muted-foreground">
                Receive a daily summary of activity from your subscribed feeds.
              </p>
            </div>
            <Switch disabled />
          </div>
          <div className="flex items-center justify-between rounded-md border border-border bg-muted/20 p-4">
            <div>
              <Label className="text-sm font-medium">Keyword alerts</Label>
              <p className="text-xs text-muted-foreground">
                Get emailed when high-priority keywords are detected.
              </p>
            </div>
            <Switch disabled />
          </div>
          <p className="text-xs text-muted-foreground italic">
            Email notifications are coming soon.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

export default NotificationSettings;
