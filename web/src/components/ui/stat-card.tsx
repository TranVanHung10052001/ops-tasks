interface StatCardProps {
  label: string;
  value: number | string;
  sub?: string;
  accent?: "default" | "red" | "orange" | "green" | "blue";
  icon?: React.ReactNode;
}

const accentBorder: Record<string, string> = {
  default: "border-gray-200",
  red:     "border-red-300",
  orange:  "border-orange-300",
  green:   "border-green-300",
  blue:    "border-blue-300",
};

const accentValue: Record<string, string> = {
  default: "text-gray-900",
  red:     "text-red-600",
  orange:  "text-orange-600",
  green:   "text-green-600",
  blue:    "text-blue-600",
};

export default function StatCard({
  label,
  value,
  sub,
  accent = "default",
  icon,
}: StatCardProps) {
  return (
    <div className={`bg-white border rounded-lg p-4 ${accentBorder[accent]}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</p>
          <p className={`text-2xl font-bold mt-1 tabular-nums ${accentValue[accent]}`}>{value}</p>
          {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
        </div>
        {icon && (
          <div className="text-gray-300 mt-0.5">{icon}</div>
        )}
      </div>
    </div>
  );
}
