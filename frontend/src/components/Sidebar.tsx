import { Radio, Search, Settings, Waves, LayoutDashboard, Sliders } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import { cn } from '../lib/utils';

const links = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/feeds', label: 'Feeds', icon: Radio },
  { to: '/calls', label: 'Calls', icon: Waves },
  { to: '/search', label: 'Search', icon: Search },
  { to: '/admin', label: 'Admin', icon: Sliders },
  { to: '/settings', label: 'Settings', icon: Settings }
];

function Sidebar() {
  return (
    <aside className="hidden w-60 border-r border-border bg-background/95 p-6 md:flex md:flex-col">
      <div className="mb-6 text-xl font-semibold">Scanner Control</div>
      <nav className="flex flex-1 flex-col gap-2">
        {links.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground',
                isActive ? 'bg-primary text-primary-foreground shadow-sm' : 'text-muted-foreground'
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}

export default Sidebar;
