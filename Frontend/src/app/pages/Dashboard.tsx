import { useState, useEffect } from 'react';
import { StatCard } from '../components/StatCard';
import { RiskBadge } from '../components/RiskBadge';
import { Header } from '../components/Header';
import {
  AlertTriangle,
  Briefcase,
  Shield,
  Activity,
  CheckCircle,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';
import { api } from '../lib/api';

export function Dashboard() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;
    async function loadDashboardData() {
      try {
        const res = await api.get<any>('/dashboard');
        if (isMounted) {
          setData(res);
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load dashboard metrics.');
          setLoading(false);
        }
      }
    }

    loadDashboardData();
    return () => {
      isMounted = false;
    };
  }, []);

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-[#F4F6F9]">
        <div className="text-center">
          <Loader2 className="w-10 h-10 text-[#1A3C5E] animate-spin mx-auto mb-4" />
          <p className="text-[#374151] font-medium text-sm">Loading system metrics...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col">
        <Header breadcrumbs={['Dashboard', 'Overview']} />
        <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6 flex items-center justify-center">
          <div className="bg-red-50 border border-red-200 rounded-xl p-6 max-w-md text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
            <h3 className="text-[#1C1C1E] font-bold text-lg mb-2">Failed to Load Dashboard</h3>
            <p className="text-sm text-[#6B7280] mb-4">{error}</p>
            <button
              onClick={() => {
                setLoading(true);
                setError('');
                // Trigger reload
                api.get<any>('/dashboard')
                  .then((res) => {
                    setData(res);
                    setLoading(false);
                  })
                  .catch((err) => {
                    setError(err.message || 'Failed to load dashboard metrics.');
                    setLoading(false);
                  });
              }}
              className="px-4 py-2 bg-[#1A3C5E] text-white rounded-lg text-sm font-semibold hover:bg-[#234d74] transition-colors"
            >
              Retry Connection
            </button>
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['Dashboard', 'Overview']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Top stat cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-6">
          <StatCard
            icon={Briefcase}
            label="Total Active Cases"
            value={data.stats.active_cases.value}
            trend={
              data.stats.active_cases.trend_value
                ? {
                    value: data.stats.active_cases.trend_value,
                    direction: data.stats.active_cases.trend_direction,
                  }
                : undefined
            }
          />
          <StatCard
            icon={AlertTriangle}
            label="Critical Alerts Today"
            value={data.stats.critical_alerts.value}
            variant="critical"
          />
          <StatCard
            icon={Shield}
            label="High Risk Entities"
            value={data.stats.high_risk_entities.value}
            trend={
              data.stats.high_risk_entities.trend_value
                ? {
                    value: data.stats.high_risk_entities.trend_value,
                    direction: data.stats.high_risk_entities.trend_direction,
                  }
                : undefined
            }
          />
          <StatCard
            icon={Activity}
            label="Transactions Scored Today"
            value={data.stats.transactions_scored.value}
          />
          <StatCard
            icon={CheckCircle}
            label="False Positive Rate"
            value={data.stats.false_positive_rate.value}
            trend={
              data.stats.false_positive_rate.trend_value
                ? {
                    value: data.stats.false_positive_rate.trend_value,
                    direction: data.stats.false_positive_rate.trend_direction,
                  }
                : undefined
            }
          />
          <StatCard
            icon={TrendingUp}
            label="Models Active"
            value={data.stats.models_active.value}
          />
        </div>

        {/* Main content area */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left column - Live Alert Feed */}
          <div className="lg:col-span-5 bg-white rounded-lg border border-[#DDE1E7] p-6">
            <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">Live Alert Feed</h3>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {data.recent_alerts.length === 0 ? (
                <div className="p-8 text-center text-sm text-[#6B7280]">
                  No recent alerts detected.
                </div>
              ) : (
                data.recent_alerts.map((alert: any) => (
                  <div
                    key={alert.id}
                    className="p-3 border border-[#DDE1E7] rounded-lg hover:bg-[#F4F6F9] cursor-pointer transition-colors"
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <RiskBadge tier={alert.tier} />
                        <span className="text-xs text-[#6B7280] font-medium uppercase tracking-wider">{alert.type}</span>
                      </div>
                      <span className="text-xs text-[#6B7280]">{alert.time}</span>
                    </div>
                    <p className="font-semibold text-sm text-[#1C1C1E]">{alert.entity}</p>
                    <p className="text-[10px] text-[#2471A3] font-medium mt-0.5">High Priority Flag</p>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Center column */}
          <div className="lg:col-span-4 space-y-6">
            {/* Risk Distribution Chart */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
              <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">Risk Distribution</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={data.risk_distribution}
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    dataKey="value"
                    labelLine={false}
                    label={({ name, percent }) => percent > 0 ? `${name} (${(percent * 100).toFixed(0)}%)` : ''}
                  >
                    {data.risk_distribution.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value} Alerts`, 'Volume']} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* County Heatmap */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
              <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">County Risk Concentration</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={data.county_risk}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#6B7280' }} />
                  <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} />
                  <Tooltip formatter={(value) => [`${value} Alerts`, 'Count']} />
                  <Bar dataKey="alerts" fill="#C0392B" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Right column */}
          <div className="lg:col-span-3 space-y-6">
            {/* SOB/COB Status */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
              <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">SOB / COB Status</h3>
              <div className="space-y-3.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#6B7280]">Today's SOB</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${data.sob_cob_status.sob_completed ? 'bg-emerald-50 text-[#2E7D52]' : 'bg-red-50 text-[#C0392B]'}`}>
                    {data.sob_cob_status.sob_completed ? `COMPLETED (${data.sob_cob_status.sob_time || 'N/A'})` : 'PENDING'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#6B7280]">Today's COB</span>
                  <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${data.sob_cob_status.cob_completed ? 'bg-emerald-50 text-[#2E7D52]' : 'bg-gray-100 text-[#6B7280]'}`}>
                    {data.sob_cob_status.cob_completed ? `COMPLETED (${data.sob_cob_status.cob_time || 'N/A'})` : 'SCHEDULED (18:00)'}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#6B7280]">Last Retrain</span>
                  <span className="text-xs font-mono font-medium text-[#374151]">{data.sob_cob_status.last_retrain}</span>
                </div>
              </div>
            </div>

            {/* Top 5 Flagged Entities */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
              <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">Top Flagged Entities</h3>
              <div className="space-y-4">
                {data.top_flagged_entities.length === 0 ? (
                  <div className="text-center py-4 text-xs text-[#6B7280]">
                    No flagged entities found.
                  </div>
                ) : (
                  data.top_flagged_entities.map((entity: any, index: number) => (
                    <div key={index} className="space-y-1.5">
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0 pr-2">
                          <p className="text-sm font-semibold text-[#1C1C1E] truncate">{entity.name}</p>
                          <p className="text-[10px] text-[#6B7280] font-medium tracking-wide uppercase">{entity.type}</p>
                        </div>
                        <RiskBadge tier={entity.tier} />
                      </div>
                      <div className="w-full bg-[#F4F6F9] rounded-full h-1.5">
                        <div
                          className="bg-[#C0392B] h-1.5 rounded-full transition-all duration-500"
                          style={{ width: `${entity.score * 100}%` }}
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Blockchain Sync Status */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
              <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">Blockchain Sync</h3>
              <div className="space-y-2.5">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#6B7280]">Status</span>
                  <span className="flex items-center gap-1.5">
                    <span className={`w-2 h-2 rounded-full ${data.blockchain_sync.status === 'HEALTHY' ? 'bg-[#2E7D52]' : 'bg-[#E8A020]'}`}></span>
                    <span className="text-xs font-bold text-[#374151]">{data.blockchain_sync.status}</span>
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-[#6B7280]">Last Sync</span>
                  <span className="text-xs font-mono text-[#374151]">{data.blockchain_sync.last_sync}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 30-day trend */}
        <div className="mt-6 bg-white rounded-lg border border-[#DDE1E7] p-6">
          <h3 className="font-bold text-lg mb-4 text-[#1C1C1E]">30-Day Alert Trend</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.trend_data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#6B7280' }} />
              <YAxis tick={{ fontSize: 11, fill: '#6B7280' }} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line type="monotone" dataKey="CRITICAL" stroke="#C0392B" strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="HIGH" stroke="#E8A020" strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="MEDIUM" stroke="#2471A3" strokeWidth={2.5} dot={false} />
              <Line type="monotone" dataKey="LOW" stroke="#2E7D52" strokeWidth={2.5} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </main>
    </div>
  );
}
