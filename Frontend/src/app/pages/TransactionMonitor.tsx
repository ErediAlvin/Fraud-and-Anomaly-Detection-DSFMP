import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import { Header } from '../components/Header';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';
import { StatCard } from '../components/StatCard';
import {
  CreditCard,
  DollarSign,
  ShieldAlert,
  Lock,
  X,
  CheckCircle,
  Plus,
  Zap,
  AlertTriangle,
  Activity,
  Loader2,
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../lib/api';

interface PaginationMetadata {
  page: number;
  limit: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

interface Transaction {
  id: string;
  type: 'MPESA' | 'SUBSIDY' | 'DONOR' | 'PROCUREMENT';
  payer: string;
  recipient: string;
  amount: number;
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'EVALUATING';
  mlScore: number;
  blockchainStatus: 'VERIFIED' | 'PENDING' | 'FAILED';
  smartContractStatus: 'PASSED' | 'BLOCKED';
  timestamp: string;
  modelScores: { IF: number; AE: number; LSTM: number; GNN: number };
  anomalyFeatures: string[];
  blockchainHash: string;
  description: string;
}

export function TransactionMonitor() {
  const navigate = useNavigate();
  const [selectedTx, setSelectedTx] = useState<Transaction | null>(null);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [stats, setStats] = useState({
    totalTransactions: '0',
    totalValue: '0',
    flaggedTransactions: 0,
    blockedTransactions: 0,
    falsePositiveRate: '0%'
  });
  const [hourlyVolume, setHourlyVolume] = useState<any[]>([]);
  const [amountDistribution, setAmountDistribution] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    type: 'ALL',
    tier: 'ALL',
  });
  const [search, setSearch] = useState('');
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [pagination, setPagination] = useState<PaginationMetadata>({
    page: 1,
    limit: 15,
    total: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false,
  });
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [actionLoading, setActionLoading] = useState(false);
  const [liveIFMsg, setLiveIFMsg] = useState<{
    score: number;
    aeScore?: number;
    lstmScore?: number;
    ensembleScore?: number;
    tier: string;
    latency: number;
    reasons: string[];
  } | null>(null);

  // Ingestion Modal States
  const [isIngestModalOpen, setIsIngestModalOpen] = useState(false);
  const [availableSchools, setAvailableSchools] = useState<{ id: string; name: string; nemis?: string; enrollment: number }[]>([]);
  const [ingestForm, setIngestForm] = useState({
    school_id: '',
    amount: '48750',
    type: 'SUBSIDY',
    payment_method: 'BANK_TRANSFER',
    transacted_at: new Date().toISOString().slice(0, 16),
    description: 'Routine term porridge subsidy grant disbursement',
    reference_no: '',
  });
  const [ingestStatus, setIngestStatus] = useState<'IDLE' | 'QUEUED' | 'EVALUATING' | 'SCORED' | 'ERROR'>('IDLE');
  const [ingestResult, setIngestResult] = useState<any>(null);
  const [ingestError, setIngestError] = useState('');

  // Fetch schools context for ingestion selection
  useEffect(() => {
    async function fetchSchools() {
      try {
        const schools = await api.get<any[]>('/transactions/context/schools');
        if (schools && schools.length > 0) {
          setAvailableSchools(schools);
          setIngestForm(prev => ({ ...prev, school_id: prev.school_id || schools[0].id }));
        }
      } catch (e) {
        console.warn('Failed to load schools for ingestion modal:', e);
      }
    }
    fetchSchools();
  }, []);

  const applyPreset = (presetName: 'NORMAL' | 'SURGE' | 'GHOST') => {
    const defaultSchool = availableSchools[0]?.id || '';
    const now = new Date();
    if (presetName === 'NORMAL') {
      now.setHours(10, 30, 0, 0);
      setIngestForm({
        school_id: defaultSchool,
        amount: '48750',
        type: 'SUBSIDY',
        payment_method: 'BANK_TRANSFER',
        transacted_at: now.toISOString().slice(0, 16),
        description: 'Routine term porridge subsidy grant disbursement',
        reference_no: `NORM-${Date.now().toString().slice(-6)}`,
      });
    } else if (presetName === 'SURGE') {
      const midnight = new Date();
      midnight.setHours(2, 30, 0, 0);
      setIngestForm({
        school_id: availableSchools[1]?.id || defaultSchool,
        amount: '2000000',
        type: 'SUBSIDY',
        payment_method: 'BANK_TRANSFER',
        transacted_at: midnight.toISOString().slice(0, 16),
        description: 'Suspicious midnight off-hours county treasury transfer',
        reference_no: `SURGE-${Date.now().toString().slice(-6)}`,
      });
    } else if (presetName === 'GHOST') {
      now.setHours(11, 45, 0, 0);
      setIngestForm({
        school_id: availableSchools[2]?.id || defaultSchool,
        amount: '980000',
        type: 'PROCUREMENT',
        payment_method: 'BANK_TRANSFER',
        transacted_at: now.toISOString().slice(0, 16),
        description: 'Inflated food distribution invoice exceeding student count baseline',
        reference_no: `GHOST-${Date.now().toString().slice(-6)}`,
      });
    }
    setIngestStatus('IDLE');
    setIngestResult(null);
    setIngestError('');
  };

  const handleSimulateIngest = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIngestStatus('QUEUED');
      setIngestError('');
      setIngestResult(null);

      const payload = {
        school_id: ingestForm.school_id || availableSchools[0]?.id,
        amount: parseFloat(ingestForm.amount),
        type: ingestForm.type,
        payment_method: ingestForm.payment_method,
        transacted_at: ingestForm.transacted_at ? new Date(ingestForm.transacted_at).toISOString() : undefined,
        description: ingestForm.description,
        reference_no: ingestForm.reference_no || undefined,
      };

      const res = await api.post<any>('/transactions', payload);
      const txnId = res.transaction_id;
      setIngestStatus('EVALUATING');

      // Refresh table immediately so newly queued transaction appears in EVALUATING state
      setRefreshTrigger(prev => prev + 1);

      // Poll for 3-model background scoring completion
      let attempts = 0;
      const interval = setInterval(async () => {
        attempts++;
        try {
          const checkRes = await api.get<any>(`/transactions/${txnId}`);
          if (checkRes && checkRes.risk_tier !== 'EVALUATING') {
            clearInterval(interval);
            setIngestStatus('SCORED');
            setIngestResult(checkRes);
            // Refresh table & KPI stats
            setRefreshTrigger(prev => prev + 1);
          } else if (attempts >= 15) {
            clearInterval(interval);
            setIngestStatus('SCORED');
            setIngestResult(checkRes);
            setRefreshTrigger(prev => prev + 1);
          }
        } catch (pollErr) {
          if (attempts >= 10) {
            clearInterval(interval);
            setIngestStatus('ERROR');
            setIngestError('Timed out polling transaction anomaly score.');
          }
        }
      }, 700);
    } catch (err: any) {
      setIngestStatus('ERROR');
      setIngestError(err.message || 'Failed to ingest transaction');
    }
  };

  const handleTestLiveIF = async (txnId: string) => {
    try {
      setActionLoading(true);
      setLiveIFMsg(null);
      const res = await api.post<any>(`/transactions/${txnId}/evaluate-isolation-forest`, {
        amount: selectedTx?.amount,
        type: selectedTx?.type,
        payer: selectedTx?.payer,
        recipient: selectedTx?.recipient,
        timestamp: selectedTx?.timestamp
      });
      if (res && res.inference) {
        const ifScore = Number(res.inference.anomaly_score ?? 0);
        const aeScore =
          res.ae_inference?.anomaly_score !== undefined
            ? Number(res.ae_inference.anomaly_score)
            : selectedTx?.modelScores?.AE;
        const lstmScore =
          res.lstm_inference?.anomaly_score !== undefined
            ? Number(res.lstm_inference.anomaly_score)
            : selectedTx?.modelScores?.LSTM;
        const fallbackComposite = Number(
          (
            0.4 * ifScore +
            0.3 * (aeScore ?? ifScore) +
            0.3 * (lstmScore ?? ifScore)
          ).toFixed(4)
        );
        const ensembleScore =
          res.ensemble?.composite_score !== undefined
            ? Number(res.ensemble.composite_score)
            : fallbackComposite;
        const tier =
          res.ensemble?.risk_tier ||
          (ensembleScore >= 0.8
            ? 'CRITICAL'
            : ensembleScore >= 0.6
            ? 'HIGH'
            : ensembleScore >= 0.4
            ? 'MEDIUM'
            : 'LOW');
        const combinedReasons = Array.from(
          new Set<string>([
            ...(res.lstm_inference?.reasons || []),
            ...(res.ae_inference?.reasons || []),
            ...(res.inference.reasons || []),
          ])
        );
        const totalLatency = Number(
          (
            res.inference.latency_ms +
            (res.ae_inference?.latency_ms || 0) +
            (res.lstm_inference?.latency_ms || 0)
          ).toFixed(2)
        );
        setLiveIFMsg({
          score: ifScore,
          aeScore,
          lstmScore,
          ensembleScore,
          tier,
          latency: totalLatency,
          reasons: combinedReasons
        });
        // Update both the open drawer state and the main transactions table row so all score bars animate immediately
        setSelectedTx(prev => {
          if (!prev || prev.id !== txnId) return prev;
          return {
            ...prev,
            mlScore: ensembleScore,
            tier,
            modelScores: {
              ...prev.modelScores,
              IF: ifScore,
              ...(aeScore !== undefined ? { AE: aeScore } : {}),
              ...(lstmScore !== undefined ? { LSTM: lstmScore } : {}),
            }
          };
        });
        setTransactions(prev =>
          prev.map(tx =>
            tx.id === txnId
              ? {
                  ...tx,
                  mlScore: ensembleScore,
                  tier,
                  modelScores: {
                    ...tx.modelScores,
                    IF: ifScore,
                    ...(aeScore !== undefined ? { AE: aeScore } : {}),
                    ...(lstmScore !== undefined ? { LSTM: lstmScore } : {}),
                  },
                }
              : tx
          )
        );
      }
    } catch (err: any) {
      alert(err.message || 'Failed to execute live model inference.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleInvestigate = async (txnId: string) => {
    try {
      setActionLoading(true);
      const res = await api.post<any>(`/transactions/${txnId}/investigate`);
      window.dispatchEvent(new CustomEvent('dsfmp_notification_refresh'));
      setRefreshTrigger(prev => prev + 1);
      setSelectedTx(null);
      // Route directly to the newly created / linked case in Case Management
      navigate('/cases');
    } catch (err: any) {
      alert(err.message || 'Failed to mark transaction for investigation.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleClear = async (txnId: string) => {
    try {
      setActionLoading(true);
      await api.post(`/transactions/${txnId}/clear`);
      setRefreshTrigger(prev => prev + 1);
      setSelectedTx(null);
    } catch (err: any) {
      alert(err.message || 'Failed to clear transaction risk.');
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    async function loadTransactions() {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.type !== 'ALL') params.append('type', filters.type);
        if (filters.tier !== 'ALL') params.append('tier', filters.tier);
        if (search) params.append('search', search);
        params.append('page', currentPage.toString());
        params.append('limit', '15');

        const res = await api.get<any>(`/transactions?${params.toString()}`);
        if (isMounted) {
          setTransactions(res.transactions || []);
          if (res.pagination) {
            setPagination(res.pagination);
          } else {
            const total = res.transactions?.length || 0;
            setPagination({
              page: currentPage,
              limit: 15,
              total,
              total_pages: Math.max(1, Math.ceil(total / 15)),
              has_next: false,
              has_prev: false,
            });
          }
          setStats(res.stats);
          setHourlyVolume(res.hourly_volume);
          setAmountDistribution(res.amount_distribution);
          setError('');
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load transactions.');
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(() => {
      loadTransactions();
    }, 300); // Debounce typing

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [filters, search, currentPage, refreshTrigger]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['Transaction Monitor']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Summary cards */}
        <div className="grid grid-cols-5 gap-4 mb-6">
          <StatCard icon={CreditCard} label="Total Transactions Today" value={loading ? '...' : stats.totalTransactions} />
          <StatCard icon={DollarSign} label="Total Value (KES)" value={loading ? '...' : stats.totalValue} />
          <StatCard icon={ShieldAlert} label="Flagged Transactions" value={loading ? 0 : stats.flaggedTransactions} variant="warning" />
          <StatCard icon={Lock} label="Blocked by Smart Contract" value={loading ? 0 : stats.blockedTransactions} variant="critical" />
          <StatCard label="False Positive Rate" value={loading ? '...' : stats.falsePositiveRate} />
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-xs text-[#6B7280] mb-1">Transaction Type</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm"
                value={filters.type}
                onChange={(e) => {
                  setFilters({ ...filters, type: e.target.value });
                  setCurrentPage(1);
                }}
              >
                <option value="ALL">All Types</option>
                <option value="MPESA">M-Pesa</option>
                <option value="SUBSIDY">Subsidy</option>
                <option value="DONOR">Donor</option>
                <option value="PROCUREMENT">Procurement</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-[#6B7280] mb-1">Risk Tier</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm"
                value={filters.tier}
                onChange={(e) => {
                  setFilters({ ...filters, tier: e.target.value });
                  setCurrentPage(1);
                }}
              >
                <option value="ALL">All Tiers</option>
                <option value="CRITICAL">CRITICAL</option>
                <option value="HIGH">HIGH</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="LOW">LOW</option>
              </select>
            </div>

            <div className="flex-1"></div>

            <div className="flex items-center gap-3 self-end">
              <input
                type="text"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setCurrentPage(1);
                }}
                placeholder="Search by transaction ID..."
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm w-64"
              />
              <button
                type="button"
                onClick={() => {
                  setIsIngestModalOpen(true);
                  setIngestStatus('IDLE');
                  setIngestResult(null);
                  setIngestError('');
                }}
                className="flex items-center gap-1.5 bg-[#1A3C5E] hover:bg-[#2E7D52] text-white px-3.5 py-1.5 rounded text-sm font-medium transition-colors shadow-sm cursor-pointer"
              >
                <Plus className="w-4 h-4" />
                Simulate Ingestion
              </button>
            </div>
          </div>
        </div>

        {/* Transactions table */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide w-12">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Type
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Payer
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Recipient
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Amount (KES)
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Risk Tier
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    ML Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Smart Contract
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-[#6B7280] text-sm">
                      Loading transactions...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-[#C0392B] text-sm font-medium">
                      {error}
                    </td>
                  </tr>
                ) : transactions.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-[#6B7280] text-sm">
                      No transactions found.
                    </td>
                  </tr>
                ) : (
                  transactions.map((tx, index) => (
                    <tr
                      key={tx.id}
                      className={`border-b border-[#DDE1E7] hover:bg-[#F4F6F9] cursor-pointer ${
                        index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'
                      }`}
                      onClick={() => {
                        setSelectedTx(tx);
                        setLiveIFMsg(null);
                      }}
                    >
                      <td className="px-4 py-3 text-xs font-mono text-[#6B7280] font-medium">
                        {(pagination.page - 1) * pagination.limit + index + 1}
                      </td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-[#2471A3] text-white">
                          {tx.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm">{tx.payer}</td>
                      <td className="px-4 py-3 text-sm">{tx.recipient}</td>
                      <td className="px-4 py-3 text-sm font-mono">
                        {tx.amount.toLocaleString()}
                      </td>
                      <td className="px-4 py-3">
                        <RiskBadge tier={tx.tier} />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-[#F4F6F9] rounded-full h-2 overflow-hidden">
                            <div
                              className={`h-2 rounded-full transition-all duration-500 ${
                                tx.mlScore >= 0.8
                                  ? 'bg-[#C0392B]'
                                  : tx.mlScore >= 0.6
                                  ? 'bg-[#E8A020]'
                                  : tx.mlScore >= 0.4
                                  ? 'bg-[#2471A3]'
                                  : 'bg-[#2E7D52]'
                              }`}
                              style={{ width: `${Math.min(Math.max(tx.mlScore * 100, 0), 100)}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono">{tx.mlScore.toFixed(2)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge
                          status={tx.smartContractStatus}
                          variant={tx.smartContractStatus === 'BLOCKED' ? 'filled' : 'outline'}
                        />
                      </td>
                      <td className="px-4 py-3">
                        <button className="text-[#1A3C5E] hover:text-[#2E7D52] text-sm font-medium">
                          View
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls (Max 15 items per page) */}
          <div className="border-t border-[#DDE1E7] bg-white px-4 py-3 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm">
            <div className="text-xs sm:text-sm text-[#6B7280]">
              {pagination.total > 0 ? (
                <>
                  Showing{' '}
                  <span className="font-semibold text-[#1C1C1E]">
                    {(pagination.page - 1) * pagination.limit + 1}
                  </span>{' '}
                  to{' '}
                  <span className="font-semibold text-[#1C1C1E]">
                    {Math.min(pagination.page * pagination.limit, pagination.total)}
                  </span>{' '}
                  of{' '}
                  <span className="font-semibold text-[#1C1C1E]">{pagination.total}</span>{' '}
                  transactions
                  <span className="ml-2 text-xs text-[#9CA3AF]">(15 per page)</span>
                </>
              ) : (
                <span>No transactions to display</span>
              )}
            </div>

            <div className="flex items-center gap-1.5">
              {/* First Page */}
              <button
                type="button"
                onClick={() => setCurrentPage(1)}
                disabled={pagination.page <= 1 || loading}
                title="First Page"
                className={`p-1.5 rounded border border-[#DDE1E7] flex items-center justify-center transition-colors ${
                  pagination.page <= 1 || loading
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <ChevronsLeft className="w-4 h-4" />
              </button>

              {/* Prev Page */}
              <button
                type="button"
                onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                disabled={!pagination.has_prev || loading}
                title="Previous Page"
                className={`px-2.5 py-1.5 rounded border border-[#DDE1E7] flex items-center gap-1 text-xs font-medium transition-colors ${
                  !pagination.has_prev || loading
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Prev</span>
              </button>

              {/* Page Number Buttons */}
              <div className="flex items-center gap-1 mx-1">
                {Array.from({ length: pagination.total_pages }, (_, i) => i + 1)
                  .filter(pageNum => {
                    if (pagination.total_pages <= 7) return true;
                    if (pageNum === 1 || pageNum === pagination.total_pages) return true;
                    return Math.abs(pageNum - pagination.page) <= 1;
                  })
                  .reduce<(number | string)[]>((acc, pageNum, idx, arr) => {
                    if (idx > 0 && pageNum - (arr[idx - 1] as number) > 1) {
                      acc.push('...');
                    }
                    acc.push(pageNum);
                    return acc;
                  }, [])
                  .map((item, idx) => {
                    if (item === '...') {
                      return (
                        <span key={`ellipsis-${idx}`} className="px-2 py-1 text-xs text-[#9CA3AF]">
                          ...
                        </span>
                      );
                    }
                    const pageNum = item as number;
                    const isActive = pageNum === pagination.page;
                    return (
                      <button
                        key={pageNum}
                        type="button"
                        onClick={() => setCurrentPage(pageNum)}
                        disabled={loading}
                        className={`min-w-[32px] h-8 px-2 rounded text-xs font-semibold transition-colors ${
                          isActive
                            ? 'bg-[#1A3C5E] text-white shadow-sm'
                            : 'border border-[#DDE1E7] text-[#374151] hover:bg-[#F4F6F9]'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
              </div>

              {/* Next Page */}
              <button
                type="button"
                onClick={() => setCurrentPage(prev => Math.min(pagination.total_pages, prev + 1))}
                disabled={!pagination.has_next || loading}
                title="Next Page"
                className={`px-2.5 py-1.5 rounded border border-[#DDE1E7] flex items-center gap-1 text-xs font-medium transition-colors ${
                  !pagination.has_next || loading
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>

              {/* Last Page */}
              <button
                type="button"
                onClick={() => setCurrentPage(pagination.total_pages)}
                disabled={pagination.page >= pagination.total_pages || loading}
                title="Last Page"
                className={`p-1.5 rounded border border-[#DDE1E7] flex items-center justify-center transition-colors ${
                  pagination.page >= pagination.total_pages || loading
                    ? 'text-[#9CA3AF] bg-[#F4F6F9] cursor-not-allowed'
                    : 'text-[#374151] hover:bg-[#F4F6F9] hover:text-[#1A3C5E]'
                }`}
              >
                <ChevronsRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Hourly volume */}
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
            <h3 className="font-bold text-lg mb-4">Transaction Volume (Hourly)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={hourlyVolume}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="hour" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="today" fill="#2471A3" name="Today" />
                <Bar dataKey="average" fill="#E8A020" name="7-Day Avg" />
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Amount distribution */}
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
            <h3 className="font-bold text-lg mb-4">Amount Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={amountDistribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#2E7D52" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>

      {/* Transaction Detail Panel */}
      {selectedTx && (
        <div className="fixed inset-0 bg-black/50 z-50 flex justify-end">
          <div className="w-[480px] bg-white h-full overflow-y-auto shadow-2xl">
            <div className="sticky top-0 bg-white border-b border-[#DDE1E7] p-6 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-xl">Transaction Details</h2>
                <p className="text-sm font-medium text-[#6B7280]">{selectedTx.type} Disbursement</p>
              </div>
              <button onClick={() => setSelectedTx(null)} className="p-2 hover:bg-[#F4F6F9] rounded">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Transaction info */}
              <div className="bg-[#F4F6F9] rounded-lg p-4 space-y-2">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-[#6B7280]">Type:</span>
                    <p className="font-medium">{selectedTx.type}</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">Amount:</span>
                    <p className="font-bold">KES {selectedTx.amount.toLocaleString()}</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">Payer:</span>
                    <p className="font-medium">{selectedTx.payer}</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">Recipient:</span>
                    <p className="font-medium">{selectedTx.recipient}</p>
                  </div>
                  <div className="col-span-2">
                    <span className="text-[#6B7280]">Timestamp:</span>
                    <p className="font-mono text-xs">{selectedTx.timestamp}</p>
                  </div>
                </div>
              </div>

              {/* Risk score */}
              <div>
                <h3 className="font-bold text-sm mb-3">Risk Score</h3>
                <div className="flex items-center gap-3 mb-4">
                  <div className="flex-1 bg-[#F4F6F9] rounded-full h-4 overflow-hidden">
                    <div
                      className={`h-4 rounded-full transition-all duration-500 ${
                        selectedTx.mlScore >= 0.8
                          ? 'bg-[#C0392B]'
                          : selectedTx.mlScore >= 0.6
                          ? 'bg-[#E8A020]'
                          : selectedTx.mlScore >= 0.4
                          ? 'bg-[#2471A3]'
                          : 'bg-[#2E7D52]'
                      }`}
                      style={{ width: `${Math.min(Math.max(selectedTx.mlScore * 100, 0), 100)}%` }}
                    />
                  </div>
                  <span className="font-mono font-bold text-lg">{selectedTx.mlScore.toFixed(2)}</span>
                </div>
                <RiskBadge tier={selectedTx.tier} />
              </div>

              {/* Model scores */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-sm">Model Breakdown &amp; Weights</h3>
                  <button
                    onClick={() => handleTestLiveIF(selectedTx.id)}
                    disabled={actionLoading}
                    className="text-xs bg-[#1A3C5E] hover:bg-[#2E7D52] text-white px-2.5 py-1 rounded font-medium transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {actionLoading ? 'Scoring...' : 'Run Live Models (IF + AE + LSTM)'}
                  </button>
                </div>

                {liveIFMsg && (
                  <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg text-xs">
                    <div className="flex items-center justify-between font-bold text-[#1A3C5E] mb-1">
                      <span>Live Model Inference (joblib):</span>
                      <span className="font-mono">{liveIFMsg.latency} ms</span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <span className="font-mono font-bold text-xs">IF: {liveIFMsg.score.toFixed(4)}</span>
                      {liveIFMsg.aeScore !== undefined && (
                        <span className="font-mono font-bold text-xs text-[#2471A3]">
                          AE: {liveIFMsg.aeScore.toFixed(4)}
                        </span>
                      )}
                      {liveIFMsg.lstmScore !== undefined && (
                        <span className="font-mono font-bold text-xs text-[#8E44AD]">
                          LSTM: {liveIFMsg.lstmScore.toFixed(4)}
                        </span>
                      )}
                      {liveIFMsg.ensembleScore !== undefined && (
                        <span className="font-mono font-bold text-xs text-[#2E7D52]">
                          Composite: {liveIFMsg.ensembleScore.toFixed(4)}
                        </span>
                      )}
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[#1A3C5E] text-white">
                        {liveIFMsg.tier}
                      </span>
                    </div>
                    {liveIFMsg.reasons.length > 0 && (
                      <div className="text-[11px] text-[#78350F] bg-amber-50 p-1.5 rounded border border-amber-200">
                        {liveIFMsg.reasons.join(' • ')}
                      </div>
                    )}
                  </div>
                )}

                <div className="space-y-2">
                  {Object.entries(selectedTx.modelScores)
                    .filter(([model]) => model !== 'GNN')
                    .map(([model, score]) => {
                    const weightMap: Record<string, string> = {
                      IF: '40%',
                      AE: '30%',
                      LSTM: '30%',
                    };
                    return (
                      <div key={model}>
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-mono">{model}</span>
                            {weightMap[model] && (
                              <span className="text-[10px] font-mono bg-gray-100 text-[#475569] px-1.5 py-0.5 rounded">
                                Weight: {weightMap[model]}
                              </span>
                            )}
                          </div>
                          <span className="text-sm font-mono">{score.toFixed(2)}</span>
                        </div>
                        <div className="w-full bg-[#F4F6F9] rounded-full h-2 overflow-hidden">
                          <div
                            className="bg-[#2471A3] h-2 rounded-full transition-all duration-500"
                            style={{ width: `${Math.min(Math.max(score * 100, 0), 100)}%` }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Anomaly features */}
              {selectedTx.anomalyFeatures.length > 0 && (
                <div>
                  <h3 className="font-bold text-sm mb-3">Anomaly Features</h3>
                  <div className="space-y-2">
                    {selectedTx.anomalyFeatures.map((feature, index) => (
                      <div key={index} className="bg-[#FEF3E2] border border-[#E8A020] rounded-lg p-3">
                        <p className="text-sm text-[#1C1C1E]">{feature}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Smart contract */}
              <div className="bg-[#F4F6F9] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-2">Smart Contract Evaluation</h3>
                <div className="flex items-center gap-2">
                  {selectedTx.smartContractStatus === 'PASSED' ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-[#2E7D52]" />
                      <span className="text-sm text-[#2E7D52] font-medium">PASSED</span>
                    </>
                  ) : (
                    <>
                      <Lock className="w-4 h-4 text-[#C0392B]" />
                      <span className="text-sm text-[#C0392B] font-medium">BLOCKED</span>
                    </>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => handleInvestigate(selectedTx.id)}
                  disabled={actionLoading}
                  className="flex-1 bg-[#1A3C5E] text-white px-4 py-2 rounded-lg font-medium hover:bg-[#2E7D52] transition-colors disabled:opacity-50"
                >
                  {actionLoading ? 'Flagging...' : 'Investigate'}
                </button>
                <button
                  onClick={() => handleClear(selectedTx.id)}
                  disabled={actionLoading}
                  className="px-4 py-2 border border-[#DDE1E7] rounded-lg font-medium hover:bg-[#F4F6F9] transition-colors disabled:opacity-50"
                >
                  {actionLoading ? 'Clearing...' : 'Clear'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Simulate Ingestion Modal */}
      {isIngestModalOpen && (
        <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-[#DDE1E7]">
            {/* Modal Header */}
            <div className="sticky top-0 bg-white border-b border-[#DDE1E7] px-6 py-4 flex items-center justify-between z-10">
              <div>
                <div className="flex items-center gap-2">
                  <div className="p-1.5 bg-blue-50 text-[#1A3C5E] rounded-lg">
                    <Zap className="w-5 h-5 text-[#2471A3]" />
                  </div>
                  <h2 className="font-bold text-lg text-[#1C1C1E]">Simulate Transaction Ingestion</h2>
                </div>
                <p className="text-xs text-[#6B7280] mt-0.5">
                  Real-time pipeline ingestion with asynchronous 3-model scoring (IF 40%, AE 30%, LSTM 30%)
                </p>
              </div>
              <button
                onClick={() => setIsIngestModalOpen(false)}
                className="p-1.5 hover:bg-[#F4F6F9] rounded-lg text-[#6B7280] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Presets */}
              <div>
                <label className="block text-xs font-semibold text-[#475569] uppercase tracking-wider mb-2">
                  Quick Simulation Presets
                </label>
                <div className="grid grid-cols-3 gap-3">
                  <button
                    type="button"
                    onClick={() => applyPreset('NORMAL')}
                    className="p-3 text-left border rounded-lg hover:border-[#2E7D52] hover:bg-emerald-50/40 transition-all cursor-pointer group"
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-[#2E7D52] mb-1">
                      <CheckCircle className="w-3.5 h-3.5" />
                      Normal Subsidy
                    </div>
                    <p className="text-[11px] text-[#6B7280]">KES 48,750 daytime grant disbursement (Low Risk)</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => applyPreset('SURGE')}
                    className="p-3 text-left border rounded-lg hover:border-[#C0392B] hover:bg-red-50/40 transition-all cursor-pointer group"
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-[#C0392B] mb-1">
                      <AlertTriangle className="w-3.5 h-3.5" />
                      Midnight Surge
                    </div>
                    <p className="text-[11px] text-[#6B7280]">KES 2,000,000 at 02:30 AM off-hours drain (Critical)</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => applyPreset('GHOST')}
                    className="p-3 text-left border rounded-lg hover:border-[#E8A020] hover:bg-amber-50/40 transition-all cursor-pointer group"
                  >
                    <div className="flex items-center gap-1.5 font-semibold text-xs text-[#E8A020] mb-1">
                      <Activity className="w-3.5 h-3.5" />
                      Ghost Enrollment Spike
                    </div>
                    <p className="text-[11px] text-[#6B7280]">Inflated KES 980,000 procurement invoice (High Risk)</p>
                  </button>
                </div>
              </div>

              {/* Ingestion Form */}
              <form onSubmit={handleSimulateIngest} className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-medium text-[#475569] mb-1">Target School</label>
                    <select
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm bg-white"
                      value={ingestForm.school_id}
                      onChange={(e) => setIngestForm({ ...ingestForm, school_id: e.target.value })}
                      required
                    >
                      {availableSchools.map((s) => (
                        <option key={s.id} value={s.id}>
                          {s.name} ({s.enrollment} students)
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#475569] mb-1">Transaction Type</label>
                    <select
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm bg-white"
                      value={ingestForm.type}
                      onChange={(e) => setIngestForm({ ...ingestForm, type: e.target.value })}
                    >
                      <option value="SUBSIDY">Government Subsidy Disbursement</option>
                      <option value="PROCUREMENT">Supplier Procurement Payment</option>
                      <option value="MPESA">M-Pesa Direct Feeding Fee</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#475569] mb-1">Amount (KES)</label>
                    <input
                      type="number"
                      step="any"
                      min="1"
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm"
                      value={ingestForm.amount}
                      onChange={(e) => setIngestForm({ ...ingestForm, amount: e.target.value })}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#475569] mb-1">Payment Method</label>
                    <select
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm bg-white"
                      value={ingestForm.payment_method}
                      onChange={(e) => setIngestForm({ ...ingestForm, payment_method: e.target.value })}
                    >
                      <option value="BANK_TRANSFER">Bank Wire Transfer</option>
                      <option value="MPESA">M-Pesa Bulk Disburse</option>
                      <option value="CHEQUE">Bankers Cheque</option>
                      <option value="SYSTEM">System Ledger Clearing</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#475569] mb-1">Transacted Timestamp</label>
                    <input
                      type="datetime-local"
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm"
                      value={ingestForm.transacted_at}
                      onChange={(e) => setIngestForm({ ...ingestForm, transacted_at: e.target.value })}
                      required
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#475569] mb-1">Reference Number (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. MP-2026-X99"
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm"
                      value={ingestForm.reference_no}
                      onChange={(e) => setIngestForm({ ...ingestForm, reference_no: e.target.value })}
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-xs font-medium text-[#475569] mb-1">Description / Memo</label>
                    <input
                      type="text"
                      className="w-full border border-[#DDE1E7] rounded px-3 py-2 text-sm"
                      value={ingestForm.description}
                      onChange={(e) => setIngestForm({ ...ingestForm, description: e.target.value })}
                      required
                    />
                  </div>
                </div>

                {ingestError && (
                  <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-[#C0392B]">
                    {ingestError}
                  </div>
                )}

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsIngestModalOpen(false)}
                    className="px-4 py-2 border border-[#DDE1E7] rounded-lg text-sm text-[#475569] hover:bg-[#F4F6F9]"
                  >
                    Close
                  </button>
                  <button
                    type="submit"
                    disabled={ingestStatus === 'QUEUED' || ingestStatus === 'EVALUATING'}
                    className="flex items-center gap-2 bg-[#1A3C5E] hover:bg-[#2E7D52] text-white px-5 py-2 rounded-lg text-sm font-semibold transition-colors disabled:opacity-50 cursor-pointer"
                  >
                    {ingestStatus === 'QUEUED' || ingestStatus === 'EVALUATING' ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        Evaluating Anomaly Models...
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4" />
                        Ingest &amp; Score Transaction
                      </>
                    )}
                  </button>
                </div>
              </form>

              {/* Progress & Scoring Result Card */}
              {(ingestStatus === 'QUEUED' || ingestStatus === 'EVALUATING') && (
                <div className="p-4 bg-purple-50 border border-purple-200 rounded-lg space-y-2 animate-pulse">
                  <div className="flex items-center justify-between text-xs font-semibold text-[#6B21A8]">
                    <span className="flex items-center gap-1.5">
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Evaluating 3-Model Ensemble (IF 40% + AE 30% + LSTM 30%)...
                    </span>
                    <span className="px-2 py-0.5 rounded bg-purple-200 text-purple-900 font-mono">EVALUATING</span>
                  </div>
                  <p className="text-[11px] text-[#6B7280]">
                    Transaction submitted with status PENDING and queued for background feature extraction &amp; scoring.
                  </p>
                </div>
              )}

              {ingestStatus === 'SCORED' && ingestResult && (
                <div className={`p-4 rounded-xl border ${
                  ingestResult.risk_tier === 'CRITICAL' ? 'bg-red-50 border-red-300' :
                  ingestResult.risk_tier === 'HIGH' ? 'bg-amber-50 border-amber-300' :
                  ingestResult.risk_tier === 'MEDIUM' ? 'bg-blue-50 border-blue-300' :
                  'bg-emerald-50 border-emerald-300'
                }`}>
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[#1C1C1E]">
                        Scoring Complete
                      </span>
                      <RiskBadge tier={ingestResult.risk_tier} />
                      <span className="text-xs px-2 py-0.5 rounded bg-white font-mono border">
                        Status: <b>{ingestResult.status}</b>
                      </span>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-[#6B7280]">Composite Score: </span>
                      <span className="font-mono font-bold text-sm">
                        {ingestResult.risk_score?.toFixed(4) || ingestResult.mlScore?.toFixed(4)}
                      </span>
                    </div>
                  </div>

                  {/* Model Scores Pill Breakdown */}
                  {ingestResult.modelScores && (
                    <div className="grid grid-cols-3 gap-2 mb-3">
                      <div className="bg-white/80 p-2 rounded border text-center">
                        <div className="text-[10px] text-[#6B7280] font-mono">Isolation Forest (40%)</div>
                        <div className="font-mono font-bold text-xs">{ingestResult.modelScores.IF?.toFixed(4)}</div>
                      </div>
                      <div className="bg-white/80 p-2 rounded border text-center">
                        <div className="text-[10px] text-[#6B7280] font-mono">Autoencoder (30%)</div>
                        <div className="font-mono font-bold text-xs">{ingestResult.modelScores.AE?.toFixed(4)}</div>
                      </div>
                      <div className="bg-white/80 p-2 rounded border text-center">
                        <div className="text-[10px] text-[#6B7280] font-mono">LSTM Autoencoder (30%)</div>
                        <div className="font-mono font-bold text-xs">{ingestResult.modelScores.LSTM?.toFixed(4)}</div>
                      </div>
                    </div>
                  )}

                  {/* Alert notification message */}
                  {(ingestResult.risk_tier === 'HIGH' || ingestResult.risk_tier === 'CRITICAL') && (
                    <div className="p-2.5 bg-white/90 rounded border border-red-200 text-xs text-[#991B1B] flex items-start gap-2">
                      <ShieldAlert className="w-4 h-4 text-[#C0392B] flex-shrink-0 mt-0.5" />
                      <div>
                        <b>Automated Alert Generated:</b> Record added to fraud alerts and sent to all active investigators.
                        {ingestResult.risk_tier === 'CRITICAL' && (
                          <span className="block mt-0.5 text-[#B91C1C] font-semibold">
                            Critical severity reached &mdash; transaction status automatically updated to FLAGGED.
                          </span>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
