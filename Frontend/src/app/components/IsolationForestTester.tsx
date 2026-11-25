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

interface ReconstructionDriver {
  feature: string;
  squared_error: number;
  share: number;
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
  reconstruction_drivers?: ReconstructionDriver[];
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

interface EnsembleBreakdownItem {
  id: string;
  name: string;
  status: string;
  score: number;
  configured_weight: number;
  effective_weight: number;
  weighted_contribution: number;
  effective_contribution: number;
}

interface EnsembleInferenceResponse {
  composite_score: number;
  raw_weighted_sum: number;
  risk_tier: string;
  is_anomaly: boolean;
  total_latency_ms: number;
  weights: Record<string, number>;
  breakdown: EnsembleBreakdownItem[];
  isolation_forest: InferenceResponse;
  autoencoder: InferenceResponse;
  lstm?: InferenceResponse;
  reasons: string[];
  features_extracted: InferenceResponse['features_extracted'];
}

export interface ScoringWeights {
  weight_if: number;
  weight_ae: number;
  weight_lstm: number;
  weight_gnn: number;
}

interface TesterProps {
  weights?: ScoringWeights;
  selectedModelId?: string;
  onScoresUpdated?: (scores: {
    ifScore: number;
    aeScore: number;
    lstmScore: number;
    compositeScore: number;
    activeModelId: ModelMode;
    activeScore: number;
  }) => void;
}

export type ModelMode = 'ensemble' | 'autoencoder' | 'lstm' | 'isolation-forest';

export function IsolationForestTester({ weights, selectedModelId, onScoresUpdated }: TesterProps) {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('normal_subsidy');
  const [modelMode, setModelMode] = useState<ModelMode>('ensemble');
  
  // Form State
  const [amount, setAmount] = useState<number>(248750);
  const [txType, setTxType] = useState<string>('SUBSIDY_DISBURSEMENT');
  const [paymentMethod, setPaymentMethod] = useState<string>('BANK_TRANSFER');
  const [transactedAt, setTransactedAt] = useState<string>('2026-10-29T12:15:00');
  const [studentCount, setStudentCount] = useState<number>(500);
  const [schoolAvgAmount, setSchoolAvgAmount] = useState<number>(240000);
  const [rolling24hCount, setRolling24hCount] = useState<number>(1);
  const [rolling24hAmount, setRolling24hAmount] = useState<number>(248750);
  const [threshold, setThreshold] = useState<number>(0.70);

  // Execution State
  const [loading, setLoading] = useState<boolean>(false);
  const [result, setResult] = useState<InferenceResponse | null>(null);
  const [ensembleResult, setEnsembleResult] = useState<EnsembleInferenceResponse | null>(null);
  const [error, setError] = useState<string>('');

  const executeInference = async (
    modeOverride?: ModelMode,
    payloadOverride?: Preset['payload']
  ) => {
    const activeMode = modeOverride ?? modelMode;
    const activeThreshold = Number(payloadOverride?.threshold ?? threshold);
    const basePayload = {
      amount: Number(payloadOverride?.amount ?? amount),
      type: payloadOverride?.type ?? txType,
      payment_method: payloadOverride?.payment_method ?? paymentMethod,
      transacted_at: payloadOverride?.transacted_at ?? transactedAt,
      student_count: Number(payloadOverride?.student_count ?? studentCount),
      school_avg_amount: Number(payloadOverride?.school_avg_amount ?? schoolAvgAmount),
      rolling_24h_count: Number(payloadOverride?.rolling_24h_count ?? rolling24hCount),
      rolling_24h_amount: Number(payloadOverride?.rolling_24h_amount ?? rolling24hAmount),
      threshold: activeThreshold,
    };

    setLoading(true);
    setError('');
    try {
      const ensPromise = api.post<EnsembleInferenceResponse>('/models/ensemble/infer', {
        ...basePayload,
        if_threshold: activeMode === 'isolation-forest' ? activeThreshold : 0.65,
        ae_threshold: activeMode === 'autoencoder' ? activeThreshold : 0.70,
        lstm_threshold: activeMode === 'lstm' ? activeThreshold : 0.68,
        ...(weights ? { weights } : {}),
      });

      if (activeMode === 'ensemble') {
        const ensRes = await ensPromise;
        setEnsembleResult(ensRes);
        setResult(null);
        onScoresUpdated?.({
          ifScore: ensRes.isolation_forest?.anomaly_score ?? 0,
          aeScore: ensRes.autoencoder?.anomaly_score ?? 0,
          lstmScore: ensRes.lstm?.anomaly_score ?? 0,
          compositeScore: ensRes.composite_score,
          activeModelId: 'ensemble',
          activeScore: ensRes.composite_score,
        });
      } else {
        const endpoint =
          activeMode === 'autoencoder'
            ? '/models/autoencoder/infer'
            : activeMode === 'lstm'
            ? '/models/lstm/infer'
            : '/models/isolation-forest/infer';
        const [singleRes, ensRes] = await Promise.all([
          api.post<InferenceResponse>(endpoint, basePayload),
          ensPromise.catch(() => null),
        ]);
        setResult(singleRes);
        setEnsembleResult(ensRes);
        onScoresUpdated?.({
          ifScore:
            activeMode === 'isolation-forest'
              ? singleRes.anomaly_score
              : ensRes?.isolation_forest?.anomaly_score ?? singleRes.anomaly_score,
          aeScore:
            activeMode === 'autoencoder'
              ? singleRes.anomaly_score
              : ensRes?.autoencoder?.anomaly_score ?? singleRes.anomaly_score,
          lstmScore:
            activeMode === 'lstm'
              ? singleRes.anomaly_score
              : ensRes?.lstm?.anomaly_score ?? singleRes.anomaly_score,
          compositeScore: ensRes?.composite_score ?? singleRes.anomaly_score,
          activeModelId: activeMode,
          activeScore: singleRes.anomaly_score,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Failed to execute inference.');
    } finally {
      setLoading(false);
    }
  };

  // Sync when parent selects a specific model card
  useEffect(() => {
    if (
      selectedModelId === 'isolation-forest' ||
      selectedModelId === 'autoencoder' ||
      selectedModelId === 'lstm'
    ) {
      setModelMode(selectedModelId);
      executeInference(selectedModelId);
    }
  }, [selectedModelId]);

  // Fetch presets on mount and run initial inference so score bar is immediately populated
  useEffect(() => {
    async function loadPresets() {
      try {
        const res = await api.get<{ presets: Preset[] }>('/models/presets');
        if (res && res.presets) {
          setPresets(res.presets);
          if (res.presets.length > 0) {
            const first = res.presets[0];
            setSelectedPresetId(first.id);
            setAmount(first.payload.amount);
            setTxType(first.payload.type);
            setPaymentMethod(first.payload.payment_method);
            setTransactedAt(first.payload.transacted_at);
            setStudentCount(first.payload.student_count);
            setSchoolAvgAmount(first.payload.school_avg_amount);
            setRolling24hCount(first.payload.rolling_24h_count);
            setRolling24hAmount(first.payload.rolling_24h_amount);
            setThreshold(first.payload.threshold || 0.70);
            executeInference(modelMode, first.payload);
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
    setThreshold(preset.payload.threshold || 0.70);
    executeInference(modelMode, preset.payload);
  };

  const handleRunInference = async () => {
    await executeInference(modelMode);
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
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <Cpu className="w-5 h-5 text-[#E8A020]" />
            <span className="font-mono text-xs uppercase tracking-wider bg-white/10 px-2 py-0.5 rounded">
              Live Model Interface
            </span>
            <span className="text-xs bg-[#2E7D52] px-2 py-0.5 rounded-full font-semibold">
              {modelMode === 'ensemble'
                ? '3-Model Weighted Ensemble'
                : modelMode === 'autoencoder'
                ? 'autoencoder_v1.joblib'
                : modelMode === 'lstm'
                ? 'lstm_autoencoder_v1.joblib'
                : 'isolation_forest_v1.joblib'}
            </span>
          </div>
          <h2 className="text-xl font-bold">
            {modelMode === 'ensemble'
              ? 'Weighted Ensemble (IF + AE + LSTM) Detection Sandbox'
              : modelMode === 'autoencoder'
              ? 'Autoencoder Neural Reconstruction Sandbox'
              : modelMode === 'lstm'
              ? 'LSTM Autoencoder Temporal Sequence Sandbox'
              : 'Isolation Forest Anomaly Detection Sandbox'}
          </h2>
          <p className="text-xs text-blue-100">
            Submit custom transaction parameters or test real-world fraud vectors to inspect model scores, reconstruction drivers, and ensemble weights.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
          <div className="flex bg-white/10 p-1 rounded-lg border border-white/15 text-xs">
            {[
              { id: 'ensemble' as const, label: '3-Model Ensemble' },
              { id: 'lstm' as const, label: 'LSTM Temporal' },
              { id: 'autoencoder' as const, label: 'Autoencoder' },
              { id: 'isolation-forest' as const, label: 'Isolation Forest' },
            ].map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => {
                  setModelMode(opt.id);
                  executeInference(opt.id);
                }}
                className={`px-2.5 py-1.5 rounded font-semibold transition-all cursor-pointer ${
                  modelMode === opt.id
                    ? 'bg-white text-[#1A3C5E] shadow-xs'
                    : 'text-blue-100 hover:bg-white/10'
                }`}
              >
                {opt.label}
              </button>
            ))}
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
      </div>

      <div className="p-6">
        {/* Preset Vectors Bar */}
        <div className="mb-6">
          <label className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-2 block">
            Test Vector Presets (One-Click Scenarios)
          </label>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
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
                  Classification Threshold (τ)
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

            {modelMode === 'ensemble' && ensembleResult ? (
              <div className="bg-white border-2 border-[#1A3C5E] rounded-xl p-5 shadow-md flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-4">
                    <div className="flex items-center gap-2">
                      <Zap className="w-5 h-5 text-[#2471A3]" />
                      <span className="font-bold text-sm text-[#1C1C1E]">Weighted Ensemble Output</span>
                    </div>
                    <span className="text-xs font-mono text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      {ensembleResult.total_latency_ms} ms
                    </span>
                  </div>

                  {/* Composite Score Display */}
                  <div className="text-center py-2">
                    <div className="text-xs font-bold text-[#6B7280] uppercase tracking-wider mb-1">
                      Composite Active-Weighted Score
                    </div>
                    <div className="text-4xl font-extrabold font-mono text-[#1C1C1E] tracking-tight mb-1">
                      {ensembleResult.composite_score.toFixed(4)}
                    </div>
                    <div className="text-[11px] font-mono text-[#6B7280] mb-2">
                      3-Model Weighted Sum: {ensembleResult.raw_weighted_sum.toFixed(4)}
                    </div>

                    <div className="relative w-full bg-gray-100 rounded-full h-3 mb-3 overflow-hidden">
                      <div
                        className={`h-3 rounded-full transition-all duration-500 ${
                          ensembleResult.composite_score >= threshold ? 'bg-[#C0392B]' : 'bg-[#2E7D52]'
                        }`}
                        style={{ width: `${Math.min(ensembleResult.composite_score * 100, 100)}%` }}
                      />
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-[#1C1C1E] z-10"
                        style={{ left: `${Math.min(Math.max(threshold * 100, 0), 100)}%` }}
                        title={`Threshold τ = ${threshold.toFixed(2)}`}
                      />
                    </div>

                    <div className="flex items-center justify-center gap-2 mb-4">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${getTierColor(ensembleResult.risk_tier)}`}>
                        {ensembleResult.risk_tier} RISK
                      </span>
                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-bold flex items-center gap-1 ${
                          ensembleResult.is_anomaly
                            ? 'bg-red-100 text-red-800 border border-red-300'
                            : 'bg-green-100 text-green-800 border border-green-300'
                        }`}
                      >
                        {ensembleResult.is_anomaly ? (
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

                  {/* Per-Model Score & Weight Table */}
                  <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3 mb-4">
                    <div className="text-[11px] font-bold text-[#334155] uppercase tracking-wide mb-2">
                      Model Scores &amp; Ensemble Weights
                    </div>
                    <div className="space-y-2">
                      {ensembleResult.breakdown.map((item) => (
                        <div key={item.id} className="text-xs">
                          <div className="flex items-center justify-between mb-0.5">
                            <div className="flex items-center gap-1.5">
                              <span className="font-semibold text-[#1C1C1E]">{item.name}</span>
                              <span
                                className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${
                                  item.status === 'ACTIVE'
                                    ? 'bg-green-100 text-green-800'
                                    : 'bg-gray-200 text-gray-600'
                                }`}
                              >
                                w={(item.configured_weight * 100).toFixed(0)}%
                              </span>
                            </div>
                            <span className="font-mono text-[#1A3C5E] font-bold">
                              {item.status === 'ACTIVE'
                                ? `${item.score.toFixed(4)} (+${item.effective_contribution.toFixed(3)})`
                                : 'Pending Training'}
                            </span>
                          </div>
                          {item.status === 'ACTIVE' && (
                            <div className="w-full bg-gray-200 rounded-full h-1.5">
                              <div
                                className="bg-[#2471A3] h-1.5 rounded-full"
                                style={{ width: `${Math.min(item.score * 100, 100)}%` }}
                              />
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Autoencoder Top Reconstruction Drivers */}
                  {ensembleResult.autoencoder?.reconstruction_drivers &&
                    ensembleResult.autoencoder.reconstruction_drivers.length > 0 && (
                      <div className="mb-4 bg-blue-50/70 border border-blue-200 rounded-lg p-3">
                        <div className="text-[11px] font-bold text-[#1A3C5E] uppercase tracking-wide mb-1.5">
                          Autoencoder Top Reconstruction Error Drivers
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {ensembleResult.autoencoder.reconstruction_drivers.map((d) => (
                            <span
                              key={d.feature}
                              className="text-[11px] font-mono bg-white border border-blue-200 text-[#1A3C5E] px-2 py-0.5 rounded"
                            >
                              {d.feature}: {(d.share * 100).toFixed(1)}%
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                  {/* Reasons / Flags */}
                  {ensembleResult.reasons && ensembleResult.reasons.length > 0 && (
                    <div className="mb-4">
                      <div className="text-xs font-bold text-[#475569] mb-1.5 flex items-center gap-1">
                        <AlertTriangle className="w-3.5 h-3.5 text-[#D35400]" />
                        Identified Fraud Drivers:
                      </div>
                      <div className="space-y-1.5">
                        {ensembleResult.reasons.map((reason, idx) => (
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
                      <div>Off-Hours: <strong className={ensembleResult.features_extracted.is_off_hours ? 'text-red-600' : 'text-gray-700'}>{ensembleResult.features_extracted.is_off_hours ? 'YES' : 'NO'}</strong></div>
                      <div>Hour of Day: <strong>{ensembleResult.features_extracted.hour_of_day}:00</strong></div>
                      <div>Amount/Student: <strong>KES {ensembleResult.features_extracted.amount_per_student.toLocaleString()}</strong></div>
                      <div>School Ratio: <strong>{ensembleResult.features_extracted.amount_to_school_avg_ratio}x</strong></div>
                      <div>24h Count: <strong>{ensembleResult.features_extracted.rolling_24h_count}</strong></div>
                      <div>Log Amount: <strong>{ensembleResult.features_extracted.log_amount}</strong></div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-gray-100 text-center">
                  <span className="text-[11px] text-[#6B7280]">
                    Scored via active artifacts <code className="bg-gray-100 px-1 py-0.5 rounded">isolation_forest_v1.joblib</code>, <code className="bg-gray-100 px-1 py-0.5 rounded">autoencoder_v1.joblib</code> &amp; <code className="bg-gray-100 px-1 py-0.5 rounded">lstm_autoencoder_v1.joblib</code>
                  </span>
                </div>
              </div>
            ) : result ? (
              <div className="bg-white border-2 border-[#1A3C5E] rounded-xl p-5 shadow-md flex-1 flex flex-col justify-between">
                <div>
                  <div className="flex items-center justify-between border-b border-gray-100 pb-3 mb-4">
                    <div className="flex items-center gap-2">
                      <Zap className="w-5 h-5 text-[#2471A3]" />
                      <span className="font-bold text-sm text-[#1C1C1E]">{result.model_name} Output</span>
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
                          result.anomaly_score >= threshold ? 'bg-[#C0392B]' : 'bg-[#2E7D52]'
                        }`}
                        style={{ width: `${Math.min(result.anomaly_score * 100, 100)}%` }}
                      />
                      <div
                        className="absolute top-0 bottom-0 w-0.5 bg-[#1C1C1E] z-10"
                        style={{ left: `${Math.min(Math.max(threshold * 100, 0), 100)}%` }}
                        title={`Threshold τ = ${threshold.toFixed(2)}`}
                      />
                    </div>

                    {/* Status & Tier Badges */}
                    <div className="flex items-center justify-center gap-2 mb-4">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-bold ${getTierColor(result.risk_tier)}`}>
                        {result.risk_tier} RISK
                      </span>
                      <span
                        className={`px-2.5 py-1 rounded-md text-xs font-bold flex items-center gap-1 ${
                          result.anomaly_score >= threshold
                            ? 'bg-red-100 text-red-800 border border-red-300'
                            : 'bg-green-100 text-green-800 border border-green-300'
                        }`}
                      >
                        {result.anomaly_score >= threshold ? (
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

                  {/* Individual vs 3-Model Score Bars */}
                  {ensembleResult && (
                    <div className="bg-[#F8FAFC] border border-[#E2E8F0] rounded-lg p-3 mb-4">
                      <div className="text-[11px] font-bold text-[#334155] uppercase tracking-wide mb-2">
                        Individual Model Score vs. Peer Fleet Bars
                      </div>
                      <div className="space-y-2">
                        {ensembleResult.breakdown.map((item) => {
                          const isCurrent =
                            (modelMode === 'isolation-forest' && item.id === 'if') ||
                            (modelMode === 'autoencoder' && item.id === 'ae') ||
                            (modelMode === 'lstm' && item.id === 'lstm');
                          const barScore = isCurrent ? result.anomaly_score : item.score;
                          return (
                            <div key={item.id} className="text-xs">
                              <div className="flex items-center justify-between mb-0.5">
                                <div className="flex items-center gap-1.5">
                                  <span className={`font-semibold ${isCurrent ? 'text-[#1A3C5E] underline' : 'text-[#1C1C1E]'}`}>
                                    {item.name} {isCurrent ? '(Selected Test)' : ''}
                                  </span>
                                </div>
                                <span className="font-mono text-[#1A3C5E] font-bold">
                                  {barScore.toFixed(4)}
                                </span>
                              </div>
                              <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                                <div
                                  className={`h-2 rounded-full transition-all duration-500 ${
                                    isCurrent
                                      ? barScore >= threshold
                                        ? 'bg-[#C0392B]'
                                        : 'bg-[#2E7D52]'
                                      : 'bg-[#2471A3]'
                                  }`}
                                  style={{ width: `${Math.min(barScore * 100, 100)}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {result.reconstruction_drivers && result.reconstruction_drivers.length > 0 && (
                    <div className="mb-4 bg-blue-50/70 border border-blue-200 rounded-lg p-3">
                      <div className="text-[11px] font-bold text-[#1A3C5E] uppercase tracking-wide mb-1.5">
                        Top Reconstruction Error Drivers
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {result.reconstruction_drivers.map((d) => (
                          <span
                            key={d.feature}
                            className="text-[11px] font-mono bg-white border border-blue-200 text-[#1A3C5E] px-2 py-0.5 rounded"
                          >
                            {d.feature}: {(d.share * 100).toFixed(1)}%
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

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
                    Scored via active artifact{' '}
                    <code className="bg-gray-100 px-1 py-0.5 rounded">
                      {result.model_name === 'Autoencoder'
                        ? 'autoencoder_v1.joblib'
                        : result.model_name === 'LSTM Autoencoder'
                        ? 'lstm_autoencoder_v1.joblib'
                        : 'isolation_forest_v1.joblib'}
                    </code>
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
