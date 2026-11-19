import { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { RiskBadge } from '../components/RiskBadge';
import { StatCard } from '../components/StatCard';
import { Users, AlertTriangle, UserX, Copy, X, CheckCircle } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { api } from '../lib/api';

interface Student {
  id: string;
  name: string;
  school: string;
  county: string;
  enrollmentDate: string;
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';
  duplicateScore: number;
  crossSchool: boolean;
  attendanceRatio: number;
  blockchainVerified: boolean;
}

export function BeneficiaryMonitor() {
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [stats, setStats] = useState({
    totalEnrolled: '0',
    flaggedSuspicious: 0,
    confirmedGhosts: 0,
    duplicateMatches: 0
  });
  const [enrollmentTrend, setEnrollmentTrend] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filters, setFilters] = useState({
    county: 'ALL',
    tier: 'ALL',
  });
  const [search, setSearch] = useState('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [actionLoading, setActionLoading] = useState(false);

  const handleFlag = async (studentId: string) => {
    try {
      setActionLoading(true);
      await api.post(`/beneficiaries/${studentId}/flag`);
      setRefreshTrigger(prev => prev + 1);
      setSelectedStudent(null);
    } catch (err: any) {
      alert(err.message || 'Failed to flag student.');
    } finally {
      setActionLoading(false);
    }
  };

  const handleClear = async (studentId: string) => {
    try {
      setActionLoading(true);
      await api.post(`/beneficiaries/${studentId}/clear`);
      setRefreshTrigger(prev => prev + 1);
      setSelectedStudent(null);
    } catch (err: any) {
      alert(err.message || 'Failed to clear student risk.');
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    let isMounted = true;
    async function loadBeneficiaries() {
      try {
        setLoading(true);
        const params = new URLSearchParams();
        if (filters.county !== 'ALL') params.append('county', filters.county);
        if (filters.tier !== 'ALL') params.append('tier', filters.tier);
        if (search) params.append('search', search);

        const res = await api.get<any>(`/beneficiaries?${params.toString()}`);
        if (isMounted) {
          setStudents(res.students);
          setStats(res.stats);
          setEnrollmentTrend(res.enrollment_trend);
          setError('');
          setLoading(false);
        }
      } catch (err: any) {
        if (isMounted) {
          setError(err.message || 'Failed to load beneficiaries.');
          setLoading(false);
        }
      }
    }

    const timer = setTimeout(() => {
      loadBeneficiaries();
    }, 300); // Debounce typing

    return () => {
      isMounted = false;
      clearTimeout(timer);
    };
  }, [filters, search, refreshTrigger]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['Beneficiary Monitor']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Summary cards */}
        <div className="grid grid-cols-4 gap-4 mb-6">
          <StatCard icon={Users} label="Total Enrolled Students" value={loading ? '...' : stats.totalEnrolled} />
          <StatCard
            icon={AlertTriangle}
            label="Flagged as Suspicious"
            value={loading ? 0 : stats.flaggedSuspicious}
            variant="warning"
          />
          <StatCard
            icon={UserX}
            label="Confirmed Ghost Beneficiaries"
            value={loading ? 0 : stats.confirmedGhosts}
            variant="critical"
          />
          <StatCard icon={Copy} label="Duplicate Identity Matches" value={loading ? 0 : stats.duplicateMatches} />
        </div>

        {/* Filters */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div>
              <label className="block text-xs text-[#6B7280] mb-1">County</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm"
                value={filters.county}
                onChange={(e) => setFilters({ ...filters, county: e.target.value })}
              >
                <option value="ALL">All Counties</option>
                <option value="Nairobi">Nairobi</option>
                <option value="Mombasa">Mombasa</option>
                <option value="Kisumu">Kisumu</option>
              </select>
            </div>

            <div>
              <label className="block text-xs text-[#6B7280] mb-1">Risk Tier</label>
              <select
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm"
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

            <div className="flex-1"></div>

            <div className="self-end">
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by student name or ID..."
                className="border border-[#DDE1E7] rounded px-3 py-1.5 text-sm w-64"
              />
            </div>
          </div>
        </div>

        {/* Students table */}
        <div className="bg-white rounded-lg border border-[#DDE1E7] overflow-hidden mb-6">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-[#F4F6F9] border-b border-[#DDE1E7]">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-[#6B7280] uppercase tracking-wide w-12">
                    #
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Name
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    School
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    County
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Risk Tier
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Duplicate Score
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Cross-School
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Attendance
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-medium text-[#6B7280] uppercase tracking-wide">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-[#6B7280] text-sm">
                      Loading beneficiaries...
                    </td>
                  </tr>
                ) : error ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-[#C0392B] text-sm font-medium">
                      {error}
                    </td>
                  </tr>
                ) : students.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="text-center py-8 text-[#6B7280] text-sm">
                      No beneficiaries found.
                    </td>
                  </tr>
                ) : (
                  students.map((student, index) => (
                    <tr
                      key={student.id}
                      className={`border-b border-[#DDE1E7] hover:bg-[#F4F6F9] cursor-pointer ${
                        index % 2 === 0 ? 'bg-white' : 'bg-[#FAFAFA]'
                      }`}
                      onClick={() => setSelectedStudent(student)}
                    >
                      <td className="px-4 py-3 text-xs font-mono text-[#6B7280] font-medium">{index + 1}</td>
                      <td className="px-4 py-3 text-sm font-medium">{student.name}</td>
                      <td className="px-4 py-3 text-sm">{student.school}</td>
                      <td className="px-4 py-3 text-sm">{student.county}</td>
                      <td className="px-4 py-3">
                        <RiskBadge tier={student.tier} />
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`text-sm font-mono ${
                            student.duplicateScore > 0.7 ? 'text-[#C0392B]' : 'text-[#6B7280]'
                          }`}
                        >
                          {student.duplicateScore.toFixed(2)}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {student.crossSchool && (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#C0392B] text-white">
                            YES
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {(student.attendanceRatio * 100).toFixed(0)}%
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
        </div>

        {/* Charts */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Enrollment trend */}
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
            <h3 className="font-bold text-lg mb-4">90-Day Enrollment Trend</h3>
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={enrollmentTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Line type="monotone" dataKey="enrollments" stroke="#2471A3" strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* School heatmap placeholder */}
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6">
            <h3 className="font-bold text-lg mb-4">School-Level Risk Heatmap</h3>
            <div className="grid grid-cols-5 gap-2">
              {Array.from({ length: 25 }, (_, i) => {
                const risk = Math.random();
                const color =
                  risk > 0.7
                    ? 'bg-[#C0392B]'
                    : risk > 0.5
                    ? 'bg-[#E8A020]'
                    : risk > 0.3
                    ? 'bg-[#2471A3]'
                    : 'bg-[#2E7D52]';
                return (
                  <div
                    key={i}
                    className={`aspect-square ${color} rounded opacity-80 hover:opacity-100 cursor-pointer`}
                    title={`School ${i + 1}`}
                  ></div>
                );
              })}
            </div>
          </div>
        </div>
      </main>

      {/* Student Profile Modal */}
      {selectedStudent && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
          <div className="bg-white rounded-lg w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
            <div className="sticky top-0 bg-white border-b border-[#DDE1E7] p-6 flex items-center justify-between">
              <div>
                <h2 className="font-bold text-xl">Student Profile</h2>
                <p className="text-sm font-medium text-[#6B7280]">{selectedStudent.name}</p>
              </div>
              <button
                onClick={() => setSelectedStudent(null)}
                className="p-2 hover:bg-[#F4F6F9] rounded"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-6">
              {/* Student details */}
              <div className="bg-[#F4F6F9] rounded-lg p-4 space-y-2">
                <h3 className="font-bold text-sm mb-3">Student Details</h3>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-[#6B7280]">Name:</span>
                    <p className="font-medium">{selectedStudent.name}</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">Record Status:</span>
                    <p className="font-medium text-[#1A3C5E]">Registered Beneficiary</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">School:</span>
                    <p className="font-medium">{selectedStudent.school}</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">County:</span>
                    <p className="font-medium">{selectedStudent.county}</p>
                  </div>
                  <div>
                    <span className="text-[#6B7280]">Enrollment Date:</span>
                    <p>{selectedStudent.enrollmentDate}</p>
                  </div>
                </div>
              </div>

              {/* Risk score */}
              <div>
                <h3 className="font-bold text-sm mb-3">Risk Assessment</h3>
                <div className="flex items-center gap-4">
                  <RiskBadge tier={selectedStudent.tier} />
                  <div className="flex-1">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm">Duplicate Score</span>
                      <span className="text-sm font-mono">
                        {selectedStudent.duplicateScore.toFixed(2)}
                      </span>
                    </div>
                    <div className="w-full bg-[#F4F6F9] rounded-full h-2">
                      <div
                        className={`h-2 rounded-full ${
                          selectedStudent.duplicateScore > 0.7 ? 'bg-[#C0392B]' : 'bg-[#2471A3]'
                        }`}
                        style={{ width: `${selectedStudent.duplicateScore * 100}%` }}
                      />
                    </div>
                  </div>
                </div>
              </div>

              {/* Attendance */}
              <div className="bg-[#F4F6F9] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-3">30-Day Attendance</h3>
                <div className="flex items-center gap-3">
                  <div className="flex-1 bg-white rounded-full h-4">
                    <div
                      className="bg-[#2E7D52] h-4 rounded-full"
                      style={{ width: `${selectedStudent.attendanceRatio * 100}%` }}
                    />
                  </div>
                  <span className="font-bold">{(selectedStudent.attendanceRatio * 100).toFixed(0)}%</span>
                </div>
              </div>

              {/* Blockchain */}
              <div className="bg-[#F4F6F9] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-2">Blockchain Verification</h3>
                <div className="flex items-center gap-2">
                  {selectedStudent.blockchainVerified ? (
                    <>
                      <CheckCircle className="w-4 h-4 text-[#2E7D52]" />
                      <span className="text-sm text-[#2E7D52] font-medium">VERIFIED</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-4 h-4 text-[#C0392B]" />
                      <span className="text-sm text-[#C0392B] font-medium">UNVERIFIED</span>
                    </>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <button
                  onClick={() => handleFlag(selectedStudent.id)}
                  disabled={actionLoading}
                  className="flex-1 bg-[#E8A020] text-white px-4 py-2 rounded-lg font-medium hover:bg-[#C0392B] transition-colors disabled:opacity-50"
                >
                  {actionLoading ? 'Flagging...' : 'Flag for Review'}
                </button>
                <button
                  onClick={() => handleClear(selectedStudent.id)}
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
    </div>
  );
}
