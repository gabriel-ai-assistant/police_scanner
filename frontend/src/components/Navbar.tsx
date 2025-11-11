import { useState } from 'react';
import { Menu, Moon, RefreshCw, Search, Sun } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';

import { Button } from './ui/button';
import { Input } from './ui/input';
import { useTheme } from '../lib/theme';

function Navbar() {
  const location = useLocation();
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const [query, setQuery] = useState('');

  const handleSearch = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (query.trim().length === 0) return;
    navigate(`/search?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <header className="flex items-center justify-between border-b border-border/60 bg-background/80 px-6 py-3 backdrop-blur">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" className="md:hidden">
          <Menu className="h-5 w-5" />
        </Button>
        <Link to="/" className="text-lg font-semibold">
          Police Scanner
        </Link>
        <span className="hidden text-sm text-muted-foreground md:inline">{location.pathname}</span>
      </div>
      <div className="flex items-center gap-3">
        <form onSubmit={handleSearch} className="hidden items-center gap-2 rounded-md border border-input bg-background px-2 py-1 md:flex">
          <Search className="h-4 w-4 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search transcripts"
            className="border-none bg-transparent p-0 focus-visible:ring-0"
          />
        </form>
        <Button variant="ghost" size="icon" onClick={() => window.location.reload()} title="Refresh data">
          <RefreshCw className="h-5 w-5" />
        </Button>
        <Button variant="ghost" size="icon" onClick={toggleTheme} title="Toggle theme">
          {theme === 'dark' ? <Sun className="h-5 w-5" /> : <Moon className="h-5 w-5" />}
        </Button>
      </div>
    </header>
  );
}

export default Navbar;
