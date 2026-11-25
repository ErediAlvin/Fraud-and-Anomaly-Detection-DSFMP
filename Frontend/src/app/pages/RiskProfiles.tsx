import { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { RiskBadge } from '../components/RiskBadge';
import { StatusBadge } from '../components/StatusBadge';
import { StatCard } from '../components/StatCard';
import {
  Shield,
  AlertTriangle,
  Eye,
  X,
  RefreshCw,
  CheckCircle,
  Clock,
  Activity,
  Sliders,
} from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
} from 'recharts';
import { api } from '../lib/api';

export function RiskProfiles() {
  const [profiles, setProfiles] = useState<any[]>([]);
  const [stats, setStats] = useState({
    monitoredCount: '0',
    watchlistCount: 0,
    suspendedCount: 0,
    newHighRisk: 0,
  });
  const [radarData, setRadarData] = useState<any[]>([]);
  const [riskHistoryData, setRiskHistoryData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [filters, setFilters] = useState({
    entity_type: 'ALL',
    tier: 'ALL',
    status: 'ALL',
  });
  const [search, setSearch] = useState('');

  // Selected Profile Modal state
  const [selectedProfileId, setSelectedProfileId] = useState<string | null>(null);
  const [detailData, setDetailData] = useState<any | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [modalActionLoading, setModalActionLoading] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    async function loadRiskProfiles() {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.entity_type !== 'ALL') params.append('entity_type', filters.entity_type);
        if (filters.tier !== 'ALL') params.append('tier', filters.tier);
        if (filters.status !== 'ALL') params.append('status', filters.status);
        if (search) params.append('search', search);

        const res = await api.get<any>(`/risk-profiles?${params.toString()}`);
        if (isMounted) {
          setProfiles(res.profiles);
          setStats(res.stats);
          if (res.radarData) setRadarData(res.radarData);
          if (res.riskHistory) setRiskHistoryData(res.riskHistory);
          setError('');
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load risk profiles.');
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(() => {
      loadRiskProfiles();
    }, 250);

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [filters, search]);

  // Open detail modal
  const handleOpenDetail = async (id: string) => {
    setSelectedProfileId(id);
    setActionSuccess(null);
    try {
      setDetailLoading(true);
      const res = await api.get<any>(`/risk-profiles/${id}`);
      setDetailData(res);
    } catch (e) {
      setDetailData(null);
    } finally {
      setDetailLoading(false);
    }
  };

  // Change entity status (CLEAN, WATCHLIST, SUSPENDED)
  const handleChangeStatus = async (newStatus: string) => {
    if (!selectedProfileId) return;
    try {
      setModalActionLoading(true);
      await api.patch(`/risk-profiles/${selectedProfileId}/status`, { status: newStatus });
      setActionSuccess(`Status updated to ${newStatus}`);

      // Update local state
      const nextTier = newStatus === 'SUSPENDED' ? 'CRITICAL' : newStatus === 'WATCHLIST' ? 'HIGH' : 'LOW';
      setProfiles((prev) =>
        prev.map((p) => (p.id === selectedProfileId ? { ...p, status: newStatus, tier: nextTier } : p))
      );
      if (detailData && detailData.profile) {
        setDetailData({
          ...detailData,
          profile: { ...detailData.profile, status: newStatus, tier: nextTier },
        });
      }
    } catch (err: any) {
      alert(err.message || 'Failed to update entity status');
    } finally {
      setModalActionLoading(false);
    }
  };

  // Recalculate score
  const handleRecalculate = async () => {
    if (!selectedProfileId) return;
    try {
      setModalActionLoading(true);
      const res = await api.post<any>(`/risk-profiles/${selectedProfileId}/recalculate`);
      const updatedScore = typeof res?.riskScore === 'number' ? res.riskScore : undefined;
      const updatedTier = res?.tier;
      const updatedRadar = res?.radar;
      const updatedLastScored = res?.lastScored;

      if (updatedScore !== undefined) {
        setProfiles((prev) =>
          prev.map((p) =>
            p.id === selectedProfileId
              ? {
                  ...p,
                  riskScore: updatedScore,
                  tier: updatedTier || p.tier,
                  lastScored: updatedLastScored || p.lastScored,
                }
              : p
          )
        );
        setDetailData((prev: any) =>
          prev && prev.profile
            ? {
                ...prev,
                profile: {
                  ...prev.profile,
                  riskScore: updatedScore,
                  tier: updatedTier || prev.profile.tier,
                  lastScored: updatedLastScored || prev.profile.lastScored,
                },
                radar: updatedRadar || prev.radar,
              }
            : prev
        );
      }
      setActionSuccess(res?.message || 'Composite risk score recalculated and refreshed');
    } catch (err: any) {
      alert(err.message || 'Failed to recalculate score');
    } finally {
      setModalActionLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['Entity Risk Profiles']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Summary cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard icon={Shield} label="Total Entities Monitored" value={loading ? '...' : stats.monitoredCount} />
          <StatCard icon={Eye} label="On Watchlist" value={loading ? '...' : stats.watchlistCount} variant="warning" />
          <StatCard
            icon={AlertTriangle}
            label="Suspended Entities"
            value={loading ? '...' : stats.suspendedCount}
            variant="critical"
          />
          <StatCard label="New High Risk (7 days)" value={loading ? '...' : stats.newHighRisk} />
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-4 mb-6 shadow-sm">
          <div className="flex flex-wrap gap-4 items-center">
            <div>
              <label className="block text-xs font-semibold text-[#6B7280] mb-1">Entity Type</label>
              <select
                className="border border-[#DDE1E7] rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-[#1A3C5E]"
                value={filters.entity_type}
                onChange={(e) => setFilters({ ...filters, entity_type: e.target.value })}
              >
                <option value="ALL">All Types</option>
                <option value="SCHOOL">School</option>
                <option value="BENEFICIARY">Student / Beneficiary</option>
                <option value="SUPPLIER">Supplier</option>
                <option value="PAYMENT_ACCOUNT">Payment Account</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[#6B7280] mb-1">Risk Tier</label>
              <select
                className="border border-[#DDE1E7] rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-[#1A3C5E]"
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
                className="border border-[#DDE1E7] rounded-lg px-3 py-1.5 text-sm bg-white focus:outline-none focus:border-[#1A3C5E]"
                value={filters.status}
                onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              >
                <option value="ALL">All Statuses</option>
                <option value="CLEAN">Clean</option>
                <option value="WATCHLIST">Watchlist</option>
                <option value="SUSPENDED">Suspended</option>
              </select>
            </div>

            <div className="flex-1"></div>

            <div className="self-end">
              <input
                type="text"
                placeholder="Search by name or entity ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="border border-[#DDE1E7] rounded-lg px-3 py-1.5 text-sm w-72 focus:outline-none focus:border-[#1A3C5E]"
              />
            </div>
          </div>
        </div>

        {/* Profiles table */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] overflow-hidden mb-6 shadow-sm">
          <div className="p-4 border-b border-[#DDE1E7] bg-[#F8FAFC] flex items-center justify-between">
            <h3 className="font-bold text-sm text-[#1A3C5E]">Monitored Entity Directory</h3>
            <span className="text-xs text-[#6B7280]">{profiles.length} profiles tracked</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase w-12">#</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Entity Name</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">County</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Risk Score</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Tier</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase">Total Alerts</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-[#6B7280] uppercase">Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-sm text-[#6B7280]">
                      Loading risk profiles...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-sm text-[#C0392B] font-medium">
                      {error}
                    </td>
                  </tr>
                ) : profiles.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="text-center py-8 text-sm text-[#6B7280]">
                      No entity risk profiles found matching the filters.
                    </td>
                  </tr>
                ) : (
                  profiles.map((profile, index) => (
                    <tr
                      key={profile.id}
                      className={`border-b border-[#DDE1E7] hover:bg-[#F4F6F9] cursor-pointer transition-colors ${
                        index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'
                      }`}
                      onClick={() => handleOpenDetail(profile.id)}
                    >
                      <td className="px-4 py-3 text-xs font-mono text-[#6B7280] font-medium">{index + 1}</td>
                      <td className="px-4 py-3 text-sm font-semibold text-[#1F2937]">{profile.name}</td>
                      <td className="px-4 py-3 text-xs font-medium text-[#4B5563]">
                        <span className="bg-[#EBF5FB] text-[#1A3C5E] px-2 py-0.5 rounded font-mono">
                          {profile.type}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-[#4B5563]">{profile.county}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          <div className="w-16 bg-[#E5E7EB] rounded-full h-2">
                            <div
                              className={`h-2 rounded-full ${
                                profile.riskScore >= 0.8
                                  ? 'bg-[#C0392B]'
                                  : profile.riskScore >= 0.6
                                  ? 'bg-[#E8A020]'
                                  : 'bg-[#2E7D52]'
                              }`}
                              style={{ width: `${profile.riskScore * 100}%` }}
                            />
                          </div>
                          <span className="text-xs font-mono font-bold">{profile.riskScore.toFixed(2)}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <RiskBadge tier={profile.tier} />
                      </td>
                      <td className="px-4 py-3">
                        <StatusBadge status={profile.status} />
                      </td>
                      <td className="px-4 py-3 text-sm font-mono text-[#1F2937]">{profile.totalAlerts}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleOpenDetail(profile.id);
                          }}
                          className="text-[#1A3C5E] hover:text-[#2E7D52] text-xs font-semibold px-2.5 py-1 rounded bg-[#EBF5FB] hover:bg-[#D4E6F1] transition-colors"
                        >
                          Dossier
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Aggregate Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Risk history */}
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
            <h3 className="font-bold text-base mb-4 text-[#1A3C5E]">90-Day Rolling Risk Progression</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={riskHistoryData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Line type="monotone" dataKey="score" stroke="#C0392B" strokeWidth={2} dot={false} name="Risk Score" />
              </LineChart>
            </ResponsiveContainer>
            <div className="flex gap-4 mt-3 text-xs">
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#C0392B]"></div>
                <span className="text-[#6B7280]">Critical (≥0.80)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#E8A020]"></div>
                <span className="text-[#6B7280]">High (0.60–0.79)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#2471A3]"></div>
                <span className="text-[#6B7280]">Medium (0.40–0.59)</span>
              </div>
              <div className="flex items-center gap-1.5">
                <div className="w-2.5 h-2.5 rounded-full bg-[#2E7D52]"></div>
                <span className="text-[#6B7280]">Low (&lt;0.40)</span>
              </div>
            </div>
          </div>

          {/* Model scores radar */}
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-sm">
            <h3 className="font-bold text-base mb-4 text-[#1A3C5E]">Multi-Model Detection Sensitivity (Radar)</h3>
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#E5E7EB" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: '#374151' }} />
                <PolarRadiusAxis domain={[0, 1]} tick={{ fontSize: 9 }} />
                <Radar name="Sensitivity" dataKey="value" stroke="#1A3C5E" fill="#1A3C5E" fillOpacity={0.4} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      </main>

      {/* ── Individual Entity Dossier Modal ── */}
      {selectedProfileId && (() => {
        const selectedProfile = profiles.find((p) => p.id === selectedProfileId);
        const entityName = detailData?.profile?.name || selectedProfile?.name || 'Loading Entity...';
        return (
          <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl w-full max-w-3xl max-h-[90vh] overflow-y-auto shadow-2xl border border-[#DDE1E7] animate-in fade-in zoom-in duration-150">
              <div className="sticky top-0 bg-white border-b border-[#DDE1E7] px-6 py-4 flex items-center justify-between z-10">
                <div>
                  <h2 className="font-bold text-lg text-[#1A3C5E]">Entity Risk Dossier &amp; Behavioral Breakdown</h2>
                  <p className="text-xs font-medium text-[#6B7280]">Target Subject: {entityName}</p>
                </div>
                <button
                  onClick={() => setSelectedProfileId(null)}
                  className="p-1.5 hover:bg-[#F4F6F9] rounded-lg text-[#6B7280]"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-6 space-y-6">
                {actionSuccess && (
                  <div className="p-3 bg-[#E8F8F0] border border-[#2E7D52] text-[#2E7D52] rounded-lg text-xs font-medium flex items-center gap-2">
                    <CheckCircle className="w-4 h-4" />
                    <span>{actionSuccess}</span>
                  </div>
                )}

                {detailLoading ? (
                  <div className="text-center py-12 text-sm text-[#6B7280]">
                    <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-[#1A3C5E]" />
                    Loading entity dossier...
                  </div>
                ) : detailData && detailData.profile ? (
                  <>
                    {/* Entity Metadata Card */}
                    <div className="bg-[#F8FAFC] rounded-lg p-4 border border-[#E2E8F0]">
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                        <div>
                          <span className="text-[#6B7280] block mb-0.5">Entity Name:</span>
                          <p className="font-bold text-sm text-[#1F2937]">{detailData.profile.name}</p>
                        </div>
                        <div>
                          <span className="text-[#6B7280] block mb-0.5">Type &amp; County:</span>
                          <p className="font-medium text-[#1F2937]">
                            {detailData.profile.entityType} &bull; {detailData.profile.county}
                          </p>
                        </div>
                        <div>
                          <span className="text-[#6B7280] block mb-0.5">Composite Score:</span>
                          <p className="font-mono font-bold text-sm text-[#C0392B]">
                            {typeof detailData.profile.riskScore === 'number'
                              ? detailData.profile.riskScore.toFixed(2)
                              : detailData.profile.riskScore || '0.00'}
                          </p>
                        </div>
                        <div>
                          <span className="text-[#6B7280] block mb-0.5">Current Status:</span>
                          <StatusBadge status={detailData.profile.status} />
                        </div>
                      </div>
                    </div>

                    {/* 4-Model Breakdown & Trend */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="border border-[#E5E7EB] rounded-lg p-4">
                        <h4 className="font-bold text-xs uppercase text-[#6B7280] mb-2 flex items-center gap-1.5">
                          <Sliders className="w-3.5 h-3.5 text-[#1A3C5E]" />
                          4-Model Score Breakdown
                        </h4>
                        <div className="space-y-2.5">
                          {detailData.radar?.map((m: any, idx: number) => (
                            <div key={idx}>
                              <div className="flex justify-between text-xs mb-1">
                                <span className="font-medium text-[#374151]">{m.metric}</span>
                                <span className="font-mono font-bold text-[#1A3C5E]">
                                  {typeof m.value === 'number' ? m.value.toFixed(2) : m.value}
                                </span>
                              </div>
                              <div className="w-full bg-[#E5E7EB] rounded-full h-1.5">
                                <div
                                  className="bg-[#1A3C5E] h-1.5 rounded-full"
                                  style={{ width: `${(m.value || 0) * 100}%` }}
                                />
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>

                      <div className="border border-[#E5E7EB] rounded-lg p-4">
                        <h4 className="font-bold text-xs uppercase text-[#6B7280] mb-2 flex items-center gap-1.5">
                          <Activity className="w-3.5 h-3.5 text-[#1A3C5E]" />
                          Associated Alert History ({detailData.alerts?.length || 0})
                        </h4>
                        <div className="space-y-2 max-h-44 overflow-y-auto pr-1">
                          {detailData.alerts?.length === 0 ? (
                            <p className="text-xs text-[#6B7280] py-4 text-center">No alerts recorded for this entity.</p>
                          ) : (
                            detailData.alerts.map((al: any) => (
                              <div key={al.id} className="p-2 rounded border border-[#E5E7EB] bg-[#F9FAFB] text-xs">
                                <div className="flex items-center justify-between mb-0.5">
                                  <span className="font-semibold text-[#1F2937]">{al.title}</span>
                                  <RiskBadge tier={al.severity} />
                                </div>
                                <div className="text-[11px] text-[#6B7280] flex justify-between">
                                  <span>{al.type}</span>
                                  <span>{al.date}</span>
                                </div>
                              </div>
                            ))
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex flex-wrap gap-3 pt-4 border-t border-[#DDE1E7]">
                      <button
                        onClick={() => handleChangeStatus('WATCHLIST')}
                        disabled={modalActionLoading || detailData.profile.status === 'WATCHLIST'}
                        className="px-4 py-2 bg-[#E8A020] text-white rounded-lg text-xs font-semibold hover:bg-[#C88210] transition-colors disabled:opacity-50"
                      >
                        Place on Watchlist
                      </button>
                      <button
                        onClick={() => handleChangeStatus('SUSPENDED')}
                        disabled={modalActionLoading || detailData.profile.status === 'SUSPENDED'}
                        className="px-4 py-2 bg-[#C0392B] text-white rounded-lg text-xs font-semibold hover:bg-[#962D22] transition-colors disabled:opacity-50"
                      >
                        Suspend Entity
                      </button>
                      <button
                        onClick={() => handleChangeStatus('CLEAN')}
                        disabled={modalActionLoading || detailData.profile.status === 'CLEAN'}
                        className="px-4 py-2 border border-[#2E7D52] text-[#2E7D52] hover:bg-[#E8F8F0] rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        Mark as Clean
                      </button>
                      <div className="flex-1"></div>
                      <button
                        onClick={handleRecalculate}
                        disabled={modalActionLoading}
                        className="px-4 py-2 border border-[#1A3C5E] text-[#1A3C5E] hover:bg-[#EBF5FB] rounded-lg text-xs font-semibold transition-colors flex items-center gap-1.5"
                      >
                        {modalActionLoading && <RefreshCw className="w-3.5 h-3.5 animate-spin" />}
                        Recalculate Score
                      </button>
                    </div>
                  </>
                ) : null}
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
