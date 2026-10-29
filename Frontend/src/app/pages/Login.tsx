import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router';
import {
  Shield,
  Lock,
  Mail,
  User,
  Eye,
  EyeOff,
  ArrowRight,
  CheckCircle,
  Fingerprint,
  Activity,
  Database,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { useAuth, getDesignatedRouteForRole } from '../context/AuthContext';

/* ─── Floating shield particles (decorative) ─── */
function FloatingParticles() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none">
      {Array.from({ length: 6 }).map((_, i) => (
        <div
          key={i}
          className="absolute animate-float"
          style={{
            left: `${15 + i * 14}%`,
            top: `${10 + (i % 3) * 30}%`,
            animationDelay: `${i * 1.2}s`,
            animationDuration: `${6 + i * 0.8}s`,
          }}
        >
          <Shield
            className="text-white/[0.06]"
            style={{ width: 20 + i * 6, height: 20 + i * 6 }}
          />
        </div>
      ))}
    </div>
  );
}

/* ─── Feature card for the left panel ─── */
function FeatureItem({
  icon: Icon,
  title,
  desc,
  delay,
}: {
  icon: typeof Shield;
  title: string;
  desc: string;
  delay: number;
}) {
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay);
    return () => clearTimeout(t);
  }, [delay]);

  return (
    <div
      className={`flex items-start gap-4 transition-all duration-700 ${
        visible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-6'
      }`}
    >
      <div className="w-10 h-10 rounded-lg bg-white/10 backdrop-blur-sm flex items-center justify-center flex-shrink-0 border border-white/10">
        <Icon className="w-5 h-5 text-white/90" />
      </div>
      <div>
        <p className="text-sm font-semibold text-white">{title}</p>
        <p className="text-xs text-white/60 mt-0.5 leading-relaxed">{desc}</p>
      </div>
    </div>
  );
}

/* ─── Main Login Component ─── */
export function Login() {
  const navigate = useNavigate();
  const { login, verify2FA, isAuthenticated, user } = useAuth();

  /* Redirect if already authenticated */
  useEffect(() => {
    if (isAuthenticated) {
      navigate(getDesignatedRouteForRole(user?.role), { replace: true });
    }
  }, [isAuthenticated, user, navigate]);

  /* State */
  const [step, setStep] = useState<'login' | '2fa'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [otpDigits, setOtpDigits] = useState(['', '', '', '', '', '']);
  const [error, setError] = useState('');
  const [tempToken, setTempToken] = useState('');

  /* Handlers */
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      const result = await login({ email, password });

      if (result.requires2Fa) {
        setTempToken(result.tempToken || '');
        setStep('2fa');
      } else {
        // No 2FA — go straight to designated role page
        navigate(getDesignatedRouteForRole(result.user?.role), { replace: true });
      }
    } catch (err: any) {
      setError(err.message || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handle2FA = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    const otpCode = otpDigits.join('');

    try {
      const authUser = await verify2FA(tempToken, otpCode);
      navigate(getDesignatedRouteForRole(authUser?.role), { replace: true });
    } catch (err: any) {
      setError(err.message || 'Invalid verification code. Please try again.');
      setOtpDigits(['', '', '', '', '', '']);
      // Focus first OTP input
      document.getElementById('otp-0')?.focus();
    } finally {
      setIsLoading(false);
    }
  };

  const handleOtpChange = (index: number, value: string) => {
    if (!/^\d*$/.test(value)) return;
    const next = [...otpDigits];
    next[index] = value.slice(-1);
    setOtpDigits(next);
    // Auto-focus next input
    if (value && index < 5) {
      const nextInput = document.getElementById(`otp-${index + 1}`);
      nextInput?.focus();
    }
  };

  const handleOtpKeyDown = (index: number, e: React.KeyboardEvent) => {
    if (e.key === 'Backspace' && !otpDigits[index] && index > 0) {
      const prevInput = document.getElementById(`otp-${index - 1}`);
      prevInput?.focus();
    }
  };

  const handleOtpPaste = (e: React.ClipboardEvent) => {
    e.preventDefault();
    const pasted = e.clipboardData.getData('text').replace(/\D/g, '').slice(0, 6);
    if (pasted.length === 6) {
      setOtpDigits(pasted.split(''));
      document.getElementById('otp-5')?.focus();
    }
  };

  return (
    <div className="min-h-screen flex bg-[#0f172a]">
      {/* ──────── Left Hero Panel ──────── */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden">
        {/* Gradient background */}
        <div className="absolute inset-0 bg-gradient-to-br from-[#1A3C5E] via-[#1a4a3e] to-[#2E7D52]" />

        {/* Subtle mesh overlay */}
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              'radial-gradient(at 20% 80%, rgba(46,125,82,0.4) 0%, transparent 50%), radial-gradient(at 80% 20%, rgba(26,60,94,0.5) 0%, transparent 50%), radial-gradient(at 50% 50%, rgba(232,160,32,0.1) 0%, transparent 60%)',
          }}
        />

        <FloatingParticles />

        {/* Content */}
        <div className="relative z-10 flex flex-col justify-between p-12 w-full max-w-xl">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-white/10 backdrop-blur-sm border border-white/15 flex items-center justify-center">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-xl text-white tracking-tight">DSFMP</h1>
              <p className="text-[11px] text-white/60 font-medium tracking-wide uppercase">
                Fraud Detection Module
              </p>
            </div>
          </div>

          {/* Headline */}
          <div className="space-y-6">
            <div>
              <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/10 backdrop-blur-sm border border-white/10 text-xs text-white/80 font-medium mb-6">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                System Online — All Models Active
              </div>

              <h2 className="text-[2.25rem] font-bold text-white leading-[1.15] tracking-tight">
                Protecting School
                <br />
                Feeding Programs
                <br />
                <span className="bg-gradient-to-r from-emerald-300 to-teal-200 bg-clip-text text-transparent">
                  Through Intelligent
                </span>
                <br />
                Oversight
              </h2>

              <p className="text-white/50 text-sm mt-4 max-w-sm leading-relaxed">
                Advanced machine learning and blockchain-powered fraud detection for Kenya's Digital
                School Feeding Management Platform.
              </p>
            </div>

            {/* Feature list */}
            <div className="space-y-4">
              <FeatureItem
                icon={Activity}
                title="Multi-Layer ML Anomaly Detection"
                desc="5 specialized models scoring every transaction in real time"
                delay={300}
              />
              <FeatureItem
                icon={Database}
                title="Hyperledger Fabric Verification"
                desc="Immutable blockchain audit trail for all flagged transactions"
                delay={600}
              />
              <FeatureItem
                icon={Fingerprint}
                title="Role-Based Access & 2FA"
                desc="Government-grade security with multi-factor authentication"
                delay={900}
              />
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center gap-2 text-xs text-white/30">
            <Shield className="w-3.5 h-3.5" />
            <span>Republic of Kenya — Ministry of Education</span>
          </div>
        </div>
      </div>

      {/* ──────── Right Login Panel ──────── */}
      <div className="w-full lg:w-[480px] xl:w-[520px] flex items-center justify-center bg-white relative">
        {/* Decorative top accent */}
        <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-[#1A3C5E] via-[#2E7D52] to-[#E8A020]" />

        <div className="w-full max-w-sm px-8 py-12">
          {/* Mobile logo (only visible on small screens) */}
          <div className="lg:hidden flex items-center gap-3 mb-10">
            <div className="w-10 h-10 rounded-xl bg-[#1A3C5E] flex items-center justify-center">
              <Shield className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="font-bold text-lg text-[#1A3C5E]">DSFMP</h1>
              <p className="text-[10px] text-[#6B7280] uppercase tracking-wide">Fraud Detection</p>
            </div>
          </div>

          {/* ──── Login Step ──── */}
          <div
            className={`transition-all duration-500 ${
              step === 'login'
                ? 'opacity-100 translate-x-0'
                : 'opacity-0 -translate-x-8 absolute pointer-events-none'
            }`}
          >
            <div className="mb-8">
              <h2 className="text-2xl font-bold text-[#1C1C1E] tracking-tight">Welcome back</h2>
              <p className="text-[#6B7280] text-sm mt-1">
                Sign in to access the fraud detection dashboard
              </p>
            </div>

            {/* Error message */}
            {error && step === 'login' && (
              <div className="mb-4 flex items-start gap-2.5 p-3.5 bg-red-50 border border-red-200 rounded-xl">
                <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-red-700 leading-relaxed">{error}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              {/* Email */}
              <div>
                <label className="block text-xs font-semibold text-[#374151] mb-1.5 uppercase tracking-wide">
                  Email Address
                </label>
                <div className="relative group">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#9CA3AF] group-focus-within:text-[#1A3C5E] transition-colors" />
                  <input
                    id="login-email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full pl-11 pr-4 py-3 bg-[#F9FAFB] border border-[#E5E7EB] rounded-xl text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1A3C5E]/20 focus:border-[#1A3C5E] transition-all"
                    placeholder="your.email@education.go.ke"
                    required
                  />
                </div>
              </div>

              {/* Password */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <label className="block text-xs font-semibold text-[#374151] uppercase tracking-wide">
                    Password
                  </label>
                  <button
                    type="button"
                    className="text-xs text-[#1A3C5E] hover:text-[#2E7D52] font-medium transition-colors"
                    tabIndex={-1}
                  >
                    Forgot password?
                  </button>
                </div>
                <div className="relative group">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-[18px] h-[18px] text-[#9CA3AF] group-focus-within:text-[#1A3C5E] transition-colors" />
                  <input
                    id="login-password"
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full pl-11 pr-12 py-3 bg-[#F9FAFB] border border-[#E5E7EB] rounded-xl text-sm placeholder:text-[#9CA3AF] focus:outline-none focus:ring-2 focus:ring-[#1A3C5E]/20 focus:border-[#1A3C5E] transition-all"
                    placeholder="••••••••"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#9CA3AF] hover:text-[#6B7280] transition-colors"
                    tabIndex={-1}
                  >
                    {showPassword ? (
                      <EyeOff className="w-[18px] h-[18px]" />
                    ) : (
                      <Eye className="w-[18px] h-[18px]" />
                    )}
                  </button>
                </div>
              </div>

              {/* Submit */}
              <button
                id="login-submit"
                type="submit"
                disabled={isLoading}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#1A3C5E] to-[#234d74] text-white py-3.5 rounded-xl font-semibold text-sm hover:from-[#234d74] hover:to-[#2E7D52] transition-all duration-300 shadow-lg shadow-[#1A3C5E]/20 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Authenticating…
                  </>
                ) : (
                  <>
                    Sign In
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>

            {/* Footer badge */}
            <div className="mt-10 pt-6 border-t border-[#F3F4F6]">
              <div className="flex items-center justify-center gap-2 text-xs text-[#9CA3AF]">
                <Lock className="w-3.5 h-3.5" />
                <span>256-bit TLS encrypted · Secure Government System</span>
              </div>
            </div>
          </div>

          {/* ──── 2FA Step ──── */}
          <div
            className={`transition-all duration-500 ${
              step === '2fa'
                ? 'opacity-100 translate-x-0'
                : 'opacity-0 translate-x-8 absolute pointer-events-none'
            }`}
          >
            <div className="mb-8">
              <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#1A3C5E] to-[#2E7D52] flex items-center justify-center mb-4 shadow-lg shadow-[#1A3C5E]/20">
                <Fingerprint className="w-7 h-7 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-[#1C1C1E] tracking-tight">
                Two-Factor Authentication
              </h2>
              <p className="text-[#6B7280] text-sm mt-1">
                Enter the 6-digit code from your authenticator app
              </p>
            </div>

            {/* Error message */}
            {error && step === '2fa' && (
              <div className="mb-4 flex items-start gap-2.5 p-3.5 bg-red-50 border border-red-200 rounded-xl">
                <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                <p className="text-xs text-red-700 leading-relaxed">{error}</p>
              </div>
            )}

            <form onSubmit={handle2FA} className="space-y-6">
              {/* OTP Inputs */}
              <div>
                <label className="block text-xs font-semibold text-[#374151] mb-3 uppercase tracking-wide">
                  Verification Code
                </label>
                <div className="flex gap-2.5 justify-between">
                  {otpDigits.map((digit, i) => (
                    <input
                      key={i}
                      id={`otp-${i}`}
                      type="text"
                      inputMode="numeric"
                      maxLength={1}
                      value={digit}
                      onChange={(e) => handleOtpChange(i, e.target.value)}
                      onKeyDown={(e) => handleOtpKeyDown(i, e)}
                      onPaste={i === 0 ? handleOtpPaste : undefined}
                      className="w-12 h-14 border-2 border-[#E5E7EB] rounded-xl text-center text-xl font-bold font-mono text-[#1C1C1E] bg-[#F9FAFB] focus:outline-none focus:ring-2 focus:ring-[#1A3C5E]/20 focus:border-[#1A3C5E] transition-all"
                      required
                    />
                  ))}
                </div>
              </div>

              {/* Info */}
              <div className="flex items-start gap-3 p-3.5 bg-[#F0FDF4] border border-[#BBF7D0] rounded-xl">
                <CheckCircle className="w-4 h-4 text-[#2E7D52] mt-0.5 flex-shrink-0" />
                <p className="text-xs text-[#166534] leading-relaxed">
                  A verification code has been sent to your registered authenticator app. The code
                  expires in <span className="font-semibold">5 minutes</span>.
                </p>
              </div>

              {/* Submit */}
              <button
                id="2fa-submit"
                type="submit"
                disabled={isLoading || otpDigits.some((d) => !d)}
                className="w-full flex items-center justify-center gap-2 bg-gradient-to-r from-[#1A3C5E] to-[#234d74] text-white py-3.5 rounded-xl font-semibold text-sm hover:from-[#234d74] hover:to-[#2E7D52] transition-all duration-300 shadow-lg shadow-[#1A3C5E]/20 disabled:opacity-70 disabled:cursor-not-allowed"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Verifying…
                  </>
                ) : (
                  <>
                    Verify & Continue
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {/* Secondary actions */}
              <div className="flex items-center justify-between text-xs">
                <button
                  type="button"
                  onClick={() => {
                    setStep('login');
                    setOtpDigits(['', '', '', '', '', '']);
                    setError('');
                    setTempToken('');
                  }}
                  className="text-[#6B7280] hover:text-[#1C1C1E] font-medium transition-colors"
                >
                  ← Back to login
                </button>
                <button
                  type="button"
                  className="text-[#1A3C5E] hover:text-[#2E7D52] font-medium transition-colors"
                >
                  Resend code
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
