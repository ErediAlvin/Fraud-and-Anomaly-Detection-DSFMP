import { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';
import { Clock, Plus, X, Send, UserCheck, ShieldAlert, FileText, CheckCircle2 } from 'lucide-react';
import { api } from '../lib/api';

interface Case {
  id: string;
  db_id: string;
  title: string;
  entityName: string;
  entityType: string;
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  stage: 'DETECTED' | 'TRIAGED' | 'UNDER INVESTIGATION' | 'ESCALATED' | 'RESOLVED';
  score: number;
  assignedTo: string;
  daysOpen: number;
  alertCount: number;
  sla: 'green' | 'amber' | 'red';
}

interface CaseDetail {
  id: string;
  db_id: string;
  title: string;
  description: string;
  priority: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  stage: 'DETECTED' | 'TRIAGED' | 'UNDER INVESTIGATION' | 'ESCALATED' | 'RESOLVED';
  status: string;
  category: string;
  entityType: string;
  entityName: string;
  assignedTo?: {
    id: string;
    name: string;
    email: string;
    role: string;
  } | null;
  createdBy: {
    id: string;
    name: string;
    email: string;
  };
  financials: {
    estimatedLoss: number;
    actualLoss: number | null;
  };
  sla: {
    targetHours: number;
    hoursOpen: number;
    hoursRemaining: number;
    status: string;
    color: string;
  };
  timestamps: {
    createdAt: string;
    updatedAt: string;
    closedAt: string | null;
    closureReason: string | null;
  };
  score: number;
  alerts: Array<{
    id: string;
    title: string;
    description: string;
    alertType: string;
    severity: string;
    compositeScore: number;
    blockchainHash: string;
  }>;
  comments: Array<{
    id: string;
    content: string;
    createdAt: string;
    author: {
      id: string;
      name: string;
      role: string;
    };
  }>;
}

export function CaseManagement() {
  const [view, setView] = useState<'kanban' | 'table'>('kanban');
  const [cases, setCases] = useState<Case[]>([]);
  const [stats, setStats] = useState({
    open: 0,
    investigating: 0,
    escalated: 0,
    resolved_this_month: 0,
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Selected Case Detail Drawer State
  const [selectedCaseId, setSelectedCaseId] = useState<string | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [newComment, setNewComment] = useState('');
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [isAssigning, setIsAssigning] = useState(false);
  const [assigneeEmail, setAssigneeEmail] = useState('');

  // New Case Modal State
  const [isNewCaseModalOpen, setIsNewCaseModalOpen] = useState(false);
  const [newCaseData, setNewCaseData] = useState({
    title: '',
    description: '',
    priority: 'MEDIUM',
    category: 'GHOST_BENEFICIARY',
    estimated_loss: 0,
  });
  const [isCreatingCase, setIsCreatingCase] = useState(false);

  const stages: Array<'DETECTED' | 'TRIAGED' | 'UNDER INVESTIGATION' | 'ESCALATED' | 'RESOLVED'> = [
    'DETECTED',
    'TRIAGED',
    'UNDER INVESTIGATION',
    'ESCALATED',
    'RESOLVED',
  ];

  const slaColors = {
    green: 'text-[#2E7D52]',
    amber: 'text-[#E8A020]',
    red: 'text-[#C0392B]',
  };

  const getCasesByStage = (stage: string) => {
    return cases.filter((c) => c.stage === stage);
  };

  const loadCases = async () => {
    try {
      setLoading(true);
      const res = await api.get<{ cases: Case[]; stats: any }>('/cases');
      setCases(res.cases);
      setStats(res.stats);
      setError('');
    } catch (err: any) {
      setError(err.message || 'Failed to load cases.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  // Fetch Full Case Detail when a case is selected
  const handleOpenDetail = async (caseId: string) => {
    setSelectedCaseId(caseId);
    setDetailLoading(true);
    try {
      const detail = await api.get<CaseDetail>(`/cases/${caseId}`);
      setCaseDetail(detail);
      setAssigneeEmail(detail.assignedTo?.email || '');
    } catch (err: any) {
      alert(err.message || 'Failed to fetch case dossier.');
      setSelectedCaseId(null);
    } finally {
      setDetailLoading(false);
    }
  };

  // Change Case Stage (PATCH /api/cases/{id}/status)
  const handleStageChange = async (targetStage: string) => {
    if (!selectedCaseId) return;
    try {
      await api.patch(`/cases/${selectedCaseId}/status`, { status: targetStage });
      setCases((prev) =>
        prev.map((c) => (c.id === selectedCaseId || c.db_id === selectedCaseId ? { ...c, stage: targetStage as any } : c))
      );
      if (caseDetail) {
        setCaseDetail({ ...caseDetail, stage: targetStage as any });
      }
      loadCases();
    } catch (err: any) {
      alert(err.message || 'Failed to update stage.');
    }
  };

  // Assign Investigator (POST /api/cases/{id}/assign)
  const handleAssignInvestigator = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCaseId || !assigneeEmail.trim()) return;
    setIsAssigning(true);
    try {
      const res = await api.post<{ status: string; assigned_to: string; stage: string }>(
        `/cases/${selectedCaseId}/assign`,
        { email: assigneeEmail.trim() }
      );
      setCases((prev) =>
        prev.map((c) =>
          c.id === selectedCaseId || c.db_id === selectedCaseId
            ? { ...c, assignedTo: res.assigned_to, stage: res.stage as any }
            : c
        )
      );
      if (caseDetail) {
        setCaseDetail({
          ...caseDetail,
          assignedTo: {
            id: '',
            name: res.assigned_to,
            email: assigneeEmail.trim(),
            role: 'Investigator',
          },
          stage: res.stage as any,
        });
      }
      alert(`Case assigned to ${res.assigned_to}`);
    } catch (err: any) {
      alert(err.message || 'Failed to assign investigator.');
    } finally {
      setIsAssigning(false);
    }
  };

  // Add Comment (POST /api/cases/{id}/comments)
  const handleAddComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedCaseId || !newComment.trim()) return;
    setIsSubmittingComment(true);
    try {
      const res = await api.post<{ status: string; comment: any }>(`/cases/${selectedCaseId}/comments`, {
        content: newComment.trim(),
      });
      if (res.comment && caseDetail) {
        setCaseDetail({
          ...caseDetail,
          comments: [
            ...caseDetail.comments,
            {
              id: res.comment.id,
              content: res.comment.content,
              createdAt: res.comment.createdAt,
              author: {
                id: res.comment.author.id,
                name: res.comment.author.name,
                role: 'Analyst',
              },
            },
          ],
        });
      }
      setNewComment('');
    } catch (err: any) {
      alert(err.message || 'Failed to post comment.');
    } finally {
      setIsSubmittingComment(false);
    }
  };

  // Create New Case (POST /api/cases)
  const handleCreateCase = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCaseData.title.trim()) return;
    setIsCreatingCase(true);
    try {
      await api.post('/cases', newCaseData);
      setIsNewCaseModalOpen(false);
      setNewCaseData({
        title: '',
        description: '',
        priority: 'MEDIUM',
        category: 'GHOST_BENEFICIARY',
        estimated_loss: 0,
      });
      await loadCases();
    } catch (err: any) {
      alert(err.message || 'Failed to open case.');
    } finally {
      setIsCreatingCase(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden relative">
      <Header breadcrumbs={['Case Management']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Summary cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-4">
            <p className="text-2xl font-bold">{loading ? '...' : stats.open}</p>
            <p className="text-sm text-[#6B7280]">Open Cases</p>
          </div>
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-4">
            <p className="text-2xl font-bold">{loading ? '...' : stats.investigating}</p>
            <p className="text-sm text-[#6B7280]">Under Investigation</p>
          </div>
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-4">
            <p className="text-2xl font-bold">{loading ? '...' : stats.escalated}</p>
            <p className="text-sm text-[#6B7280]">Escalated</p>
          </div>
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-4">
            <p className="text-2xl font-bold">{loading ? '...' : stats.resolved_this_month}</p>
            <p className="text-sm text-[#6B7280]">Resolved This Month</p>
          </div>
        </div>

        {/* View toggle & Action Bar */}
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setView('kanban')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                view === 'kanban'
                  ? 'bg-[#1A3C5E] text-white shadow-sm'
                  : 'bg-white border border-[#DDE1E7] text-[#6B7280] hover:bg-[#F4F6F9]'
              }`}
            >
              Kanban View
            </button>
            <button
              onClick={() => setView('table')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                view === 'table'
                  ? 'bg-[#1A3C5E] text-white shadow-sm'
                  : 'bg-white border border-[#DDE1E7] text-[#6B7280] hover:bg-[#F4F6F9]'
              }`}
            >
              Table View
            </button>
          </div>

          <button
            onClick={() => setIsNewCaseModalOpen(true)}
            className="flex items-center gap-2 bg-[#2E7D52] hover:bg-[#256643] text-white px-4 py-2 rounded-lg font-medium shadow-sm transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>Open Investigation</span>
          </button>
        </div>

        {loading ? (
          <div className="text-center py-16 text-[#6B7280] text-sm">Loading active investigation pipeline...</div>
        ) : error ? (
          <div className="text-center py-8 text-[#C0392B] text-sm font-medium">{error}</div>
        ) : (
          <>
            {/* Kanban view */}
            {view === 'kanban' && (
              <div className="grid grid-cols-5 gap-4 overflow-x-auto pb-4">
                {stages.map((stage) => (
                  <div key={stage} className="min-w-[280px]">
                    <div className="bg-white rounded-t-lg border border-[#DDE1E7] border-b-0 p-3 flex items-center justify-between">
                      <h3 className="font-bold text-xs uppercase tracking-wider text-[#1A3C5E]">{stage}</h3>
                      <span className="text-xs bg-[#F4F6F9] px-2 py-0.5 rounded-full font-mono text-[#6B7280]">
                        {getCasesByStage(stage).length}
                      </span>
                    </div>
                    <div className="space-y-3 bg-[#FAFAFA] rounded-b-lg border border-[#DDE1E7] border-t-0 p-3 min-h-[500px]">
                      {getCasesByStage(stage).map((caseItem) => (
                        <div
                          key={caseItem.id}
                          onClick={() => handleOpenDetail(caseItem.id)}
                          className="bg-white rounded-lg border border-[#DDE1E7] p-4 shadow-sm hover:shadow-md hover:border-[#1A3C5E] transition-all cursor-pointer group"
                        >
                          <div className="flex items-start justify-between mb-2">
                            <RiskBadge tier={caseItem.tier} />
                            <span className={`text-xs ${slaColors[caseItem.sla]}`}>
                              <Clock className="w-3 h-3 inline mr-1" />
                              {caseItem.daysOpen}d
                            </span>
                          </div>

                          <h4 className="font-medium text-sm mb-1 text-[#1A3C5E] group-hover:text-[#2471A3] transition-colors">
                            {caseItem.entityName}
                          </h4>
                          <p className="text-xs text-[#6B7280] mb-3">{caseItem.entityType}</p>

                          <div className="flex items-center gap-2 mb-3">
                            <div className="flex-1 bg-[#F4F6F9] rounded-full h-1.5">
                              <div
                                className="bg-[#C0392B] h-1.5 rounded-full"
                                style={{ width: `${caseItem.score * 100}%` }}
                              />
                            </div>
                            <span className="text-xs font-mono font-medium">{caseItem.score.toFixed(2)}</span>
                          </div>

                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-1.5">
                              <div className="w-5 h-5 rounded-full bg-[#1A3C5E] flex items-center justify-center text-white text-[10px] font-bold">
                                {caseItem.assignedTo ? caseItem.assignedTo.split(' ')[0][0] : 'U'}
                              </div>
                              <span className="text-[#6B7280] truncate max-w-[110px]">{caseItem.assignedTo}</span>
                            </div>
                            <span className="text-[#6B7280] bg-[#F4F6F9] px-1.5 py-0.5 rounded text-[10px]">
                              {caseItem.alertCount} alert{caseItem.alertCount === 1 ? '' : 's'}
                            </span>
                          </div>

                          <p className="text-[11px] font-mono text-[#9CA3AF] mt-2 pt-2 border-t border-[#F4F6F9]">
                            {caseItem.id}
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Table view */}
            {view === 'table' && (
              <div className="bg-white rounded-lg border border-[#DDE1E7] overflow-hidden">
                <table className="w-full">
                  <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Case ID
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Entity
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Risk Tier
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Stage
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Assigned To
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Days Open
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                        Alerts
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cases.map((caseItem, index) => (
                      <tr
                        key={caseItem.id}
                        onClick={() => handleOpenDetail(caseItem.id)}
                        className={`border-b border-[#DDE1E7] hover:bg-[#F4F6F9] cursor-pointer transition-colors ${
                          index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'
                        }`}
                      >
                        <td className="px-4 py-3 text-sm font-mono font-medium text-[#1A3C5E]">{caseItem.id}</td>
                        <td className="px-4 py-3">
                          <div>
                            <p className="text-sm font-medium">{caseItem.entityName}</p>
                            <p className="text-xs text-[#6B7280]">{caseItem.entityType}</p>
                          </div>
                        </td>
                        <td className="px-4 py-3">
                          <RiskBadge tier={caseItem.tier} />
                        </td>
                        <td className="px-4 py-3 text-sm">
                          <StatusBadge status={caseItem.stage} />
                        </td>
                        <td className="px-4 py-3 text-sm">{caseItem.assignedTo}</td>
                        <td className="px-4 py-3">
                          <span className={`text-sm ${slaColors[caseItem.sla]}`}>
                            {caseItem.daysOpen} days
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm font-mono">{caseItem.alertCount}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </main>

      {/* ── Slide-Over Case Dossier Drawer ────────────────────────── */}
      {selectedCaseId && (
        <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-black/40 backdrop-blur-xs transition-opacity">
          <div className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col border-l border-[#DDE1E7] animate-in slide-in-from-right duration-200">
            {/* Header */}
            <div className="p-5 border-b border-[#DDE1E7] flex items-center justify-between bg-[#F8FAFC]">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono text-[#6B7280]">{caseDetail?.id || selectedCaseId}</span>
                  {caseDetail && <RiskBadge tier={caseDetail.priority} />}
                </div>
                <h2 className="text-lg font-bold text-[#1A3C5E] mt-0.5">
                  {caseDetail?.title || 'Case Dossier'}
                </h2>
              </div>
              <button
                onClick={() => setSelectedCaseId(null)}
                className="p-2 rounded-lg hover:bg-[#E2E8F0] text-[#6B7280] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Body */}
            {detailLoading ? (
              <div className="flex-1 flex items-center justify-center text-sm text-[#6B7280]">
                Loading case dossier and evidence...
              </div>
            ) : caseDetail ? (
              <div className="flex-1 overflow-y-auto p-6 space-y-6">
                {/* Stage Progression Selector */}
                <div className="bg-[#F8FAFC] border border-[#DDE1E7] rounded-lg p-4">
                  <p className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-2">Lifecycle Stage</p>
                  <div className="flex flex-wrap gap-2">
                    {stages.map((stg) => (
                      <button
                        key={stg}
                        onClick={() => handleStageChange(stg)}
                        className={`text-xs px-3 py-1.5 rounded-md font-medium transition-all ${
                          caseDetail.stage === stg
                            ? 'bg-[#1A3C5E] text-white shadow-sm'
                            : 'bg-white border border-[#DDE1E7] text-[#6B7280] hover:border-[#1A3C5E]'
                        }`}
                      >
                        {stg}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Metadata & SLA Grid */}
                <div className="grid grid-cols-2 gap-4 text-sm bg-white border border-[#DDE1E7] rounded-lg p-4">
                  <div>
                    <span className="text-xs text-[#6B7280]">Entity / Location</span>
                    <p className="font-medium text-[#1A3C5E]">{caseDetail.entityName}</p>
                    <p className="text-xs text-[#6B7280]">{caseDetail.entityType}</p>
                  </div>
                  <div>
                    <span className="text-xs text-[#6B7280]">Resolution SLA</span>
                    <p className="font-medium flex items-center gap-1.5 text-xs">
                      <span className={`w-2 h-2 rounded-full ${caseDetail.sla.color === 'red' ? 'bg-[#C0392B]' : caseDetail.sla.color === 'amber' ? 'bg-[#E8A020]' : 'bg-[#2E7D52]'}`}></span>
                      {caseDetail.sla.status} ({caseDetail.sla.hoursRemaining}h remaining)
                    </p>
                  </div>
                  <div>
                    <span className="text-xs text-[#6B7280]">Estimated Financial Impact</span>
                    <p className="font-mono font-medium">KES {caseDetail.financials.estimatedLoss.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-xs text-[#6B7280]">Opened At</span>
                    <p className="text-xs text-[#6B7280]">{caseDetail.timestamps.createdAt}</p>
                  </div>
                </div>

                {/* Description */}
                <div>
                  <h3 className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-1">
                    Forensic Overview
                  </h3>
                  <p className="text-sm text-[#374151] bg-[#FAFAFA] p-3 rounded-lg border border-[#DDE1E7]">
                    {caseDetail.description || 'No description recorded.'}
                  </p>
                </div>

                {/* Investigator Assignment */}
                <div className="bg-white border border-[#DDE1E7] rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-[#6B7280] uppercase tracking-wider">
                      Assigned Investigator
                    </span>
                    <span className="text-xs font-medium text-[#1A3C5E]">
                      {caseDetail.assignedTo?.name || 'Currently Unassigned'}
                    </span>
                  </div>
                  <form onSubmit={handleAssignInvestigator} className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Enter investigator email or UUID..."
                      value={assigneeEmail}
                      onChange={(e) => setAssigneeEmail(e.target.value)}
                      className="flex-1 text-xs border border-[#DDE1E7] rounded-md px-3 py-1.5 focus:outline-none focus:border-[#1A3C5E]"
                    />
                    <button
                      type="submit"
                      disabled={isAssigning}
                      className="bg-[#1A3C5E] text-white text-xs px-3 py-1.5 rounded-md font-medium hover:bg-[#2471A3] transition-colors disabled:opacity-50 flex items-center gap-1"
                    >
                      <UserCheck className="w-3.5 h-3.5" />
                      <span>{isAssigning ? 'Saving...' : 'Assign'}</span>
                    </button>
                  </form>
                </div>

                {/* Linked Alerts */}
                <div>
                  <h3 className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-2">
                    Linked Fraud Alerts ({caseDetail.alerts.length})
                  </h3>
                  <div className="space-y-2">
                    {caseDetail.alerts.map((alt) => (
                      <div key={alt.id} className="p-3 bg-[#F8FAFC] border border-[#DDE1E7] rounded-lg text-xs space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[#1A3C5E]">{alt.title}</span>
                          <span className="font-mono text-[#C0392B] font-medium">Score: {alt.compositeScore.toFixed(2)}</span>
                        </div>
                        <p className="text-[#6B7280]">{alt.description}</p>
                        <div className="text-[10px] font-mono text-[#9CA3AF] truncate">Hash: {alt.blockchainHash}</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Collaboration & Comments Thread */}
                <div>
                  <h3 className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-2">
                    Investigator Collaboration Thread ({caseDetail.comments.length})
                  </h3>
                  <div className="space-y-3 mb-3 max-h-60 overflow-y-auto">
                    {caseDetail.comments.length === 0 ? (
                      <p className="text-xs text-[#9CA3AF] italic">No investigator comments yet.</p>
                    ) : (
                      caseDetail.comments.map((cm) => (
                        <div key={cm.id} className="bg-[#F8FAFC] p-3 rounded-lg border border-[#DDE1E7] text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-bold text-[#1A3C5E]">{cm.author.name}</span>
                            <span className="text-[10px] text-[#9CA3AF]">{cm.createdAt}</span>
                          </div>
                          <p className="text-[#374151] whitespace-pre-wrap">{cm.content}</p>
                        </div>
                      ))
                    )}
                  </div>

                  <form onSubmit={handleAddComment} className="flex gap-2">
                    <input
                      type="text"
                      placeholder="Add investigation note or finding..."
                      value={newComment}
                      onChange={(e) => setNewComment(e.target.value)}
                      className="flex-1 text-xs border border-[#DDE1E7] rounded-md px-3 py-2 focus:outline-none focus:border-[#1A3C5E]"
                    />
                    <button
                      type="submit"
                      disabled={isSubmittingComment || !newComment.trim()}
                      className="bg-[#2E7D52] hover:bg-[#256643] text-white px-3 py-2 rounded-md font-medium text-xs flex items-center gap-1 transition-colors disabled:opacity-50"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>Post</span>
                    </button>
                  </form>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      )}

      {/* ── Open Investigation Modal ────────────────────────────── */}
      {isNewCaseModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-xs p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-lg w-full border border-[#DDE1E7] overflow-hidden">
            <div className="p-4 border-b border-[#DDE1E7] flex items-center justify-between bg-[#F8FAFC]">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-5 h-5 text-[#C0392B]" />
                <h3 className="font-bold text-[#1A3C5E]">Open New Fraud Investigation</h3>
              </div>
              <button
                onClick={() => setIsNewCaseModalOpen(false)}
                className="p-1 rounded hover:bg-[#E2E8F0] text-[#6B7280]"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleCreateCase} className="p-5 space-y-4 text-sm">
              <div>
                <label className="block text-xs font-bold text-[#6B7280] uppercase mb-1">Investigation Title *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Unreconciled Grain Shortage - Mombasa Primary"
                  value={newCaseData.title}
                  onChange={(e) => setNewCaseData({ ...newCaseData, title: e.target.value })}
                  className="w-full text-xs border border-[#DDE1E7] rounded-md px-3 py-2 focus:outline-none focus:border-[#1A3C5E]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-bold text-[#6B7280] uppercase mb-1">Priority Tier</label>
                  <select
                    value={newCaseData.priority}
                    onChange={(e) => setNewCaseData({ ...newCaseData, priority: e.target.value })}
                    className="w-full text-xs border border-[#DDE1E7] rounded-md px-3 py-2 focus:outline-none focus:border-[#1A3C5E] bg-white"
                  >
                    <option value="LOW">LOW</option>
                    <option value="MEDIUM">MEDIUM</option>
                    <option value="HIGH">HIGH</option>
                    <option value="CRITICAL">CRITICAL</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#6B7280] uppercase mb-1">Fraud Category</label>
                  <select
                    value={newCaseData.category}
                    onChange={(e) => setNewCaseData({ ...newCaseData, category: e.target.value })}
                    className="w-full text-xs border border-[#DDE1E7] rounded-md px-3 py-2 focus:outline-none focus:border-[#1A3C5E] bg-white"
                  >
                    <option value="GHOST_BENEFICIARY">Ghost Beneficiary</option>
                    <option value="PAYMENT_FRAUD">Payment Anomaly</option>
                    <option value="SUPPLY_CHAIN">Supply Chain Shortage</option>
                    <option value="COLLUSION">Collusion Network</option>
                    <option value="DATA_TAMPERING">Record Tampering</option>
                    <option value="OTHER">Other Anomaly</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-[#6B7280] uppercase mb-1">Estimated Exposure (KES)</label>
                <input
                  type="number"
                  min="0"
                  placeholder="e.g. 250000"
                  value={newCaseData.estimated_loss || ''}
                  onChange={(e) => setNewCaseData({ ...newCaseData, estimated_loss: parseFloat(e.target.value) || 0 })}
                  className="w-full text-xs border border-[#DDE1E7] rounded-md px-3 py-2 focus:outline-none focus:border-[#1A3C5E]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-[#6B7280] uppercase mb-1">Forensic Description</label>
                <textarea
                  rows={3}
                  placeholder="Outline anomalies, involved officers, or initial indicators..."
                  value={newCaseData.description}
                  onChange={(e) => setNewCaseData({ ...newCaseData, description: e.target.value })}
                  className="w-full text-xs border border-[#DDE1E7] rounded-md px-3 py-2 focus:outline-none focus:border-[#1A3C5E]"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsNewCaseModalOpen(false)}
                  className="px-4 py-2 border border-[#DDE1E7] rounded-md text-xs font-medium text-[#6B7280] hover:bg-[#F4F6F9]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isCreatingCase || !newCaseData.title.trim()}
                  className="bg-[#2E7D52] hover:bg-[#256643] text-white px-4 py-2 rounded-md text-xs font-medium transition-colors disabled:opacity-50"
                >
                  {isCreatingCase ? 'Creating Case...' : 'Open Case'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
