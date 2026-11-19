import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Header } from '../components/Header';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';
import { 
  X, 
  ExternalLink, 
  ShieldAlert, 
  CheckCircle2, 
  AlertTriangle, 
  ArrowRight, 
  Loader2, 
  UserCheck, 
  FileWarning, 
  Check, 
  RotateCcw
} from 'lucide-react';
import { api } from '../lib/api';

interface Alert {
  id: string;
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  entityType: string;
  entityName: string;
  alertType: string;
  compositeScore: number;
  modelScores: {
    IF: number;
    AE: number;
    LSTM: number;
    GNN?: number;
  };
  triggeredAt: string;
  status: string;
  assignedTo: string;
  evidence: Array<{ feature: string; expected: string; actual: string }>;
  blockchainHash: string;
  description: string;
  title?: string;
}

interface ActionToast {
  type: 'success' | 'error' | 'info';
  message: string;
  caseRef?: string;
  caseId?: string;
}

export function FraudAlerts() {
  const navigate = useNavigate();
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    tier: 'ALL',
    status: 'ALL',
    alertType: 'ALL',
  });
  const [search, setSearch] = useState('');

  // Action states
  const [actionLoadingId, setActionLoadingId] = useState<string | null>(null);
  const [toast, setToast] = useState<ActionToast | null>(null);

  // Dismiss Modal State
  const [dismissModalOpen, setDismissModalOpen] = useState(false);
  const [dismissTarget, setDismissTarget] = useState<Alert | null>(null);
  const [dismissReason, setDismissReason] = useState<string>('FALSE_POSITIVE');
  const [dismissNotes, setDismissNotes] = useState<string>('');
  const [dismissing, setDismissing] = useState(false);

  // Escalate Modal State
  const [escalateModalOpen, setEscalateModalOpen] = useState(false);
  const [escalateTarget, setEscalateTarget] = useState<Alert | null>(null);
  const [escalateTitle, setEscalateTitle] = useState<string>('');
  const [escalatePriority, setEscalatePriority] = useState<string>('HIGH');
  const [escalateNotes, setEscalateNotes] = useState<string>('');
  const [escalating, setEscalating] = useState(false);

  // Auto-dismiss toast after 6 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => setToast(null), 6000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  // Load Alerts
  useEffect(() => {
    let isMounted = true;
    async function loadAlerts() {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.tier !== 'ALL') params.append('tier', filters.tier);
        if (filters.status !== 'ALL') params.append('status', filters.status);
        if (filters.alertType !== 'ALL') params.append('alert_type', filters.alertType);
        if (search) params.append('search', search);

        const data = await api.get<Alert[]>(`/alerts?${params.toString()}`);
        if (isMounted) {
          setAlerts(data);
          setError('');
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load alerts.');
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(() => {
      loadAlerts();
    }, 300);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [filters, search]);

  // ── Handler: Acknowledge Alert ─────────────────────────────────────────────
  const handleAcknowledge = async (alert: Alert) => {
    try {
      setActionLoadingId(alert.id);
      const res = await api.post<{
        success: boolean;
        alert_id: string;
        status: string;
        message: string;
        assigned_to?: string;
      }>(`/alerts/${alert.id}/acknowledge`, {});

      // Update state in memory
      setAlerts((prev) =>
        prev.map((a) =>
          a.id === alert.id
            ? { ...a, status: res.status, assignedTo: res.assigned_to || 'You' }
            : a
        )
      );
      if (selectedAlert?.id === alert.id) {
        setSelectedAlert((prev) =>
          prev ? { ...prev, status: res.status, assignedTo: res.assigned_to || 'You' } : null
        );
      }

      setToast({
        type: 'success',
        message: res.message || 'Alert acknowledged and assigned for investigation.',
      });
    } catch (err: any) {
      setToast({
        type: 'error',
        message: err.message || 'Failed to acknowledge alert.',
      });
    } finally {
      setActionLoadingId(null);
    }
  };

  // ── Handler: Open Dismiss Modal ────────────────────────────────────────────
  const openDismissModal = (alert: Alert) => {
    setDismissTarget(alert);
    setDismissReason('FALSE_POSITIVE');
    setDismissNotes('');
    setDismissModalOpen(true);
  };

  // ── Handler: Submit Dismissal ──────────────────────────────────────────────
  const handleConfirmDismiss = async () => {
    if (!dismissTarget) return;
    try {
      setDismissing(true);
      const res = await api.post<{
        success: boolean;
        alert_id: string;
        status: string;
        message: string;
      }>(`/alerts/${dismissTarget.id}/dismiss`, {
        reason_code: dismissReason,
        notes: dismissNotes,
      });

      setAlerts((prev) =>
        prev.map((a) =>
          a.id === dismissTarget.id ? { ...a, status: 'DISMISSED' } : a
        )
      );
      if (selectedAlert?.id === dismissTarget.id) {
        setSelectedAlert((prev) => (prev ? { ...prev, status: 'DISMISSED' } : null));
      }

      setDismissModalOpen(false);
      setToast({
        type: 'success',
        message: res.message || `Alert marked as dismissed (${dismissReason}). Ground-truth recorded.`,
      });
    } catch (err: any) {
      setToast({
        type: 'error',
        message: err.message || 'Failed to dismiss alert.',
      });
    } finally {
      setDismissing(false);
    }
  };

  // ── Handler: Open Escalate Modal ───────────────────────────────────────────
  const openEscalateModal = (alert: Alert) => {
    setEscalateTarget(alert);
    setEscalateTitle(alert.title ? `Investigation: ${alert.title}` : `Investigation: ${alert.alertType} - ${alert.entityName}`);
    setEscalatePriority(alert.tier || 'HIGH');
    setEscalateNotes('');
    setEscalateModalOpen(true);
  };

  // ── Handler: Submit Escalation ─────────────────────────────────────────────
  const handleConfirmEscalate = async () => {
    if (!escalateTarget) return;
    try {
      setEscalating(true);
      const res = await api.post<{
        success: boolean;
        alert_id: string;
        status: string;
        message: string;
        case_id: string;
        case_ref: string;
      }>(`/alerts/${escalateTarget.id}/escalate`, {
        case_title: escalateTitle,
        priority: escalatePriority,
        notes: escalateNotes,
      });

      setAlerts((prev) =>
        prev.map((a) =>
          a.id === escalateTarget.id ? { ...a, status: 'ESCALATED' } : a
        )
      );
      if (selectedAlert?.id === escalateTarget.id) {
        setSelectedAlert((prev) => (prev ? { ...prev, status: 'ESCALATED' } : null));
      }

      setEscalateModalOpen(false);
      setToast({
        type: 'success',
        message: `Alert escalated to formal case ${res.case_ref}.`,
        caseRef: res.case_ref,
        caseId: res.case_id,
      });
    } catch (err: any) {
      setToast({
        type: 'error',
        message: err.message || 'Failed to escalate alert into a case.',
      });
    } finally {
      setEscalating(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative">
      <Header breadcrumbs={['Fraud Alerts']} />

      {/* Floating Action Toast Banner */}
      {toast && (
        <div className="absolute top-16 right-6 z-50 max-w-md w-full animate-in fade-in slide-in-from-top-4 duration-300">
          <div
            className={`p-4 rounded-xl border shadow-lg flex items-start gap-3 ${
              toast.type === 'success'
                ? 'bg-[#E8F8F0] border-[#C3E6CB] text-[#2E7D52]'
                : toast.type === 'error'
                ? 'bg-[#FDF2F2] border-[#F5C6CB] text-[#C0392B]'
                : 'bg-[#F0F7FF] border-[#BFDBFE] text-[#1A3C5E]'
            }`}
          >
            {toast.type === 'success' ? (
              <CheckCircle2 className="w-5 h-5 shrink-0 mt-0.5 text-[#2E7D52]" />
            ) : (
              <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-[#C0392B]" />
            )}
            <div className="flex-1 text-xs">
              <p className="font-bold">{toast.message}</p>
              {toast.caseRef && (
                <div className="mt-2 flex items-center gap-2">
                  <button
                    onClick={() => navigate('/cases')}
                    className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#1A3C5E] text-white font-medium rounded hover:bg-[#2471A3] transition-colors"
                  >
                    <span>View in Case Management</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              )}
            </div>
            <button
              onClick={() => setToast(null)}
              className="text-gray-400 hover:text-gray-600 p-1"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Filters bar */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-4 mb-6 shadow-sm">
          <div className="flex flex-wrap items-center gap-4">
            <div>
              <label className="block text-xs font-semibold text-[#6B7280] mb-1">Risk Tier</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-white"
                value={filters.tier}
                onChange={(e) => setFilters({ ...filters, tier: e.target.value })}
              >
                <option value="ALL">All Tiers</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#6B7280] mb-1">Status</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-white"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="ALL">All Statuses</option>
                <option value="NEW">NEW</option>
                <option value="UNDER_REVIEW">UNDER REVIEW</option>
                <option value="INVESTIGATING">INVESTIGATING</option>
                <option value="ESCALATED">ESCALATED</option>
                <option value="DISMISSED">DISMISSED</option>
                <option value="RESOLVED">RESOLVED</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#6B7280] mb-1">Alert Type</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm bg-white"
                value={filters.alertType}
                onChange={(e) => setFilters({ ...filters, alertType: e.target.value })}
              >
                <option value="ALL">All Typologies</option>
                <option value="GHOST_BENEFICIARY">Ghost Beneficiary</option>
                <option value="PAYMENT_ANOMALY">Payment Anomaly</option>
                <option value="SUPPLY_CHAIN_IRREGULARITY">Supply Chain</option>
                <option value="ENROLLMENT_SPIKE">Enrollment Spike</option>
                <option value="OFF_HOURS_TRANSACTION">Off-Hours Payment</option>
                <option value="OTHER">Other / Statistical Outlier</option>
              </select>
            </div>

            <div className="flex-1"></div>

            <div className="self-end">
              <label className="block text-xs font-semibold text-[#6B7280] mb-1">Search</label>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search alert title, ID, entity..."
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm w-72"
              />
            </div>
          </div>
        </div>

        {/* Summary Metric Strip */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-3 mb-6 flex flex-wrap items-center justify-between gap-4 shadow-sm">
          <div className="flex items-center gap-6">
            <span className="text-sm text-[#6B7280]">
              Total Displayed: <span className="font-bold text-[#1C1C1E]">{alerts.length}</span> alerts
            </span>
            <div className="flex items-center gap-4">
              <span className="text-xs flex items-center">
                <RiskBadge tier="CRITICAL" className="mr-1.5" />
                <span className="font-bold text-[#1C1C1E]">
                  {alerts.filter((a) => a.tier === 'CRITICAL').length}
                </span>
              </span>
              <span className="text-xs flex items-center">
                <RiskBadge tier="HIGH" className="mr-1.5" />
                <span className="font-bold text-[#1C1C1E]">
                  {alerts.filter((a) => a.tier === 'HIGH').length}
                </span>
              </span>
              <span className="text-xs flex items-center">
                <RiskBadge tier="MEDIUM" className="mr-1.5" />
                <span className="font-bold text-[#1C1C1E]">
                  {alerts.filter((a) => a.tier === 'MEDIUM').length}
                </span>
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-[#6B7280]">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-blue-500"></span>
              Under Review: {alerts.filter((a) => a.status === 'UNDER_REVIEW' || a.status === 'INVESTIGATING').length}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-orange-500"></span>
              Escalated: {alerts.filter((a) => a.status === 'ESCALATED').length}
            </span>
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-gray-400"></span>
              Dismissed: {alerts.filter((a) => a.status === 'DISMISSED').length}
            </span>
          </div>
        </div>

        {/* Alerts Table */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide w-12">#</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Risk Tier</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Flagged Entity</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Fraud Typology</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Composite Score</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Assigned To</th>
                  <th className="px-4 py-3 text-center text-xs font-semibold text-[#6B7280] uppercase tracking-wide">Quick Triage</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-10 text-[#6B7280] text-sm">
                      <div className="flex items-center justify-center gap-2">
                        <Loader2 className="w-4 h-4 animate-spin text-[#1A3C5E]" />
                        <span>Loading alerts database...</span>
                      </div>
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={8} className="text-center py-10 text-[#C0392B] text-sm font-medium">
                      {error}
                    </td>
                  </tr>
                ) : alerts.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-10 text-[#6B7280] text-sm">
                      No fraud alerts matching active filter criteria.
                    </td>
                  </tr>
                ) : (
                  alerts.map((alert, index) => {
                    const isAlertBusy = actionLoadingId === alert.id;
                    const isNew = alert.status === 'NEW';
                    const isUnderReview = alert.status === 'UNDER_REVIEW' || alert.status === 'INVESTIGATING' || alert.status === 'ACKNOWLEDGED';
                    const isEscalated = alert.status === 'ESCALATED';
                    const isDismissed = alert.status === 'DISMISSED';

                    return (
                      <tr
                        key={alert.id}
                        className={`border-b border-[#DDE1E7] hover:bg-[#F8FAFC] transition-colors cursor-pointer ${
                          alert.tier === 'CRITICAL' ? 'border-l-4 border-l-[#C0392B]' : ''
                        } ${index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'}`}
                        onClick={() => setSelectedAlert(alert)}
                      >
                        <td className="px-4 py-3 text-xs font-mono text-[#6B7280] font-medium">{index + 1}</td>
                        <td className="px-4 py-3">
                          <RiskBadge tier={alert.tier} />
                        </td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-semibold text-[#1C1C1E]">{alert.entityName}</p>
                            <p className="text-xs text-[#6B7280]">{alert.entityType}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3 text-sm text-[#374151]">
                          <span className="font-medium">{alert.alertType}</span>
                        </td>
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2">
                            <div className="w-20 bg-[#E5E7EB] rounded-full h-2">
                              <div
                                className={`h-2 rounded-full ${
                                  alert.compositeScore >= 0.8
                                    ? 'bg-[#C0392B]'
                                    : alert.compositeScore >= 0.6
                                    ? 'bg-[#D35400]'
                                    : 'bg-[#2E7D52]'
                                }`}
                                style={{ width: `${Math.min(alert.compositeScore * 100, 100)}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono font-bold text-[#1A3C5E]">
                              {alert.compositeScore.toFixed(2)}
                            </span>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={alert.status} />
                        </td>
                        <td className="px-4 py-3 text-xs text-[#4B5563]">{alert.assignedTo}</td>
                        <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-center gap-1.5">
                            {/* Quick Acknowledge */}
                            {isNew && (
                              <button
                                type="button"
                                disabled={isAlertBusy}
                                onClick={() => handleAcknowledge(alert)}
                                title="Acknowledge alert and begin review"
                                className="px-2.5 py-1 text-xs font-medium bg-[#E8F8F0] text-[#2E7D52] hover:bg-[#D4EDDA] border border-[#C3E6CB] rounded transition-colors flex items-center gap-1"
                              >
                                {isAlertBusy ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  <Check className="w-3 h-3" />
                                )}
                                <span>Review</span>
                              </button>
                            )}

                            {/* Quick Escalate */}
                            {!isEscalated && !isDismissed && (
                              <button
                                type="button"
                                disabled={isAlertBusy}
                                onClick={() => openEscalateModal(alert)}
                                title="Escalate to formal Case Management"
                                className="px-2.5 py-1 text-xs font-medium bg-[#F0F7FF] text-[#1A3C5E] hover:bg-[#E0EFFE] border border-[#BFDBFE] rounded transition-colors flex items-center gap-1"
                              >
                                <span>Escalate</span>
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            )}

                            {/* Quick Dismiss */}
                            {!isDismissed && !isEscalated && (
                              <button
                                type="button"
                                disabled={isAlertBusy}
                                onClick={() => openDismissModal(alert)}
                                title="Dismiss false positive with reason code"
                                className="px-2 py-1 text-xs text-[#6B7280] hover:text-[#C0392B] hover:bg-red-50 border border-transparent hover:border-red-200 rounded transition-colors"
                              >
                                Dismiss
                              </button>
                            )}

                            {isEscalated && (
                              <button
                                onClick={() => navigate('/cases')}
                                className="text-xs font-medium text-[#1A3C5E] hover:underline flex items-center gap-1"
                              >
                                <span>View Case</span>
                                <ExternalLink className="w-3 h-3" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      </main>

      {/* ── Alert Detail Side Panel ─────────────────────────────────────────── */}
      {selectedAlert && (
        <div className="fixed inset-0 bg-black/40 z-50 flex justify-end">
          <div className="w-[500px] bg-white h-full overflow-y-auto shadow-2xl flex flex-col animate-in slide-in-from-right duration-200">
            <div className="sticky top-0 bg-white border-b border-[#DDE1E7] p-5 flex items-center justify-between z-10">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-bold text-[#6B7280]">
                    ALERT #{selectedAlert.id.slice(0, 8)}
                  </span>
                  <StatusBadge status={selectedAlert.status} />
                </div>
                <h2 className="font-bold text-lg text-[#1C1C1E]">{selectedAlert.alertType}</h2>
              </div>
              <button
                onClick={() => setSelectedAlert(null)}
                className="p-1.5 hover:bg-[#F4F6F9] rounded-lg text-gray-400 hover:text-gray-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6 flex-1">
              {/* Header Info */}
              <div className="flex items-center justify-between p-3.5 bg-[#F8FAFC] border border-[#E2E8F0] rounded-xl">
                <div>
                  <span className="text-[11px] text-[#6B7280] uppercase tracking-wider block mb-1">Risk Severity</span>
                  <RiskBadge tier={selectedAlert.tier} />
                </div>
                <div className="text-right">
                  <span className="text-[11px] text-[#6B7280] uppercase tracking-wider block mb-1">Triggered At</span>
                  <span className="text-xs font-mono font-medium text-[#374151]">{selectedAlert.triggeredAt}</span>
                </div>
              </div>

              {/* Description */}
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-[#6B7280] mb-2">Description & Forensic Signal</h3>
                <div className="bg-[#FFFBEB] border border-[#FDE68A] p-3.5 rounded-lg text-xs text-[#92400E] leading-relaxed">
                  {selectedAlert.description}
                </div>
              </div>

              {/* Entity info */}
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-[#6B7280] mb-2">Flagged Entity Context</h3>
                <div className="border border-[#DDE1E7] rounded-lg p-3 bg-white">
                  <p className="font-bold text-sm text-[#1A3C5E]">{selectedAlert.entityName}</p>
                  <p className="text-xs text-[#6B7280]">Type: {selectedAlert.entityType}</p>
                  <p className="text-xs text-[#6B7280] mt-1">Assigned Investigator: <span className="font-medium text-[#1C1C1E]">{selectedAlert.assignedTo}</span></p>
                </div>
              </div>

              {/* Composite score & Multi-model breakdown */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="font-bold text-xs uppercase tracking-wider text-[#6B7280]">3-Model Scoring Calibration</h3>
                  <span className="font-mono font-bold text-sm text-[#1A3C5E]">
                    Composite: {selectedAlert.compositeScore.toFixed(2)}
                  </span>
                </div>
                <div className="space-y-2.5 bg-[#F9FAFB] p-3.5 rounded-xl border border-[#E5E7EB]">
                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-[#374151]">Isolation Forest (40% Weight)</span>
                      <span className="font-mono font-bold">{selectedAlert.modelScores.IF.toFixed(2)}</span>
                    </div>
                    <div className="w-full bg-[#E5E7EB] rounded-full h-1.5">
                      <div className="bg-[#2471A3] h-1.5 rounded-full" style={{ width: `${selectedAlert.modelScores.IF * 100}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-[#374151]">Autoencoder MLP (30% Weight)</span>
                      <span className="font-mono font-bold">{selectedAlert.modelScores.AE.toFixed(2)}</span>
                    </div>
                    <div className="w-full bg-[#E5E7EB] rounded-full h-1.5">
                      <div className="bg-[#2E7D52] h-1.5 rounded-full" style={{ width: `${selectedAlert.modelScores.AE * 100}%` }} />
                    </div>
                  </div>

                  <div>
                    <div className="flex justify-between text-xs mb-1">
                      <span className="font-medium text-[#374151]">LSTM Temporal (30% Weight)</span>
                      <span className="font-mono font-bold">{selectedAlert.modelScores.LSTM.toFixed(2)}</span>
                    </div>
                    <div className="w-full bg-[#E5E7EB] rounded-full h-1.5">
                      <div className="bg-[#E8A020] h-1.5 rounded-full" style={{ width: `${selectedAlert.modelScores.LSTM * 100}%` }} />
                    </div>
                  </div>
                </div>
              </div>

              {/* Evidence */}
              <div>
                <h3 className="font-bold text-xs uppercase tracking-wider text-[#6B7280] mb-2">Engineered Feature Evidence</h3>
                <div className="space-y-2">
                  {selectedAlert.evidence.map((item, index) => (
                    <div key={index} className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3">
                      <p className="text-xs font-semibold text-[#1E3A8A] mb-1.5">{item.feature}</p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-white p-2 rounded border border-[#E2E8F0]">
                          <span className="text-[10px] text-[#6B7280] block">Expected Normal</span>
                          <span className="font-medium text-[#374151]">{item.expected}</span>
                        </div>
                        <div className="bg-white p-2 rounded border border-[#FEE2E2]">
                          <span className="text-[10px] text-[#C0392B] block">Observed Value</span>
                          <span className="font-bold text-[#C0392B]">{item.actual}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Blockchain Anchor */}
              <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3">
                <span className="text-[10px] font-bold uppercase tracking-wider text-[#6B7280] block mb-1">Audit Ledger Hash</span>
                <span className="text-xs font-mono text-[#475569] break-all">{selectedAlert.blockchainHash}</span>
              </div>
            </div>

            {/* Bottom Actions Bar */}
            <div className="sticky bottom-0 bg-white border-t border-[#DDE1E7] p-4 flex items-center gap-3">
              {selectedAlert.status === 'NEW' && (
                <button
                  type="button"
                  disabled={actionLoadingId === selectedAlert.id}
                  onClick={() => handleAcknowledge(selectedAlert)}
                  className="flex-1 bg-[#2E7D52] hover:bg-[#256543] text-white py-2.5 px-4 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2"
                >
                  {actionLoadingId === selectedAlert.id ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <UserCheck className="w-4 h-4" />
                  )}
                  <span>Acknowledge & Assign</span>
                </button>
              )}

              {selectedAlert.status !== 'ESCALATED' && selectedAlert.status !== 'DISMISSED' && (
                <button
                  type="button"
                  onClick={() => openEscalateModal(selectedAlert)}
                  className="flex-1 bg-[#1A3C5E] hover:bg-[#2471A3] text-white py-2.5 px-4 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2"
                >
                  <ArrowRight className="w-4 h-4" />
                  <span>Escalate to Case</span>
                </button>
              )}

              {selectedAlert.status !== 'DISMISSED' && selectedAlert.status !== 'ESCALATED' && (
                <button
                  type="button"
                  onClick={() => openDismissModal(selectedAlert)}
                  className="py-2.5 px-4 border border-[#DDE1E7] hover:bg-red-50 hover:border-red-300 text-xs font-bold text-[#C0392B] rounded-lg transition-colors"
                >
                  Dismiss False Positive
                </button>
              )}

              {selectedAlert.status === 'ESCALATED' && (
                <button
                  type="button"
                  onClick={() => navigate('/cases')}
                  className="flex-1 bg-[#1A3C5E] hover:bg-[#2471A3] text-white py-2.5 px-4 rounded-lg text-xs font-bold transition-colors flex items-center justify-center gap-2"
                >
                  <span>Open Active Case</span>
                  <ExternalLink className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ── Dismissal Feedback Modal ────────────────────────────────────────── */}
      {dismissModalOpen && dismissTarget && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-md w-full overflow-hidden border border-[#DDE1E7] animate-in zoom-in-95 duration-150">
            <div className="bg-[#FFFBEB] p-4 border-b border-[#FDE68A] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileWarning className="w-5 h-5 text-[#B9770E]" />
                <h3 className="font-bold text-sm text-[#92400E]">Dismiss Fraud Alert</h3>
              </div>
              <button
                onClick={() => setDismissModalOpen(false)}
                className="text-[#92400E] hover:text-[#78350F]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <p className="text-[#4B5563]">
                Dismissing marks this alert as a verified non-fraud event. This verdict is recorded into the audit trail and serves as training ground-truth feedback.
              </p>

              <div>
                <label className="block font-bold text-[#374151] mb-1">Dismissal Reason Code *</label>
                <select
                  value={dismissReason}
                  onChange={(e) => setDismissReason(e.target.value)}
                  className="w-full border border-[#DDE1E7] rounded-lg p-2.5 text-xs bg-white"
                >
                  <option value="FALSE_POSITIVE">FALSE_POSITIVE (Model Misclassification)</option>
                  <option value="LEGITIMATE_BULK_PURCHASE">LEGITIMATE_BULK_PURCHASE (Authorized Procurement)</option>
                  <option value="APPROVED_OFF_HOURS_OVERRIDE">APPROVED_OFF_HOURS_OVERRIDE (Emergency Approval)</option>
                  <option value="ENROLLMENT_DISCREPANCY_RESOLVED">ENROLLMENT_DISCREPANCY_RESOLVED (Registry Matched)</option>
                  <option value="DATA_ENTRY_ERROR">DATA_ENTRY_ERROR (Clerical Correction)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#374151] mb-1">Investigative Notes / Justification</label>
                <textarea
                  rows={3}
                  value={dismissNotes}
                  onChange={(e) => setDismissNotes(e.target.value)}
                  placeholder="Explain why this transaction or feeding log is benign..."
                  className="w-full border border-[#DDE1E7] rounded-lg p-2.5 text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E5E7EB]">
                <button
                  type="button"
                  onClick={() => setDismissModalOpen(false)}
                  className="px-4 py-2 border border-[#DDE1E7] rounded-lg text-[#4B5563] hover:bg-gray-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={dismissing}
                  onClick={handleConfirmDismiss}
                  className="px-4 py-2 bg-[#C0392B] hover:bg-[#A93226] text-white rounded-lg font-bold flex items-center gap-1.5"
                >
                  {dismissing && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Confirm Dismissal</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Single-Click Escalation Modal ───────────────────────────────────── */}
      {escalateModalOpen && escalateTarget && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full overflow-hidden border border-[#DDE1E7] animate-in zoom-in-95 duration-150">
            <div className="bg-gradient-to-r from-[#1A3C5E] to-[#2471A3] p-4 text-white flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-[#E8A020]" />
                <h3 className="font-bold text-sm">Escalate Alert to Investigation Case</h3>
              </div>
              <button
                onClick={() => setEscalateModalOpen(false)}
                className="text-white/80 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div className="bg-[#F0F7FF] border border-[#BFDBFE] p-3 rounded-lg">
                <span className="text-[10px] uppercase font-bold text-[#1E3A8A] block mb-1">Source Anomaly Target</span>
                <p className="font-bold text-[#1A3C5E] text-sm">{escalateTarget.entityName}</p>
                <p className="text-[11px] text-[#475569]">
                  {escalateTarget.alertType} &bull; Score: {escalateTarget.compositeScore.toFixed(2)} &bull; Tier: {escalateTarget.tier}
                </p>
              </div>

              <div>
                <label className="block font-bold text-[#374151] mb-1">Investigation Case Title *</label>
                <input
                  type="text"
                  value={escalateTitle}
                  onChange={(e) => setEscalateTitle(e.target.value)}
                  className="w-full border border-[#DDE1E7] rounded-lg p-2.5 text-xs font-medium"
                />
              </div>

              <div>
                <label className="block font-bold text-[#374151] mb-1">Initial Priority Tier *</label>
                <select
                  value={escalatePriority}
                  onChange={(e) => setEscalatePriority(e.target.value)}
                  className="w-full border border-[#DDE1E7] rounded-lg p-2.5 text-xs bg-white font-medium"
                >
                  <option value="CRITICAL">CRITICAL (24-hour SLA)</option>
                  <option value="HIGH">HIGH (72-hour SLA)</option>
                  <option value="MEDIUM">MEDIUM (7-day SLA)</option>
                  <option value="LOW">LOW (14-day SLA)</option>
                </select>
              </div>

              <div>
                <label className="block font-bold text-[#374151] mb-1">Investigation Handover Notes</label>
                <textarea
                  rows={3}
                  value={escalateNotes}
                  onChange={(e) => setEscalateNotes(e.target.value)}
                  placeholder="Provide context for the assigned investigator or forensic auditor..."
                  className="w-full border border-[#DDE1E7] rounded-lg p-2.5 text-xs"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-2 border-t border-[#E5E7EB]">
                <button
                  type="button"
                  onClick={() => setEscalateModalOpen(false)}
                  className="px-4 py-2 border border-[#DDE1E7] rounded-lg text-[#4B5563] hover:bg-gray-50 font-medium"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={escalating}
                  onClick={handleConfirmEscalate}
                  className="px-4 py-2 bg-[#1A3C5E] hover:bg-[#2471A3] text-white rounded-lg font-bold flex items-center gap-1.5"
                >
                  {escalating && <Loader2 className="w-3.5 h-3.5 animate-spin" />}
                  <span>Open Investigation Case</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
