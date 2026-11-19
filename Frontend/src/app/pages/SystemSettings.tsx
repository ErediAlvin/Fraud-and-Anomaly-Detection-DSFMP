import { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import {
  Settings,
  Users,
  Shield,
  Database,
  Clock,
  FileText,
  Save,
  CheckCircle,
  AlertCircle,
  Plus,
  X,
  RefreshCw,
  Bell,
  Search,
} from 'lucide-react';
import { api } from '../lib/api';

const settingsNav = [
  { id: 'general', icon: Settings, label: 'General Settings' },
  { id: 'users', icon: Users, label: 'User Management' },
  { id: 'thresholds', icon: Shield, label: 'Risk Thresholds' },
  { id: 'alerts', icon: Bell, label: 'Alert Configuration' },
  { id: 'blockchain', icon: Database, label: 'Blockchain Configuration' },
  { id: 'schedule', icon: Clock, label: 'SOB / COB Schedule' },
  { id: 'audit', icon: FileText, label: 'Audit Log' },
];

interface UserItem {
  id: string;
  name: string;
  firstName?: string;
  lastName?: string;
  email: string;
  role: string;
  rawRole: string;
  county: string;
  status: string;
  isActive: boolean;
  phone: string;
  lastLogin: string;
  createdAt: string;
}

interface AuditLogItem {
  id: number;
  userName: string;
  userEmail: string;
  action: string;
  entityType: string;
  entityId: string;
  details: any;
  createdAt: string;
}

export function SystemSettings() {
  const [activeTab, setActiveTab] = useState('general');
  const [loading, setLoading] = useState(true);
  const [savingCategory, setSavingCategory] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Settings states
  const [general, setGeneral] = useState({
    system_name: 'DSFMP Fraud Detection Module',
    version: 'v2.1.4',
    environment: 'PRODUCTION',
    default_county: 'All Counties',
    session_timeout: 30,
    email_notifications: true,
    in_app_notifications: true,
    sms_notifications: false,
  });

  const [thresholds, setThresholds] = useState({
    model_threshold_if: 0.65,
    model_threshold_ae: 0.70,
    model_threshold_lstm: 0.69,
    model_threshold_gnn: 0.71,
    weight_if: 0.40,
    weight_ae: 0.30,
    weight_lstm: 0.30,
    weight_gnn: 0.00,
    threshold_critical: 0.80,
    threshold_high: 0.60,
    threshold_medium: 0.40,
    threshold_low: 0.40,
  });

  const [blockchain, setBlockchain] = useState({
    endpoint_url: 'https://blockchain.dsfmp.go.ke:7051',
    channel_name: 'dsfmp-channel',
    chaincode_name: 'fraud-detection-cc',
    sync_interval: 60,
    certificate_status: 'VALID',
    certificate_expiry: '2027-05-12',
  });

  const [schedule, setSchedule] = useState({
    sob_time: '06:00',
    cob_time: '18:00',
    enable_scheduled_sob: true,
    enable_scheduled_cob: true,
  });

  const [alerts, setAlerts] = useState({
    email_alerts: true,
    in_app_alerts: true,
    sms_critical_only: true,
    auto_assign: true,
    escalation_timeout_hours: 24,
  });

  // Users state & Modal
  const [users, setUsers] = useState<UserItem[]>([]);
  const [showAddUserModal, setShowAddUserModal] = useState(false);
  const [newUser, setNewUser] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: '',
    role: 'fraud_analyst',
    phone: '',
    county: 'All Counties',
  });
  const [userModalError, setUserModalError] = useState('');
  const [userModalLoading, setUserModalLoading] = useState(false);

  // Audit logs state
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditSearch, setAuditSearch] = useState('');

  // Load initial settings and users
  useEffect(() => {
    async function loadData() {
      try {
        setLoading(true);
        const [settingsRes, usersRes, auditRes] = await Promise.allSettled([
          api.get<any>('/settings'),
          api.get<UserItem[]>('/settings/users'),
          api.get<AuditLogItem[]>('/settings/audit-log'),
        ]);

        if (settingsRes.status === 'fulfilled' && settingsRes.value) {
          const val = settingsRes.value;
          if (val.general) setGeneral((prev) => ({ ...prev, ...val.general }));
          if (val.thresholds) setThresholds((prev) => ({ ...prev, ...val.thresholds }));
          if (val.blockchain) setBlockchain((prev) => ({ ...prev, ...val.blockchain }));
          if (val.schedule) setSchedule((prev) => ({ ...prev, ...val.schedule }));
          if (val.alerts) setAlerts((prev) => ({ ...prev, ...val.alerts }));
        }

        if (usersRes.status === 'fulfilled' && Array.isArray(usersRes.value)) {
          setUsers(usersRes.value);
        }

        if (auditRes.status === 'fulfilled' && Array.isArray(auditRes.value)) {
          setAuditLogs(auditRes.value);
        }
      } catch (err: any) {
        console.error('Failed to load settings:', err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  // Generic category save
  const handleSaveCategory = async (category: string, payload: any) => {
    try {
      setSavingCategory(category);
      setSaveMessage(null);
      await api.put(`/settings/${category}`, payload);
      setSaveMessage({ type: 'success', text: `${category.toUpperCase()} settings saved successfully!` });
      // Refresh audit logs
      const freshLogs = await api.get<AuditLogItem[]>('/settings/audit-log').catch(() => []);
      if (Array.isArray(freshLogs)) setAuditLogs(freshLogs);
    } catch (err: any) {
      setSaveMessage({ type: 'error', text: err.message || `Failed to save ${category} settings.` });
    } finally {
      setSavingCategory(null);
      setTimeout(() => setSaveMessage(null), 4000);
    }
  };

  // Add User handler
  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newUser.email || !newUser.password || !newUser.first_name || !newUser.last_name) {
      setUserModalError('Please fill in all required fields.');
      return;
    }

    try {
      setUserModalLoading(true);
      setUserModalError('');
      const res = await api.post<any>('/settings/users', newUser);
      if (res && res.user) {
        setUsers((prev) => [res.user, ...prev]);
      } else {
        const freshUsers = await api.get<UserItem[]>('/settings/users');
        setUsers(freshUsers);
      }
      setShowAddUserModal(false);
      setNewUser({
        email: '',
        password: '',
        first_name: '',
        last_name: '',
        role: 'fraud_analyst',
        phone: '',
        county: 'All Counties',
      });
      // Refresh audit log
      const freshLogs = await api.get<AuditLogItem[]>('/settings/audit-log').catch(() => []);
      if (Array.isArray(freshLogs)) setAuditLogs(freshLogs);
    } catch (err: any) {
      setUserModalError(err.message || 'Failed to create user.');
    } finally {
      setUserModalLoading(false);
    }
  };

  // Toggle User Status
  const handleToggleUserStatus = async (user: UserItem) => {
    const nextStatus = !user.isActive;
    try {
      await api.patch(`/settings/users/${user.id}`, { is_active: nextStatus });
      setUsers((prev) =>
        prev.map((u) =>
          u.id === user.id
            ? { ...u, isActive: nextStatus, status: nextStatus ? 'ACTIVE' : 'INACTIVE' }
            : u
        )
      );
      // Refresh audit logs
      const freshLogs = await api.get<AuditLogItem[]>('/settings/audit-log').catch(() => []);
      if (Array.isArray(freshLogs)) setAuditLogs(freshLogs);
    } catch (err: any) {
      alert(`Failed to update user status: ${err.message}`);
    }
  };

  // Change User Role
  const handleChangeRole = async (userId: string, newRole: string) => {
    try {
      await api.patch(`/settings/users/${userId}`, { role: newRole });
      setUsers((prev) =>
        prev.map((u) =>
          u.id === userId
            ? { ...u, role: newRole.replace('_', ' ').replace(/\b\w/g, (c) => c.toUpperCase()), rawRole: newRole }
            : u
        )
      );
      // Refresh audit logs
      const freshLogs = await api.get<AuditLogItem[]>('/settings/audit-log').catch(() => []);
      if (Array.isArray(freshLogs)) setAuditLogs(freshLogs);
    } catch (err: any) {
      alert(`Failed to update user role: ${err.message}`);
    }
  };

  // Filtered audit logs
  const filteredAudit = auditLogs.filter(
    (log) =>
      log.userName?.toLowerCase().includes(auditSearch.toLowerCase()) ||
      log.action?.toLowerCase().includes(auditSearch.toLowerCase()) ||
      log.entityType?.toLowerCase().includes(auditSearch.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['System Settings']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9]">
        <div className="flex h-full">
          {/* Left navigation */}
          <aside className="w-64 bg-white border-r border-[#DDE1E7] p-4 flex-shrink-0">
            <nav className="space-y-1">
              {settingsNav.map((item) => (
                <button
                  key={item.id}
                  onClick={() => {
                    setActiveTab(item.id);
                    setSaveMessage(null);
                  }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === item.id
                      ? 'bg-[#1A3C5E] text-white shadow-sm'
                      : 'text-[#6B7280] hover:bg-[#F4F6F9] hover:text-[#1F2937]'
                  }`}
                >
                  <item.icon className="w-4 h-4" />
                  {item.label}
                </button>
              ))}
            </nav>
          </aside>

          {/* Main content area */}
          <div className="flex-1 p-6 overflow-y-auto">
            {/* Notification alert banner */}
            {saveMessage && (
              <div
                className={`mb-6 p-4 rounded-lg flex items-center gap-3 border ${
                  saveMessage.type === 'success'
                    ? 'bg-[#E8F8F0] border-[#2E7D52] text-[#2E7D52]'
                    : 'bg-[#FDF2F2] border-[#C0392B] text-[#C0392B]'
                }`}
              >
                {saveMessage.type === 'success' ? (
                  <CheckCircle className="w-5 h-5 flex-shrink-0" />
                ) : (
                  <AlertCircle className="w-5 h-5 flex-shrink-0" />
                )}
                <span className="text-sm font-medium">{saveMessage.text}</span>
              </div>
            )}

            {/* ── 1. General Settings ── */}
            {activeTab === 'general' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <h2 className="font-bold text-xl mb-6 text-[#1A3C5E]">General System Settings</h2>

                <div className="space-y-6 max-w-2xl">
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-[#374151]">System Name</label>
                    <input
                      type="text"
                      value={general.system_name}
                      onChange={(e) => setGeneral({ ...general, system_name: e.target.value })}
                      className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold mb-2 text-[#374151]">Version</label>
                      <input
                        type="text"
                        value={general.version}
                        disabled
                        className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm bg-[#F9FAFB] text-[#6B7280]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold mb-2 text-[#374151]">Environment</label>
                      <select
                        value={general.environment}
                        onChange={(e) => setGeneral({ ...general, environment: e.target.value })}
                        className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                      >
                        <option value="PRODUCTION">PRODUCTION</option>
                        <option value="STAGING">STAGING</option>
                        <option value="DEVELOPMENT">DEVELOPMENT</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold mb-2 text-[#374151]">Default County Scope</label>
                    <select
                      value={general.default_county}
                      onChange={(e) => setGeneral({ ...general, default_county: e.target.value })}
                      className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                    >
                      <option value="All Counties">All Counties</option>
                      <option value="Nairobi">Nairobi</option>
                      <option value="Mombasa">Mombasa</option>
                      <option value="Kisumu">Kisumu</option>
                      <option value="Nakuru">Nakuru</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold mb-2 text-[#374151]">Session Timeout (minutes)</label>
                    <input
                      type="number"
                      value={general.session_timeout}
                      onChange={(e) => setGeneral({ ...general, session_timeout: parseInt(e.target.value) || 30 })}
                      className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-semibold mb-2 text-[#374151]">System Notifications</label>
                    <div className="space-y-2 bg-[#F9FAFB] p-3 rounded-lg border border-[#E5E7EB]">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={general.email_notifications}
                          onChange={(e) => setGeneral({ ...general, email_notifications: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <span className="text-sm text-[#374151]">Email notifications for urgent system events</span>
                      </label>
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={general.in_app_notifications}
                          onChange={(e) => setGeneral({ ...general, in_app_notifications: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <span className="text-sm text-[#374151]">In-app notification toast feed</span>
                      </label>
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={general.sms_notifications}
                          onChange={(e) => setGeneral({ ...general, sms_notifications: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <span className="text-sm text-[#374151]">SMS notifications for critical system alarms</span>
                      </label>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSaveCategory('general', general)}
                    disabled={savingCategory === 'general'}
                    className="bg-[#1A3C5E] text-white px-6 py-2.5 rounded-lg font-medium hover:bg-[#2E7D52] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {savingCategory === 'general' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save General Settings
                  </button>
                </div>
              </div>
            )}

            {/* ── 2. User Management ── */}
            {activeTab === 'users' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="font-bold text-xl text-[#1A3C5E]">User Management</h2>
                    <p className="text-xs text-[#6B7280] mt-1">Manage platform investigators, county officers, and supervisors</p>
                  </div>
                  <button
                    onClick={() => setShowAddUserModal(true)}
                    className="bg-[#1A3C5E] text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#2E7D52] transition-colors flex items-center gap-2 shadow-sm"
                  >
                    <Plus className="w-4 h-4" />
                    Add User
                  </button>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase w-12">#</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Name</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Role</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Status</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Last Login</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold text-[#6B7280] uppercase">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.length === 0 ? (
                        <tr>
                          <td colSpan={7} className="text-center py-6 text-sm text-[#6B7280]">
                            No user accounts found.
                          </td>
                        </tr>
                      ) : (
                        users.map((user, index) => (
                          <tr
                            key={user.id}
                            className={`border-b border-[#DDE1E7] hover:bg-[#F9FAFB] transition-colors ${
                              index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'
                            }`}
                          >
                            <td className="px-4 py-3 text-xs font-mono text-[#6B7280] font-medium">{index + 1}</td>
                            <td className="px-4 py-3 text-sm font-medium text-[#1F2937]">{user.name}</td>
                            <td className="px-4 py-3 text-sm text-[#4B5563]">{user.email}</td>
                            <td className="px-4 py-3 text-sm">
                              <select
                                value={user.rawRole || 'fraud_analyst'}
                                onChange={(e) => handleChangeRole(user.id, e.target.value)}
                                className="border border-[#DDE1E7] rounded px-2 py-1 text-xs bg-white focus:outline-none focus:border-[#1A3C5E]"
                              >
                                <option value="fraud_analyst">Fraud Analyst</option>
                                <option value="county_officer">County Officer</option>
                                <option value="system_admin">System Admin</option>
                                <option value="supervisor">Supervisor</option>
                                <option value="school_admin">School Admin</option>
                              </select>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                                  user.isActive
                                    ? 'bg-[#E8F8F0] text-[#2E7D52]'
                                    : 'bg-[#FDF2F2] text-[#C0392B]'
                                }`}
                              >
                                {user.isActive ? 'ACTIVE' : 'INACTIVE'}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-xs font-mono text-[#6B7280]">{user.lastLogin}</td>
                            <td className="px-4 py-3 text-right">
                              <button
                                onClick={() => handleToggleUserStatus(user)}
                                className={`text-xs font-medium px-2.5 py-1 rounded border transition-colors ${
                                  user.isActive
                                    ? 'border-[#C0392B] text-[#C0392B] hover:bg-[#FDF2F2]'
                                    : 'border-[#2E7D52] text-[#2E7D52] hover:bg-[#E8F8F0]'
                                }`}
                              >
                                {user.isActive ? 'Deactivate' : 'Activate'}
                              </button>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* ── 3. Risk Thresholds ── */}
            {activeTab === 'thresholds' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <h2 className="font-bold text-xl mb-6 text-[#1A3C5E]">Risk Thresholds & Model Sensitivities</h2>

                <div className="space-y-6 max-w-2xl">
                  <div>
                    <h3 className="font-bold text-sm mb-4 text-[#374151]">Model Anomaly Cut-off Thresholds</h3>
                    <div className="space-y-4 bg-[#F9FAFB] p-4 rounded-lg border border-[#E5E7EB]">
                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-sm font-medium text-[#374151]">Isolation Forest Threshold</label>
                          <span className="font-mono text-sm font-bold text-[#1A3C5E]">
                            {thresholds.model_threshold_if.toFixed(2)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={thresholds.model_threshold_if}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, model_threshold_if: parseFloat(e.target.value) })
                          }
                          className="w-full accent-[#1A3C5E]"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-sm font-medium text-[#374151]">Autoencoder Error Threshold</label>
                          <span className="font-mono text-sm font-bold text-[#1A3C5E]">
                            {thresholds.model_threshold_ae.toFixed(2)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={thresholds.model_threshold_ae}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, model_threshold_ae: parseFloat(e.target.value) })
                          }
                          className="w-full accent-[#1A3C5E]"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-sm font-medium text-[#374151]">LSTM Autoencoder Temporal Threshold</label>
                          <span className="font-mono text-sm font-bold text-[#1A3C5E]">
                            {thresholds.model_threshold_lstm.toFixed(2)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={thresholds.model_threshold_lstm}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, model_threshold_lstm: parseFloat(e.target.value) })
                          }
                          className="w-full accent-[#1A3C5E]"
                        />
                      </div>

                      <div>
                        <div className="flex items-center justify-between mb-1.5">
                          <label className="text-sm font-medium text-[#374151]">GNN Graph Collusion Threshold</label>
                          <span className="font-mono text-sm font-bold text-[#1A3C5E]">
                            {thresholds.model_threshold_gnn.toFixed(2)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.01"
                          value={thresholds.model_threshold_gnn}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, model_threshold_gnn: parseFloat(e.target.value) })
                          }
                          className="w-full accent-[#1A3C5E]"
                        />
                      </div>
                    </div>
                  </div>

                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <h3 className="font-bold text-sm text-[#374151]">Ensemble Model Scoring Weights</h3>
                        <p className="text-xs text-[#6B7280]">
                          Controls how each model contributes to the composite fraud risk score (recommended sum: 100%).
                        </p>
                      </div>
                      {(() => {
                        const weightSum =
                          (thresholds.weight_if || 0) +
                          (thresholds.weight_ae || 0) +
                          (thresholds.weight_lstm || 0);
                        const isBalanced = Math.abs(weightSum - 1.0) < 0.01;
                        return (
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-xs font-mono font-bold px-2.5 py-1 rounded ${
                                isBalanced
                                  ? 'bg-[#E8F8F0] text-[#2E7D52]'
                                  : 'bg-[#FEF9E7] text-[#B9770E]'
                              }`}
                            >
                              Total: {(weightSum * 100).toFixed(0)}%
                            </span>
                            <button
                              type="button"
                              onClick={() =>
                                setThresholds({
                                  ...thresholds,
                                  weight_if: 0.40,
                                  weight_ae: 0.30,
                                  weight_lstm: 0.30,
                                  weight_gnn: 0.00,
                                })
                              }
                              className="text-xs text-[#1A3C5E] hover:underline font-medium cursor-pointer"
                            >
                              Reset Defaults
                            </button>
                          </div>
                        );
                      })()}
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-[#F9FAFB] p-4 rounded-lg border border-[#E5E7EB]">
                      {[
                        { 
                          key: 'weight_if' as const, 
                          label: 'Isolation Forest Weight', 
                          badge: 'ACTIVE',
                          desc: 'Out-of-distribution tabular anomaly detection' 
                        },
                        { 
                          key: 'weight_ae' as const, 
                          label: 'Autoencoder (MLP) Weight', 
                          badge: 'ACTIVE',
                          desc: 'Reconstruction error on structured patterns' 
                        },
                        { 
                          key: 'weight_lstm' as const, 
                          label: 'LSTM Temporal Weight', 
                          badge: 'ACTIVE',
                          desc: 'Sequence drift across disbursement windows' 
                        },
                      ].map((item) => {
                        const activeSum = thresholds.weight_if + thresholds.weight_ae + thresholds.weight_lstm || 1;
                        const effectiveShare = item.badge === 'ACTIVE' 
                          ? ((thresholds[item.key] / activeSum) * 100).toFixed(1) 
                          : '0.0';
                        return (
                          <div key={item.key} className="bg-white p-3 rounded border border-[#E5E7EB]">
                            <div className="flex items-center justify-between mb-1">
                              <div className="flex items-center gap-1.5">
                                <span className="text-xs font-semibold text-[#1C1C1E]">{item.label}</span>
                                <span
                                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                    item.badge === 'ACTIVE'
                                      ? 'bg-green-100 text-green-800'
                                      : 'bg-gray-200 text-gray-600'
                                  }`}
                                >
                                  {item.badge}
                                </span>
                              </div>
                              <span className="text-xs font-mono font-bold text-[#1A3C5E]">
                                {(thresholds[item.key] * 100).toFixed(0)}% ({thresholds[item.key].toFixed(2)})
                              </span>
                            </div>
                            <p className="text-[11px] text-[#6B7280] mb-2">{item.desc}</p>
                            <input
                              type="range"
                              min="0"
                              max="1"
                              step="0.05"
                              value={thresholds[item.key]}
                              onChange={(e) =>
                                setThresholds({ ...thresholds, [item.key]: parseFloat(e.target.value) })
                              }
                              className="w-full accent-[#1A3C5E]"
                            />
                            <div className="flex items-center justify-between mt-1 text-[10px] text-[#6B7280] font-mono">
                              <span>Configured: {thresholds[item.key].toFixed(2)}</span>
                              <span>Active Share: {effectiveShare}%</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    
                    {/* Active Ensemble Formula Banner */}
                    <div className="mt-3 p-3 rounded-lg bg-[#F0F7FF] border border-[#BFDBFE] text-xs">
                      <div className="font-semibold text-[#1A3C5E] mb-1 flex items-center justify-between">
                        <span>Current 3-Model Active Ensemble Formula</span>
                        <span className="text-[11px] font-mono bg-white px-2 py-0.5 rounded border border-[#BFDBFE]">
                          Active Total: {((thresholds.weight_if + thresholds.weight_ae + thresholds.weight_lstm) * 100).toFixed(0)}%
                        </span>
                      </div>
                      <p className="font-mono text-[11px] text-[#1E3A8A]">
                        Composite Score = [({thresholds.weight_if.toFixed(2)} &times; IF) + ({thresholds.weight_ae.toFixed(2)} &times; AE) + ({thresholds.weight_lstm.toFixed(2)} &times; LSTM)] &divide; {(thresholds.weight_if + thresholds.weight_ae + thresholds.weight_lstm).toFixed(2)}
                      </p>
                      <p className="text-[10px] text-[#475569] mt-1">
                        Effective active weights: Isolation Forest ({((thresholds.weight_if / (thresholds.weight_if + thresholds.weight_ae + thresholds.weight_lstm)) * 100).toFixed(1)}%) + Autoencoder ({((thresholds.weight_ae / (thresholds.weight_if + thresholds.weight_ae + thresholds.weight_lstm)) * 100).toFixed(1)}%) + LSTM Autoencoder ({((thresholds.weight_lstm / (thresholds.weight_if + thresholds.weight_ae + thresholds.weight_lstm)) * 100).toFixed(1)}%).
                      </p>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-sm mb-4 text-[#374151]">Composite Score Tier Boundaries</h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-[#FDF2F2] p-3 rounded-lg border border-[#F5C6CB]">
                        <label className="block text-xs font-bold mb-1 text-[#C0392B]">CRITICAL TIER (Score ≥)</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={thresholds.threshold_critical}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, threshold_critical: parseFloat(e.target.value) || 0.8 })
                          }
                          className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-white font-mono"
                        />
                        <p className="text-[11px] text-[#C0392B] mt-1">Automatic suspension & county escalation</p>
                      </div>

                      <div className="bg-[#FEF9E7] p-3 rounded-lg border border-[#FCEEC5]">
                        <label className="block text-xs font-bold mb-1 text-[#E8A020]">HIGH TIER (Score ≥)</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={thresholds.threshold_high}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, threshold_high: parseFloat(e.target.value) || 0.6 })
                          }
                          className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-white font-mono"
                        />
                        <p className="text-[11px] text-[#E8A020] mt-1">Flag for senior review & freeze payments</p>
                      </div>

                      <div className="bg-[#EBF5FB] p-3 rounded-lg border border-[#D4E6F1]">
                        <label className="block text-xs font-bold mb-1 text-[#2471A3]">MEDIUM TIER (Score ≥)</label>
                        <input
                          type="number"
                          step="0.01"
                          min="0"
                          max="1"
                          value={thresholds.threshold_medium}
                          onChange={(e) =>
                            setThresholds({ ...thresholds, threshold_medium: parseFloat(e.target.value) || 0.4 })
                          }
                          className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-white font-mono"
                        />
                        <p className="text-[11px] text-[#2471A3] mt-1">Queue for investigator monitoring</p>
                      </div>

                      <div className="bg-[#E8F8F0] p-3 rounded-lg border border-[#C3E6CB]">
                        <label className="block text-xs font-bold mb-1 text-[#2E7D52]">LOW TIER (Score &lt;)</label>
                        <input
                          type="number"
                          step="0.01"
                          value={thresholds.threshold_medium}
                          disabled
                          className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-[#F9FAFB] text-[#6B7280] font-mono"
                        />
                        <p className="text-[11px] text-[#2E7D52] mt-1">Logged and monitored automatically</p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSaveCategory('thresholds', thresholds)}
                    disabled={savingCategory === 'thresholds'}
                    className="bg-[#1A3C5E] text-white px-6 py-2.5 rounded-lg font-medium hover:bg-[#2E7D52] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {savingCategory === 'thresholds' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Thresholds &amp; Weights
                  </button>
                </div>
              </div>
            )}

            {/* ── 4. Alert Configuration ── */}
            {activeTab === 'alerts' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <h2 className="font-bold text-xl mb-6 text-[#1A3C5E]">Alert & Workflow Configuration</h2>

                <div className="space-y-6 max-w-2xl">
                  <div>
                    <h3 className="font-bold text-sm mb-3 text-[#374151]">Dispatch Channels</h3>
                    <div className="space-y-3 bg-[#F9FAFB] p-4 rounded-lg border border-[#E5E7EB]">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={alerts.email_alerts}
                          onChange={(e) => setAlerts({ ...alerts, email_alerts: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <div>
                          <span className="text-sm font-medium text-[#374151]">Email Dispatch</span>
                          <p className="text-xs text-[#6B7280]">Dispatch instant email notifications when CRITICAL alerts occur</p>
                        </div>
                      </label>

                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={alerts.in_app_alerts}
                          onChange={(e) => setAlerts({ ...alerts, in_app_alerts: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <div>
                          <span className="text-sm font-medium text-[#374151]">Real-Time In-App Banners</span>
                          <p className="text-xs text-[#6B7280]">Display live top bar banner notifications on active dashboards</p>
                        </div>
                      </label>

                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={alerts.sms_critical_only}
                          onChange={(e) => setAlerts({ ...alerts, sms_critical_only: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <div>
                          <span className="text-sm font-medium text-[#374151]">SMS Gateway (Emergency Escalation Only)</span>
                          <p className="text-xs text-[#6B7280]">Send SMS notifications only to County Directors for Critical incidents</p>
                        </div>
                      </label>
                    </div>
                  </div>

                  <div>
                    <h3 className="font-bold text-sm mb-3 text-[#374151]">Case Routing Automation</h3>
                    <div className="space-y-4">
                      <label className="flex items-center gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={alerts.auto_assign}
                          onChange={(e) => setAlerts({ ...alerts, auto_assign: e.target.checked })}
                          className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                        />
                        <div>
                          <span className="text-sm font-medium text-[#374151]">Auto-Assign Alerts to Investigators</span>
                          <p className="text-xs text-[#6B7280]">Distribute incoming alerts round-robin among active Fraud Analysts</p>
                        </div>
                      </label>

                      <div>
                        <label className="block text-sm font-semibold mb-1.5 text-[#374151]">
                          SLA Escalation Timeout (Hours)
                        </label>
                        <input
                          type="number"
                          value={alerts.escalation_timeout_hours}
                          onChange={(e) =>
                            setAlerts({ ...alerts, escalation_timeout_hours: parseInt(e.target.value) || 24 })
                          }
                          className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                        />
                        <p className="text-xs text-[#6B7280] mt-1">
                          Cases without investigator activity after this timeframe are automatically flagged Amber/Red.
                        </p>
                      </div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleSaveCategory('alerts', alerts)}
                    disabled={savingCategory === 'alerts'}
                    className="bg-[#1A3C5E] text-white px-6 py-2.5 rounded-lg font-medium hover:bg-[#2E7D52] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {savingCategory === 'alerts' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Alert Configuration
                  </button>
                </div>
              </div>
            )}

            {/* ── 5. Blockchain Configuration ── */}
            {activeTab === 'blockchain' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <h2 className="font-bold text-xl mb-6 text-[#1A3C5E]">Blockchain Ledger Configuration</h2>

                <div className="space-y-6 max-w-2xl">
                  <div>
                    <label className="block text-sm font-semibold mb-2 text-[#374151]">
                      Hyperledger Fabric Peer Endpoint URL
                    </label>
                    <input
                      type="text"
                      value={blockchain.endpoint_url}
                      onChange={(e) => setBlockchain({ ...blockchain, endpoint_url: e.target.value })}
                      className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 font-mono text-sm focus:outline-none focus:border-[#1A3C5E]"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-semibold mb-2 text-[#374151]">Channel Name</label>
                      <input
                        type="text"
                        value={blockchain.channel_name}
                        onChange={(e) => setBlockchain({ ...blockchain, channel_name: e.target.value })}
                        className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold mb-2 text-[#374151]">Chaincode Name</label>
                      <input
                        type="text"
                        value={blockchain.chaincode_name}
                        onChange={(e) => setBlockchain({ ...blockchain, chaincode_name: e.target.value })}
                        className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-semibold mb-2 text-[#374151]">Sync Interval (seconds)</label>
                    <input
                      type="number"
                      value={blockchain.sync_interval}
                      onChange={(e) => setBlockchain({ ...blockchain, sync_interval: parseInt(e.target.value) || 60 })}
                      className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                    />
                  </div>

                  <div className="bg-[#F9FAFB] rounded-lg p-4 border border-[#E5E7EB]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-[#374151]">MSP Certificate Status</span>
                      <span className="flex items-center gap-2">
                        <span className="w-2.5 h-2.5 bg-[#2E7D52] rounded-full"></span>
                        <span className="text-sm font-bold text-[#2E7D52]">{blockchain.certificate_status}</span>
                      </span>
                    </div>
                    <p className="text-xs text-[#6B7280]">Certificate expires: {blockchain.certificate_expiry}</p>
                  </div>

                  <div className="flex gap-3">
                    <button
                      onClick={() => handleSaveCategory('blockchain', blockchain)}
                      disabled={savingCategory === 'blockchain'}
                      className="bg-[#1A3C5E] text-white px-6 py-2.5 rounded-lg font-medium hover:bg-[#2E7D52] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                    >
                      {savingCategory === 'blockchain' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                      Save Configuration
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* ── 6. SOB/COB Schedule ── */}
            {activeTab === 'schedule' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <h2 className="font-bold text-xl mb-6 text-[#1A3C5E]">SOB / COB Automated Run Schedule</h2>

                <div className="space-y-6 max-w-2xl">
                  <div className="grid grid-cols-2 gap-6">
                    <div>
                      <label className="block text-sm font-semibold mb-2 text-[#374151]">
                        Start-of-Business (SOB) Time
                      </label>
                      <input
                        type="time"
                        value={schedule.sob_time}
                        onChange={(e) => setSchedule({ ...schedule, sob_time: e.target.value })}
                        className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-semibold mb-2 text-[#374151]">
                        Close-of-Business (COB) Time
                      </label>
                      <input
                        type="time"
                        value={schedule.cob_time}
                        onChange={(e) => setSchedule({ ...schedule, cob_time: e.target.value })}
                        className="w-full border border-[#DDE1E7] rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-[#1A3C5E]"
                      />
                    </div>
                  </div>

                  <div className="space-y-3 bg-[#F9FAFB] p-4 rounded-lg border border-[#E5E7EB]">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={schedule.enable_scheduled_sob}
                        onChange={(e) => setSchedule({ ...schedule, enable_scheduled_sob: e.target.checked })}
                        className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                      />
                      <div>
                        <span className="text-sm font-medium text-[#374151]">Enable Automated SOB Overnight Batch</span>
                        <p className="text-xs text-[#6B7280]">Performs nightly database sync, risk score caching, and daily stats reset</p>
                      </div>
                    </label>
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={schedule.enable_scheduled_cob}
                        onChange={(e) => setSchedule({ ...schedule, enable_scheduled_cob: e.target.checked })}
                        className="rounded text-[#1A3C5E] focus:ring-[#1A3C5E]"
                      />
                      <div>
                        <span className="text-sm font-medium text-[#374151]">Enable Automated COB Evening Sweep</span>
                        <p className="text-xs text-[#6B7280]">Flushes daily event logs, evaluates drift checks, and archives daily summaries</p>
                      </div>
                    </label>
                  </div>

                  <button
                    onClick={() => handleSaveCategory('schedule', schedule)}
                    disabled={savingCategory === 'schedule'}
                    className="bg-[#1A3C5E] text-white px-6 py-2.5 rounded-lg font-medium hover:bg-[#2E7D52] transition-colors flex items-center gap-2 shadow-sm disabled:opacity-50"
                  >
                    {savingCategory === 'schedule' ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Schedule
                  </button>
                </div>
              </div>
            )}

            {/* ── 7. Audit Log ── */}
            {activeTab === 'audit' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h2 className="font-bold text-xl text-[#1A3C5E]">System Audit Trail</h2>
                    <p className="text-xs text-[#6B7280] mt-1">Immutable administrative action logs and setting change records</p>
                  </div>
                  <div className="relative w-64">
                    <Search className="w-4 h-4 text-[#9CA3AF] absolute left-3 top-2.5" />
                    <input
                      type="text"
                      placeholder="Search action or user..."
                      value={auditSearch}
                      onChange={(e) => setAuditSearch(e.target.value)}
                      className="w-full pl-9 pr-4 py-1.5 text-xs border border-[#DDE1E7] rounded-lg focus:outline-none focus:border-[#1A3C5E]"
                    />
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Timestamp</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Actor</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Action</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Entity</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Details</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredAudit.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="text-center py-6 text-sm text-[#6B7280]">
                            No audit log entries recorded yet.
                          </td>
                        </tr>
                      ) : (
                        filteredAudit.map((log) => (
                          <tr key={log.id} className="border-b border-[#DDE1E7] hover:bg-[#F9FAFB] text-xs">
                            <td className="px-4 py-3 font-mono text-[#4B5563] whitespace-nowrap">{log.createdAt}</td>
                            <td className="px-4 py-3 font-medium text-[#1F2937]">
                              <div>{log.userName}</div>
                              <div className="text-[11px] text-[#6B7280]">{log.userEmail}</div>
                            </td>
                            <td className="px-4 py-3">
                              <span className="inline-flex px-2 py-0.5 rounded text-[11px] font-semibold bg-[#EBF5FB] text-[#1A3C5E]">
                                {log.action}
                              </span>
                            </td>
                            <td className="px-4 py-3 text-[#4B5563]">
                              {log.entityType} {log.entityId !== 'N/A' && `(${log.entityId})`}
                            </td>
                            <td className="px-4 py-3 font-mono text-[#4B5563] max-w-xs truncate" title={typeof log.details === 'object' ? JSON.stringify(log.details) : log.details}>
                              {typeof log.details === 'object' ? JSON.stringify(log.details) : log.details || '—'}
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* ── Add User Modal ── */}
      {showAddUserModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-xl border border-[#DDE1E7] w-full max-w-md overflow-hidden animate-in fade-in zoom-in duration-150">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#DDE1E7] bg-[#F8FAFC]">
              <h3 className="font-bold text-[#1A3C5E]">Create Platform User</h3>
              <button
                onClick={() => setShowAddUserModal(false)}
                className="text-[#6B7280] hover:text-[#1F2937]"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddUser} className="p-6 space-y-4">
              {userModalError && (
                <div className="p-3 bg-[#FDF2F2] border border-[#F5C6CB] text-[#C0392B] rounded text-xs font-medium">
                  {userModalError}
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1">First Name *</label>
                  <input
                    type="text"
                    required
                    value={newUser.first_name}
                    onChange={(e) => setNewUser({ ...newUser, first_name: e.target.value })}
                    className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[#1A3C5E]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1">Last Name *</label>
                  <input
                    type="text"
                    required
                    value={newUser.last_name}
                    onChange={(e) => setNewUser({ ...newUser, last_name: e.target.value })}
                    className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[#1A3C5E]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#374151] mb-1">Email Address *</label>
                <input
                  type="email"
                  required
                  value={newUser.email}
                  onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                  className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[#1A3C5E]"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[#374151] mb-1">Initial Password *</label>
                <input
                  type="password"
                  required
                  value={newUser.password}
                  onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                  placeholder="Min 8 characters"
                  className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[#1A3C5E]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1">Role *</label>
                  <select
                    value={newUser.role}
                    onChange={(e) => setNewUser({ ...newUser, role: e.target.value })}
                    className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[#1A3C5E]"
                  >
                    <option value="fraud_analyst">Fraud Analyst</option>
                    <option value="county_officer">County Officer</option>
                    <option value="system_admin">System Admin</option>
                    <option value="supervisor">Supervisor</option>
                    <option value="school_admin">School Admin</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-[#374151] mb-1">Phone (Optional)</label>
                  <input
                    type="text"
                    value={newUser.phone}
                    onChange={(e) => setNewUser({ ...newUser, phone: e.target.value })}
                    placeholder="+254..."
                    className="w-full border border-[#DDE1E7] rounded px-3 py-1.5 text-xs focus:outline-none focus:border-[#1A3C5E]"
                  />
                </div>
              </div>

              <div className="pt-4 flex justify-end gap-2 border-t border-[#DDE1E7]">
                <button
                  type="button"
                  onClick={() => setShowAddUserModal(false)}
                  className="px-4 py-2 border border-[#DDE1E7] rounded text-xs font-medium text-[#6B7280] hover:bg-[#F4F6F9]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={userModalLoading}
                  className="px-5 py-2 bg-[#1A3C5E] text-white rounded text-xs font-medium hover:bg-[#2E7D52] transition-colors disabled:opacity-50 flex items-center gap-1.5"
                >
                  {userModalLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                  Create Account
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
