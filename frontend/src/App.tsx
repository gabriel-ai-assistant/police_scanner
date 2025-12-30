import { Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';

import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import LoadingScreen from './components/LoadingScreen';
import Dashboard from './pages/Dashboard';
import Feeds from './pages/Feeds';
import Calls from './pages/Calls';
import Search from './pages/Search';
import Settings from './pages/Settings';
import Admin from './pages/Admin';
import Login from './pages/Login';
import Subscriptions from './pages/Subscriptions';
import SubscriptionDetail from './pages/SubscriptionDetail';
import KeywordGroups from './pages/KeywordGroups';
import KeywordGroupDetail from './pages/KeywordGroupDetail';
import { ProtectedRoute } from './auth';

/**
 * Main app layout with sidebar and navbar
 */
function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          <Suspense fallback={<LoadingScreen />}>
            {children}
          </Suspense>
        </main>
      </div>
    </div>
  );
}

function App() {
  return (
    <Routes>
      {/* Login page - no layout */}
      <Route path="/login" element={<Login />} />

      {/* Protected routes with layout */}
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Dashboard />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/feeds"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Feeds />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/calls"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Calls />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/search"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Search />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Settings />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/subscriptions"
        element={
          <ProtectedRoute>
            <AppLayout>
              <Subscriptions />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/subscriptions/:id"
        element={
          <ProtectedRoute>
            <AppLayout>
              <SubscriptionDetail />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/keyword-groups"
        element={
          <ProtectedRoute>
            <AppLayout>
              <KeywordGroups />
            </AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/keyword-groups/:id"
        element={
          <ProtectedRoute>
            <AppLayout>
              <KeywordGroupDetail />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Admin route - requires admin role */}
      <Route
        path="/admin"
        element={
          <ProtectedRoute requireAdmin>
            <AppLayout>
              <Admin />
            </AppLayout>
          </ProtectedRoute>
        }
      />

      {/* Catch all - redirect to home */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
