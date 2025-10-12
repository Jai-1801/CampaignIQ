import { ReactNode } from 'react';
import { cn } from '@/lib/utils';

interface StatsCardProps {
  label: string;
  value: string;
  icon: ReactNode;
  trend?: {
    value: string;
    positive: boolean;
  };
  className?: string;
}

export const StatsCard = ({ label, value, icon, trend, className }: StatsCardProps) => {
  return (
    <div className={cn(
      "gradient-card rounded-2xl p-6 shadow-smooth hover-lift",
      className
    )}>
      <div className="flex items-start justify-between mb-4">
        <div className="p-3 rounded-xl bg-primary/10 text-primary">
          {icon}
        </div>
        {trend && (
          <div className={cn(
            "text-xs font-medium px-2 py-1 rounded-full",
            trend.positive ? "bg-green-500/10 text-green-600" : "bg-red-500/10 text-red-600"
          )}>
            {trend.positive ? '+' : '-'}{trend.value}
          </div>
        )}
      </div>
      <div className="space-y-1">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-3xl font-bold text-foreground">{value}</p>
      </div>
    </div>
  );
};
