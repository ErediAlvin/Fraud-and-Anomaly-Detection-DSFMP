import { NavLink, useNavigate } from 'react-router';
import {
  LayoutDashboard,
  AlertTriangle,
  Briefcase,
  Users,
  CreditCard,
  Package,
  Database,
  Shield,
  FileText,
  Activity,
  FileCheck,
  Settings,
  ChevronLeft,
  ChevronRight,
  LogOut,
  User as UserIcon,
  ShieldCheck,
} from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import { useAuth } from '../context/AuthContext';

const navItems = [
  { path: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { path: '/alerts', icon: AlertTriangle, label: 'Fraud Alerts' },
  { path: '/cases', icon: Briefcase, label: 'Case Management' },
  { path: '/beneficiaries', icon: Users, label: 'Beneficiary Monitor' },
  { path: '/transactions', icon: CreditCard, label: 'Transaction Monitor' },
  { path: '/supply-chain', icon: Package, label: 'Supply Chain Monitor' },
  { path: '/blockchain', icon: Database, label: 'Blockchain Ledger' },
  { path: '/risk-profiles', icon: Shield, label: 'Risk Profiles' },
  { path: '/reports', icon: FileText, label: 'Reports & Analytics' },
  { path: '/model-performance', icon: Activity, label: 'Model Performance' },
  { path: '/procedures', icon: FileCheck, label: 'SOB / COB Procedures' },
  { path: '/settings', icon: Settings, label: 'System Settings' },
];

function formatRole(role?: string): string {
  switch (role) {
    case 'system_admin':
      return 'System Administrator';
    case 'fraud_analyst':
      return 'Fraud Analyst';
    case 'supervisor':
      return 'Supervisor';
    case 'county_officer':
      return 'County Officer';
    case 'school_admin':
      return 'School Administrator';
    default:
      return role ? role.replace(/_/g, ' ') : 'System Administrator';
  }
}

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const userButtonRef = useRef<HTMLButtonElement>(null);

  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const displayName = user
    ? `${user.firstName || ''} ${user.lastName || ''}`.trim() || 'Admin User'
    : 'Admin User';

  const initials = user
    ? `${user.firstName?.[0] || ''}${user.lastName?.[0] || ''}`.toUpperCase() || 'AD'
    : 'AD';

  const roleLabel = formatRole(user?.role);

  // Close popup on click outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        menuRef.current &&
        !menuRef.current.contains(event.target as Node) &&
        userButtonRef.current &&
        !userButtonRef.current.contains(event.target as Node)
      ) {
        setIsMenuOpen(false);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setIsMenuOpen(false);
      }
    }

    if (isMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      document.addEventListener('keydown', handleKeyDown);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMenuOpen]);

  const handleLogout = async () => {
    setIsMenuOpen(false);
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <aside
      className={`bg-[#1A3C5E] text-white transition-all duration-300 flex flex-col relative select-none ${
        collapsed ? 'w-16' : 'w-60'
      }`}
    >
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          {!collapsed && (
            <div>
              <h1 className="font-bold text-lg">DSFMP</h1>
              <p className="text-xs text-white/70">Fraud Detection</p>
            </div>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 hover:bg-white/10 rounded cursor-pointer transition-colors"
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {collapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 py-4 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors ${
                isActive ? 'bg-white/10 border-l-4 border-[#2E7D52]' : ''
              } ${collapsed ? 'justify-center' : ''}`
            }
            title={collapsed ? item.label : undefined}
          >
            <item.icon className="w-5 h-5 flex-shrink-0" />
            {!collapsed && <span className="text-sm">{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User Section & Pop-out Menu */}
      <div className="p-4 border-t border-white/10 relative">
        {/* The Clickable User Info Bar */}
        <button
          ref={userButtonRef}
          type="button"
          onClick={() => setIsMenuOpen((prev) => !prev)}
          className={`w-full flex items-center gap-3 p-1.5 -m-1.5 rounded-lg hover:bg-white/10 transition-all cursor-pointer text-left focus:outline-hidden ${
            collapsed ? 'justify-center' : ''
          } ${isMenuOpen ? 'bg-white/15 ring-2 ring-white/20' : ''}`}
          title="Click to view account and log out"
          aria-expanded={isMenuOpen}
          aria-haspopup="true"
        >
          <div className="w-8 h-8 rounded-full bg-[#2E7D52] flex-shrink-0 flex items-center justify-center text-sm font-bold shadow-xs">
            {initials}
          </div>
          {!collapsed && (
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate text-white leading-tight">{displayName}</p>
              <p className="text-xs text-white/70 truncate mt-0.5">{roleLabel}</p>
            </div>
          )}
        </button>

        {/* Pop-out Dropdown Menu */}
        {isMenuOpen && (
          <div
            ref={menuRef}
            className={`absolute bg-white text-[#1C1C1E] rounded-xl shadow-2xl border border-gray-200 z-50 transition-all animate-in fade-in zoom-in-95 duration-150 ${
              collapsed
                ? 'bottom-3 left-16 ml-3 w-64 p-3.5'
                : 'bottom-full mb-3 left-3 right-3 p-3.5'
            }`}
          >
            {/* User Profile Header in Popout */}
            <div className="flex items-start gap-3 pb-3 border-b border-gray-100">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-[#1A3C5E] to-[#2E7D52] flex items-center justify-center text-white font-bold text-sm shadow-xs flex-shrink-0">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-bold text-[#1C1C1E] truncate leading-tight">
                  {displayName}
                </p>
                <p className="text-xs text-[#6B7280] truncate mt-0.5">
                  {user?.email || 'user@dsfmp.go.ke'}
                </p>
                <div className="mt-1.5 flex items-center gap-1">
                  <span className="inline-flex items-center gap-1 text-[10px] font-semibold tracking-wide uppercase px-2 py-0.5 rounded-full bg-emerald-50 text-[#2E7D52] border border-emerald-200">
                    <ShieldCheck className="w-3 h-3" />
                    {roleLabel}
                  </span>
                </div>
              </div>
            </div>

            {/* Quick Links / Status */}
            <div className="py-2 text-xs text-[#6B7280] space-y-1">
              <div className="flex items-center justify-between text-[11px] py-1 px-1">
                <span>Session Expiry:</span>
                <span className="font-mono font-medium text-[#1C1C1E]">3 Hours</span>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="pt-2 border-t border-gray-100">
              <button
                onClick={handleLogout}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 text-xs font-bold text-red-600 bg-red-50/80 hover:bg-red-100 hover:text-red-700 rounded-lg transition-colors cursor-pointer active:scale-98"
              >
                <LogOut className="w-4 h-4" />
                <span>Log out</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </aside>
  );
}
