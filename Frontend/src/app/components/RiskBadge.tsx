interface RiskBadgeProps {
  tier: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'EVALUATING' | string;
  className?: string;
}

export function RiskBadge({ tier, className = '' }: RiskBadgeProps) {
  const styles: Record<string, string> = {
    CRITICAL: 'bg-[#C0392B] text-white',
    HIGH: 'bg-[#E8A020] text-white',
    MEDIUM: 'bg-[#2471A3] text-white',
    LOW: 'bg-[#2E7D52] text-white',
    EVALUATING: 'bg-[#6B21A8] text-white animate-pulse',
  };

  const badgeStyle = styles[tier] || 'bg-[#6B7280] text-white';

  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold ${badgeStyle} ${className}`}>
      {tier}
    </span>
  );
}
