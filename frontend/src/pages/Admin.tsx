import { useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import GeographyTree from '../components/admin/GeographyTree';
import PlaylistManager from '../components/admin/PlaylistManager';
import ProcessingPipeline from '../components/admin/ProcessingPipeline';

function Admin() {
  const [activeTab, setActiveTab] = useState('geography');

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Administration</h1>
        <p className="text-muted-foreground">Configure scanner settings, playlists, and monitoring.</p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="geography">Geographic Sync</TabsTrigger>
          <TabsTrigger value="playlists">Playlists</TabsTrigger>
          <TabsTrigger value="monitoring">Monitoring</TabsTrigger>
        </TabsList>

        <TabsContent value="geography" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Geographic Sync Configuration</CardTitle>
              <CardDescription>
                Enable or disable countries, states, and counties for monitoring.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <GeographyTree />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="playlists" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Playlist Management</CardTitle>
              <CardDescription>
                Manage which Broadcastify playlists are actively monitored.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <PlaylistManager />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="monitoring" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Processing Pipeline</CardTitle>
              <CardDescription>
                Monitor the status of call processing through the pipeline.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ProcessingPipeline />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default Admin;
