interface BadgeProps {
  children: React.ReactNode;
  variant?: "green" | "red" | "amber" | "blue" | "neutral";
}

export function Badge({ children, variant = "neutral" }: BadgeProps) {
  return <span className={`badge badge-${variant}`}>{children}</span>;
}
