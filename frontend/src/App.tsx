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

function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col">
        <Navbar />
        <main className="flex-1 overflow-y-auto bg-muted/30 p-6">
          <Suspense fallback={<LoadingScreen />}>            
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/feeds" element={<Feeds />} />
              <Route path="/calls" element={<Calls />} />
              <Route path="/search" element={<Search />} />
              <Route path="/settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  );
}

export default App;
