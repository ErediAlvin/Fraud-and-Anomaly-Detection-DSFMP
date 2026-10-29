import React, { useState, useEffect } from 'react';
import { 
  Play, 
  RotateCcw, 
  CheckCircle2, 
  AlertTriangle, 
  ShieldAlert, 
  Clock, 
  DollarSign, 
  Zap, 
  Cpu, 
  Layers, 
  ChevronRight,
  Info
} from 'lucide-react';
import { api } from '../lib/api';

interface Preset {
  id: string;
  name: string;
  description: string;
  payload: {
    amount: number;
    type: string;
    payment_method: string;
    transacted_at: string;
    student_count: number;
    school_avg_amount: number;
    rolling_24h_count: number;
    rolling_24h_amount: number;
    threshold: number;
  };
  expected_outcome: string;
}

interface InferenceResponse {
  model_name: string;
  model_version: string;
  anomaly_score: number;
  is_anomaly: boolean;
  risk_tier: string;
  threshold: number;
  latency_ms: number;
  reasons: string[];
  features_extracted: {
    amount: number;
    type: string;
    payment_method: string;
    hour_of_day: number;
    day_of_week: number;
    is_weekend: boolean;
    is_off_hours: boolean;
    amount_per_student: number;
    amount_to_school_avg_ratio: number;
    rolling_24h_count: number;
    log_amount: number;
  };
}

export function IsolationForestTester() {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('normal_subsidy');
  
  // Form State
  const [amount, setAmount] = useState<number>(250000);
  const [txType, setTxType] = useState<string>('SUBSIDY_DISBURSEMENT');
  const [paymentMethod, setPaymentMethod] = useState<string>('BANK_TRANSFER');
  const [transactedAt, setTransactedAt] = useState<string>('2026-10-29T12:00:00');
  const [studentCount, setStudentCount] = useState<number>(500);
  const [schoolAvgAmount, setSchoolAvgAmount] = useState<number>(240000);
  const [rolling24hCount, setRolling24hCount] = useState<number>(1);
  const [rolling24hAmount, setRolling24hAmount] = useState<number>(250000);
  const [threshold, setThreshold] = useState<number>(0.65);

  // Execution State
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<InferenceResponse | null>(null);
  const [error, setError] = useState<string>('');

  // Fetch presets on mount
  useEffect(() => {
    async function loadPresets() {
      try {
        const res = await api.get<{ presets: Preset[] }>('/models/presets');
        if (res && res.presets) {
          setPresets(res.presets);
          if (res.presets.length > 0) {
            applyPreset(res.presets[0]);
          }
        }
      } catch (err: any) {
        console.warn('Could not load presets from backend, using fallbacks:', err);
      }
    }
    loadPresets();
  }, []);

  const applyPreset = (preset: Preset) => {
    setSelectedPresetId(preset.id);
    setAmount(preset.payload.amount);
    setTxType(preset.payload.type);
    setPaymentMethod(preset.payload.payment_method);
    setTransactedAt(preset.payload.transacted_at);
    setStudentCount(preset.payload.student_count);
    setSchoolAvgAmount(preset.payload.school_avg_amount);
    setRolling24hCount(preset.payload.rolling_24h_count);
    setRolling24hAmount(preset.payload.rolling_24h_amount);
    setThreshold(preset.payload.threshold || 0.65);
    setResult(null);
    setError('');
  };

  const handleRunInference = async () => {
    setLoading(true);
    setError('');
    try {
      const payload = {
        amount: Number(amount),
        type: txType,
        payment_method: paymentMethod,
        transacted_at: transactedAt,
        student_count: Number(studentCount),
        school_avg_amount: Number(schoolAvgAmount),
        rolling_24h_count: Number(rolling24hCount),
        rolling_24h_amount: Number(rolling24hAmount),
        threshold: Number(threshold)
      };

      const res = await api.post<InferenceResponse>('/models/isolation-forest/infer', payload);
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Failed to execute inference.');
    } finally {
      setLoading(false);
    }
  };

  const getTierColor = (tier: string) => {
    switch (tier) {
      case 'CRITICAL':
        return 'bg-[#C0392B] text-white';
      case 'HIGH':
        return 'bg-[#D35400] text-white';
      case 'MEDIUM':
        return 'bg-[#E8A020] text-white';
      case 'LOW':
      default:
        return 'bg-[#2E7D52] text-white';
    }
  };

  return (
    <div className="bg-white rounded-xl border border-[#DDE1E7] shadow-sm overflow-hidden mb-6">
      {/* Header Banner */}
      <div className="bg-gradient-to-r from-[#1A3C5E] to-[#2471A3] p-5 text-white flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="w-5 h-5 text-[#E8A020]" />
            <span className="font-mono text-xs uppercase tracking-wider bg-white/10 px-2 py-0.5 rounded">
              Live Model Interface
            </span>
            <span className="text-xs bg-[#2E7D52] px-2 py-0.5 rounded-full font-semibold">
              isolation_forest_v1.joblib
            </span>
          </div>
          <h2 className="text-xl font-bold">Isolation Forest Anomaly Detection Sandbox</h2>
          <p className="text-xs text-blue-100">
            Submit custom transaction parameters or test real-world fraud vectors to evaluate unsupervised outlier scoring in real time.
          </p>
        </div>

        <button
          onClick={handleRunInference}
          disabled={loading}
          className="flex items-center justify-center gap-2 bg-[#2E7D52] hover:bg-[#256843] active:scale-95 text-white px-5 py-2.5 rounded-lg font-semibold shadow transition-all cursor-pointer disabled:opacity-50"
        >
          {loading ? (
            <>
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
              <span>Scoring...</span>
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" />
              <span>Run Inference</span>
            </>
          )}
        </button>
      </div>

      <div className="p-6">
        {/* Preset Vectors Bar */}
        <div className="mb-6">
          <label className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-2 block">
            Test Vector Presets (One-Click Scenarios)
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {presets.map((preset) => (
              <button
                key={preset.id}
                onClick={() => applyPreset(preset)}
                className={`p-3 text-left rounded-lg border text-sm transition-all cursor-pointer ${
                  selectedPresetId === preset.id
                    ? 'border-[#1A3C5E] bg-[#F4F6F9] ring-2 ring-[#1A3C5E]/20 shadow-xs'
                    : 'border-[#DDE1E7] hover:border-gray-400 bg-white'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-xs text-[#1C1C1E]">{preset.name}</span>
                  <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
                </div>
                <p className="text-[11px] text-[#6B7280] line-clamp-2 mb-1.5">{preset.description}</p>
                <span className="inline-block text-[10px] font-mono font-medium text-[#1A3C5E] bg-blue-50 px-1.5 py-0.5 rounded">
                  {preset.expected_outcome}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Input Parameters Form */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-7 bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-5">
            <h3 className="text-sm font-bold text-[#1C1C1E] mb-4 flex items-center gap-2">
              <Layers className="w-4 h-4 text-[#1A3C5E]" />
              Transaction Features & Context Parameters
            </h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
              {/* Amount */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">
                  Disbursement Amount (KES)
                </label>
                <div className="relative">
                  <DollarSign className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2.5" />
                  <input
                    type="number"
                    min="1"
                    value={amount}
                    onChange={(e) => setAmount(Number(e.target.value))}
                    className="w-full pl-8 pr-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm font-mono focus:border-[#1A3C5E] focus:outline-hidden"
                  />
                </div>
              </div>

              {/* Transaction Type */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">Transaction Type</label>
                <select
                  value={txType}
                  onChange={(e) => setTxType(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm focus:border-[#1A3C5E] focus:outline-hidden"
                >
                  <option value="SUBSIDY_DISBURSEMENT">SUBSIDY_DISBURSEMENT (Ministry)</option>
                  <option value="SUPPLIER_PAYMENT">SUPPLIER_PAYMENT (Procurement)</option>
                  <option value="MPESA_PAYMENT">MPESA_PAYMENT (Mobile Money)</option>
                  <option value="PARENTAL_CONTRIBUTION">PARENTAL_CONTRIBUTION</option>
                </select>
              </div>

              {/* Payment Method */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">Payment Method</label>
                <select
                  value={paymentMethod}
                  onChange={(e) => setPaymentMethod(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm focus:border-[#1A3C5E] focus:outline-hidden"
                >
                  <option value="BANK_TRANSFER">BANK_TRANSFER</option>
                  <option value="MPESA">MPESA</option>
                  <option value="CASH">CASH (High Risk Vector)</option>
                  <option value="CHEQUE">CHEQUE</option>
                </select>
              </div>

              {/* Transacted At */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block flex items-center gap-1">
                  <Clock className="w-3 h-3" /> Transacted Timestamp
                </label>
                <input
                  type="datetime-local"
                  value={transactedAt.slice(0, 16)}
                  onChange={(e) => setTransactedAt(e.target.value + ':00')}
                  className="w-full px-3 py-1.5 bg-white border border-[#CBD5E1] rounded text-sm font-mono focus:border-[#1A3C5E] focus:outline-hidden"
                />
              </div>

              {/* Student Count */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">
                  Enrolled Students (Ghost Student Check)
                </label>
                <input
                  type="number"
                  min="1"
                  value={studentCount}
                  onChange={(e) => setStudentCount(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm font-mono focus:border-[#1A3C5E] focus:outline-hidden"
                />
              </div>

              {/* School Average */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">
                  School Historical Average (KES)
                </label>
                <input
                  type="number"
                  min="1"
                  value={schoolAvgAmount}
                  onChange={(e) => setSchoolAvgAmount(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm font-mono focus:border-[#1A3C5E] focus:outline-hidden"
                />
              </div>

              {/* 24h Velocity Count */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">
                  24h Velocity Count (Disbursements)
                </label>
                <input
                  type="number"
                  min="1"
                  value={rolling24hCount}
                  onChange={(e) => setRolling24hCount(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm font-mono focus:border-[#1A3C5E] focus:outline-hidden"
                />
              </div>

              {/* 24h Cumulative Amount */}
              <div>
                <label className="font-medium text-[#475569] mb-1 block">
                  24h Cumulative Value (KES)
                </label>
                <input
                  type="number"
                  min="1"
                  value={rolling24hAmount}
                  onChange={(e) => setRolling24hAmount(Number(e.target.value))}
                  className="w-full px-3 py-2 bg-white border border-[#CBD5E1] rounded text-sm font-mono focus:border-[#1A3C5E] focus:outline-hidden"
                />
              </div>
            </div>

            {/* Threshold Slider */}
            <div className="mt-4 pt-4 border-t border-[#E2E8F0]">
              <div className="flex items-center justify-between mb-1.5">
                <span className="font-semibold text-xs text-[#334155]">
                  Classification Threshold ($\tau$)
                </span>
                <span className="font-mono font-bold text-xs text-[#1A3C5E]">
                  {threshold.toFixed(2)}
                </span>
              </div>
              <input
                type="range"
                min="0.10"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(Number(e.target.value))}
                className="w-full cursor-pointer accent-[#1A3C5E]"
              />
              <div className="flex justify-between text-[10px] text-gray-500 mt-1">
                <span>0.10 (Strict)</span>
                <span>0.65 (Calibrated Default)</span>
                <span>0.95 (Lenient)</span>
              </div>
            </div>
          </div>

          {/* Inference Output Card */}
          <div className="lg:col-span-5 flex flex-col justify-between">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-sm mb-4">
                <strong>Inference Error:</strong> {error}
              </div>
            )}

            {result ? (
              <div className="bg-white border-2 border-[#1A3C5E] rounded-xl p-5 shadow-md flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-4">
                    <div className="flex items-center gap-2">
                      <Zap className="w-5 h-5 text-[#2471A3]" />
                      <span className="font-bold text-sm text-[#1C1C1E]">Inference Output</span>
                    </div>
                    <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      {result.latency_ms} ms
                    </span>
                  </div>

                  {/* Anomaly Score Display */}
                  <div className="text-center py-2">
                    <div className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-1">
                      Calibrated Anomaly Score
                    </div>
                    <div className="text-4xl font-extrabold font-mono text-[#1C1C1E] tracking-tight mb-2">
                      {result.anomaly_score.toFixed(4)}
                    </div>

                    {/* Progress Bar with Threshold Marker */}
                    <div className="relative w-full bg-gray-100 rounded-full h-3 mb-3 overflow-hidden">
                      <div
                        className={`h-3 rounded-full transition-all duration-500 ${
                          result.is_anomaly ? 'bg-[#C0392B]' : 'bg-[#2E7D52]'
                        }`}
                        style={{ width: `${Math.min(result.anomaly_score * 100, 100)}%` }}
                      />
                    </div>

                    {/* Status & Tier Badges */}
                    <div className="flex items-center justify-center gap-2 mb-4">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${getTierColor(result.risk_tier)}`}>
                        {result.risk_tier} RISK
                      </span>
                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-bold flex items-center gap-1 ${
                          result.is_anomaly
                            ? 'bg-red-100 text-red-800 border border-red-300'
                            : 'bg-green-100 text-green-800 border border-green-300'
                        }`}
                      >
                        {result.is_anomaly ? (
                          <>
                            <ShieldAlert className="w-3.5 h-3.5" /> ANOMALY DETECTED
                          </>
                        ) : (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5" /> NORMAL BEHAVIOR
                          </>
                        )}
                      </span>
                    </div>
                  </div>

                  {/* Reasons / Flags */}
                  {result.reasons && result.reasons.length > 0 && (
                    <div className="mb-4">
                      <div className="text-xs font-bold text-[#475569] mb-1.5 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-[#D35400]" />
                        Identified Fraud Drivers:
                      </div>
                      <div className="space-y-1.5">
                        {result.reasons.map((reason, idx) => (
                          <div
                            key={idx}
                            className="bg-[#FEF3E2] border-l-4 border-[#E8A020] text-[#78350F] text-xs p-2 rounded-r"
                          >
                            {reason}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Extracted Engineered Features Summary */}
                  <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3 text-xs">
                    <span className="font-bold text-[#334155] block mb-2 text-[11px] uppercase tracking-wide">
                      Engineered Features Extracted:
                    </span>
                    <div className="grid grid-cols-2 gap-x-2 gap-y-1 font-mono text-[11px] text-[#475569]">
                      <div>Off-Hours: <strong className={result.features_extracted.is_off_hours ? 'text-red-600' : 'text-gray-700'}>{result.features_extracted.is_off_hours ? 'YES' : 'NO'}</strong></div>
                      <div>Hour of Day: <strong>{result.features_extracted.hour_of_day}:00</strong></div>
                      <div>Amount/Student: <strong>KES {result.features_extracted.amount_per_student.toLocaleString()}</strong></div>
                      <div>School Ratio: <strong>{result.features_extracted.amount_to_school_avg_ratio}x</strong></div>
                      <div>24h Count: <strong>{result.features_extracted.rolling_24h_count}</strong></div>
                      <div>Log Amount: <strong>{result.features_extracted.log_amount}</strong></div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 text-center">
                  <span className="text-[11px] text-[#6B7280]">
                    Scored via active artifact <code className="bg-gray-100 px-1 py-0.5 rounded">isolation_forest_v1.joblib</code>
                  </span>
                </div>
              </div>
            ) : (
              <div className="bg-[#F8FAFC] border-2 border-dashed border-[#CBD5E1] rounded-xl p-8 flex flex-col items-center justify-center text-center h-full min-h-[300px]">
                <Cpu className="w-12 h-12 text-[#94A3B8] mb-3 animate-pulse" />
                <h4 className="font-bold text-sm text-[#334155] mb-1">Awaiting Execution</h4>
                <p className="text-xs text-[#64748B] max-w-[260px] mb-4">
                  Adjust features on the left or select a preset vector above, then click <strong>Run Inference</strong> to test the model.
                </p>
                <button
                  onClick={handleRunInference}
                  disabled={loading}
                  className="bg-[#1A3C5E] text-white text-xs font-semibold px-4 py-2 rounded shadow hover:bg-[#2E7D52] transition-colors cursor-pointer"
                >
                  Run Test Now
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
