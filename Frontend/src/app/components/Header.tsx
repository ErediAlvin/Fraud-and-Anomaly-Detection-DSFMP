import { useState, useEffect, useRef, useCallback } from 'react';
import { Bell, X, CheckCheck, Briefcase, ShieldAlert, Info, ExternalLink } from 'lucide-react';
import { useNavigate } from 'react-router';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';

interface HeaderProps {
  breadcrumbs?: string[];
}

interface InAppNotification {
  id: string;
  userId: string;
  type: string;
  title: string;
  message: string;
  link?: string | null;
  isRead: boolean;
  createdAt: string;
  recipientName: string;
  recipientEmail: string;
}

export function Header({ breadcrumbs = ['Dashboard'] }: HeaderProps) {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<InAppNotification[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = useCallback(async () => {
    if (!user?.id) {
      setNotifications([]);
      setUnreadCount(0);
      return;
    }
    try {
      setLoading(true);
      const res = await api.get<{ notifications: InAppNotification[]; unread_count: number }>(
        `/notifications?user_id=${encodeURIComponent(user.id)}`
      );
      if (res && Array.isArray(res.notifications)) {
        // Filter strictly to the authenticated user's notifications
        const userNotifs = res.notifications.filter((n) => !n.userId || n.userId === user.id);
        setNotifications(userNotifs);
        setUnreadCount(
          typeof res.unread_count === 'number'
            ? res.unread_count
            : userNotifs.filter((n) => !n.isRead).length
        );
      }
    } catch (e) {
      // Graceful fallback
    } finally {
      setLoading(false);
    }
  }, [user?.id]);

  useEffect(() => {
    fetchNotifications();

    // Listen for custom trigger when case assignments or actions occur
    const handleRefresh = () => {
      fetchNotifications();
    };

    window.addEventListener('dsfmp_notification_refresh', handleRefresh);
    const interval = setInterval(fetchNotifications, 30000);

    return () => {
      window.removeEventListener('dsfmp_notification_refresh', handleRefresh);
      clearInterval(interval);
    };
  }, [fetchNotifications]);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleMarkAllRead = async () => {
    if (!user?.id) return;
    try {
      await api.patch(`/notifications/mark-read?user_id=${encodeURIComponent(user.id)}`);
      setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
      setUnreadCount(0);
    } catch (e) {
      console.warn('Failed to mark all notifications read:', e);
    }
  };

  const handleItemClick = async (notif: InAppNotification) => {
    if (!notif.isRead) {
      try {
        const query = user?.id ? `?user_id=${encodeURIComponent(user.id)}` : '';
        await api.patch(`/notifications/${notif.id}/read${query}`);
        setNotifications((prev) =>
          prev.map((n) => (n.id === notif.id ? { ...n, isRead: true } : n))
        );
        setUnreadCount((c) => Math.max(0, c - 1));
      } catch (e) {
        // ignore
      }
    }
    if (notif.link) {
      setIsOpen(false);
      navigate(notif.link);
    }
  };

  const getIcon = (type: string) => {
    switch (type) {
      case 'CASE_UPDATE':
        return <Briefcase className="w-4 h-4 text-[#1A3C5E]" />;
      case 'ALERT':
        return <ShieldAlert className="w-4 h-4 text-[#C0392B]" />;
      default:
        return <Info className="w-4 h-4 text-[#2E7D52]" />;
    }
  };

  return (
    <header className="bg-white border-b border-[#DDE1E7] px-6 py-4 relative z-30">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-[#6B7280]">
          {breadcrumbs.map((crumb, index) => (
            <span key={index}>
              {index > 0 && <span className="mx-2">/</span>}
              <span className={index === breadcrumbs.length - 1 ? 'text-[#1C1C1E] font-medium' : ''}>
                {crumb}
              </span>
            </span>
          ))}
        </div>

        <div className="flex items-center gap-4 relative" ref={dropdownRef}>
          <button
            onClick={() => setIsOpen(!isOpen)}
            className="relative p-2 hover:bg-[#F4F6F9] rounded-lg transition-colors cursor-pointer"
            title="Notifications"
            aria-label="View notifications"
          >
            <Bell className="w-5 h-5 text-[#6B7280]" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 min-w-[18px] h-[18px] px-1 bg-[#C0392B] text-white text-[10px] font-bold rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Drawer */}
          {isOpen && (
            <div className="absolute right-0 top-12 w-96 bg-white rounded-xl shadow-2xl border border-[#DDE1E7] overflow-hidden animate-in fade-in zoom-in-95 duration-150 z-50">
              <div className="p-4 bg-[#F8FAFC] border-b border-[#DDE1E7] flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="font-bold text-sm text-[#1C1C1E]">My Notifications</h3>
                    {unreadCount > 0 && (
                      <span className="text-[10px] font-bold bg-[#C0392B] text-white px-1.5 py-0.5 rounded-full">
                        {unreadCount} new
                      </span>
                    )}
                  </div>
                  {user && (
                    <p className="text-[11px] text-[#6B7280] mt-0.5 truncate">
                      {user.firstName} {user.lastName} ({user.email})
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={handleMarkAllRead}
                      className="text-[11px] font-semibold text-[#1A3C5E] hover:underline flex items-center gap-1 cursor-pointer"
                    >
                      <CheckCheck className="w-3.5 h-3.5" />
                      Mark all read
                    </button>
                  )}
                  <button
                    onClick={() => setIsOpen(false)}
                    className="p-1 hover:bg-gray-200 rounded text-[#6B7280] cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="max-h-[380px] overflow-y-auto divide-y divide-gray-100">
                {loading && notifications.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[#6B7280]">Loading your notifications...</div>
                ) : notifications.length === 0 ? (
                  <div className="p-8 text-center text-xs text-[#6B7280]">No notifications for your account.</div>
                ) : (
                  notifications.map((n) => (
                    <div
                      key={n.id}
                      onClick={() => handleItemClick(n)}
                      className={`p-3.5 transition-colors cursor-pointer hover:bg-[#F9FAFB] flex gap-3 ${
                        !n.isRead ? 'bg-[#F0F7FF]/50' : 'bg-white'
                      }`}
                    >
                      <div className="mt-0.5 p-1.5 rounded-lg bg-gray-100 h-fit">
                        {getIcon(n.type)}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-1 mb-0.5">
                          <p className={`text-xs font-semibold truncate ${!n.isRead ? 'text-[#1A3C5E]' : 'text-[#374151]'}`}>
                            {n.title}
                          </p>
                          {!n.isRead && (
                            <span className="w-2 h-2 rounded-full bg-[#1A3C5E] shrink-0 mt-1" />
                          )}
                        </div>
                        <p className="text-[11px] text-[#4B5563] line-clamp-2 mb-1.5 leading-relaxed">
                          {n.message}
                        </p>
                        <div className="flex items-center justify-between text-[10px] text-[#9CA3AF] font-mono">
                          <span className="bg-gray-100 px-1.5 py-0.5 rounded text-gray-700">
                            {n.type.replace(/_/g, ' ')}
                          </span>
                          <span>{n.createdAt}</span>
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>

              <div className="p-2.5 bg-[#F8FAFC] border-t border-[#DDE1E7] text-center">
                <button
                  onClick={() => {
                    setIsOpen(false);
                    navigate('/cases');
                  }}
                  className="text-xs font-semibold text-[#1A3C5E] hover:underline flex items-center justify-center gap-1 w-full py-1 cursor-pointer"
                >
                  <span>Go to Case Management</span>
                  <ExternalLink className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
