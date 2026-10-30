import React, { useState, useEffect } from 'react';
import { Header } from '../components/Header';
import { StatusBadge } from '../components/StatusBadge';
import { IsolationForestTester } from '../components/IsolationForestTester';
import { 
  Activity, 
  TrendingUp, 
  AlertTriangle, 
  PlayCircle, 
  BarChart3, 
  ShieldCheck, 
  Database,
  Sliders
} from 'lucide-react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { api } from '../lib/api';

const defaultModels = [
  { id: 'isolation-forest', name: 'Isolation Forest', version: 'v1.0.0', deployed: '2026-04-15', status: 'HEALTHY', threshold: 0.65, is_active: true },
  { id: 'autoencoder', name: 'Autoencoder', version: 'v3.0.2', deployed: '2026-04-20', status: 'HEALTHY', threshold: 0.70, is_active: false },
  { id: 'lstm', name: 'LSTM Autoencoder', version: 'v1.8.1', deployed: '2026-04-18', status: 'DRIFTING', threshold: 0.68, is_active: false },
  { id: 'gnn', name: 'Graph Neural Network', version: 'v2.3.0', deployed: '2026-04-22', status: 'HEALTHY', threshold: 0.72, is_active: false },
  { id: 'xgboost', name: 'XGBoost Supervised', version: 'v4.1.0', deployed: '2026-05-01', status: 'HEALTHY', threshold: 0.75, is_active: false },
];

const scoreDistribution = Array.from({ length: 20 }, (_, i) => ({
  range: (i * 0.05).toFixed(2),
  count: Math.floor(Math.random() * 150) + 50,
}));

const performanceMetrics = [
  { model: 'IF', precision: 0.87, recall: 0.82, f1: 0.84 },
  { model: 'AE', precision: 0.89, recall: 0.85, f1: 0.87 },
  { model: 'LSTM', precision: 0.83, recall: 0.79, f1: 0.81 },
  { model: 'GNN', precision: 0.92, recall: 0.88, f1: 0.90 },
  { model: 'XGB', precision: 0.94, recall: 0.91, f1: 0.92 },
];

const labelAccumulation = Array.from({ length: 30 }, (_, i) => ({
  day: i + 1,
  labels: Math.floor(Math.random() * 10) + 5,
  cumulative: (i + 1) * 8,
}));

export function ModelPerformance() {
  const [activeTab, setActiveTab] = useState<'tester' | 'metrics' | 'comparison'>('tester');
  const [selectedModelIdx, setSelectedModelIdx] = useState<number>(0);
  const [models, setModels] = useState(defaultModels);
  const [currentThreshold, setCurrentThreshold] = useState<number>(0.65);

  useEffect(() => {
    async function loadOverview() {
      try {
        const res = await api.get<{ models: any[] }>('/models/overview');
        if (res && res.models && res.models.length > 0) {
          setModels(res.models);
        }
      } catch (e) {
        // Fallback to static definitions
      }
    }
    loadOverview();
  }, []);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      <Header breadcrumbs={['Model Performance & Live Inference']} />

      <main className="flex-1 overflow-y-auto bg-[#F4F6F9] p-6">
        {/* Model status cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4 mb-6">
          {models.map((model, index) => (
            <div 
              key={index} 
              onClick={() => setSelectedModelIdx(index)}
              className={`bg-white rounded-lg border p-4 transition-all cursor-pointer ${
                selectedModelIdx === index 
                  ? 'border-[#1A3C5E] ring-2 ring-[#1A3C5E]/20 shadow-xs' 
                  : 'border-[#DDE1E7] hover:border-gray-400'
              }`}
            >
              <div className="flex items-start justify-between mb-3">
                <Activity className="w-5 h-5 text-[#6B7280]" />
                <StatusBadge
                  status={model.status}
                  variant={model.status === 'DRIFTING' ? 'filled' : 'outline'}
                />
              </div>
              <h3 className="font-bold text-sm mb-1">{model.name}</h3>
              <p className="text-xs text-[#6B7280] mb-1 font-mono">{model.version}</p>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-100">
                <span className="text-[10px] text-[#6B7280]">Deployed: {model.deployed}</span>
                {model.id === 'isolation-forest' && (
                  <span className="text-[10px] bg-green-100 text-green-800 font-bold px-1.5 py-0.5 rounded">
                    ACTIVE
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* View Mode Tabs */}
        <div className="flex items-center gap-2 mb-4 bg-white p-1 rounded-lg border border-[#DDE1E7] w-fit shadow-xs">
          <button
            onClick={() => setActiveTab('tester')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'tester'
                ? 'bg-[#1A3C5E] text-white shadow-xs'
                : 'text-[#475569] hover:bg-gray-100'
            }`}
          >
            <PlayCircle className="w-4 h-4" />
            Live Inference Sandbox (Interactive)
          </button>
          <button
            onClick={() => setActiveTab('metrics')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'metrics'
                ? 'bg-[#1A3C5E] text-white shadow-xs'
                : 'text-[#475569] hover:bg-gray-100'
            }`}
          >
            <Sliders className="w-4 h-4" />
            Model Benchmarks & Drift
          </button>
          <button
            onClick={() => setActiveTab('comparison')}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-semibold transition-all cursor-pointer ${
              activeTab === 'comparison'
                ? 'bg-[#1A3C5E] text-white shadow-xs'
                : 'text-[#475569] hover:bg-gray-100'
            }`}
          >
            <BarChart3 className="w-4 h-4" />
            Fleet Comparison
          </button>
        </div>

        {/* Tab 1: Live Interactive Inference Tester */}
        {activeTab === 'tester' && (
          <div>
            <IsolationForestTester />
          </div>
        )}

        {/* Tab 2: Model Architecture & Drift details */}
        {activeTab === 'metrics' && (
          <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 mb-6">
            <div className="border-b border-[#DDE1E7] pb-4 mb-6 flex items-center justify-between">
              <div>
                <h2 className="text-lg font-bold">{models[selectedModelIdx].name} Specifications</h2>
                <p className="text-xs text-[#6B7280]">
                  Production artifact loaded: <code className="font-mono bg-gray-100 px-1 py-0.5 rounded">backend/ml/saved_models/isolation_forest_v1.joblib</code>
                </p>
              </div>
              <span className="text-xs font-mono bg-blue-50 text-[#1A3C5E] px-2.5 py-1 rounded font-semibold border border-blue-200">
                ROC-AUC: 0.9422
              </span>
            </div>

            {/* Model details */}
            <div className="space-y-6">
              {/* Threshold */}
              <div>
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-bold text-sm">Operating Decision Threshold</h3>
                  <span className="text-xs text-gray-500">Calibrated for 5% contamination</span>
                </div>
                <div className="flex items-center gap-4">
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={currentThreshold}
                    onChange={(e) => setCurrentThreshold(Number(e.target.value))}
                    className="flex-1 accent-[#1A3C5E] cursor-pointer"
                  />
                  <span className="font-mono font-bold text-lg">{currentThreshold.toFixed(2)}</span>
                </div>
              </div>

              {/* Score distribution */}
              <div>
                <h3 className="font-bold text-sm mb-3">Score Distribution (Historical Test Population)</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={scoreDistribution}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="range" tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 12 }} />
                    <Tooltip />
                    <Bar dataKey="count" fill="#2471A3" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Performance metrics */}
              <div>
                <h3 className="font-bold text-sm mb-3">Test Set Evaluation Metrics</h3>
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-[#F4F6F9] rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-[#1C1C1E]">0.87</p>
                    <p className="text-sm text-[#6B7280]">Precision</p>
                  </div>
                  <div className="bg-[#F4F6F9] rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-[#1C1C1E]">0.82</p>
                    <p className="text-sm text-[#6B7280]">Recall</p>
                  </div>
                  <div className="bg-[#F4F6F9] rounded-lg p-4 text-center">
                    <p className="text-2xl font-bold text-[#1C1C1E]">0.84</p>
                    <p className="text-sm text-[#6B7280]">F1 Score</p>
                  </div>
                </div>
              </div>

              {/* Drift detection */}
              <div className="bg-[#F4F6F9] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-2">Kolmogorov-Smirnov Feature Drift Status</h3>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">KS-Statistic (vs Reference Baseline):</span>
                  <span className="font-mono font-bold">0.042 (p = 0.814)</span>
                </div>
                <div className="flex items-center justify-between mt-2">
                  <span className="text-sm text-gray-600">Statistical Drift Detected:</span>
                  <span className="text-[#2E7D52] font-semibold flex items-center gap-1">
                    <ShieldCheck className="w-4 h-4" /> NO DRIFT DETECTED
                  </span>
                </div>
              </div>

              {/* Retraining */}
              <div className="bg-[#FEF3E2] border border-[#E8A020] rounded-lg p-4">
                <h3 className="font-bold text-sm mb-2 flex items-center gap-2 text-[#78350F]">
                  <TrendingUp className="w-4 h-4" />
                  Retraining Trigger Status
                </h3>
                <p className="text-sm mb-2 text-[#78350F]">
                  Automated re-fit pipeline triggered at <span className="font-bold">50 confirmed labels</span> — currently <span className="font-bold">34 labels</span> accumulated from case investigations.
                </p>
                <div className="w-full bg-white rounded-full h-2 mb-3">
                  <div className="bg-[#E8A020] h-2 rounded-full" style={{ width: '68%' }}></div>
                </div>
                <button className="bg-[#1A3C5E] text-white px-4 py-2 rounded font-medium hover:bg-[#2E7D52] transition-colors text-sm cursor-pointer">
                  Trigger Manual Retraining Pipeline
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 3: Fleet Comparison charts */}
        {activeTab === 'comparison' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Model comparison */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-xs">
              <h3 className="font-bold text-base mb-4">Multi-Model Performance Comparison</h3>
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={performanceMetrics}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="model" tick={{ fontSize: 12 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="precision" fill="#2E7D52" name="Precision" />
                  <Bar dataKey="recall" fill="#2471A3" name="Recall" />
                  <Bar dataKey="f1" fill="#E8A020" name="F1 Score" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Label accumulation */}
            <div className="bg-white rounded-lg border border-[#DDE1E7] p-6 shadow-xs">
              <h3 className="font-bold text-base mb-4">Ground-Truth Label Accumulation (Last 30 Days)</h3>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={labelAccumulation}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="cumulative" stroke="#1A3C5E" strokeWidth={2} name="Cumulative Labels" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
