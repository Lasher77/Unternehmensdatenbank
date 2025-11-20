import * as React from "react";
import { cn } from "@/lib/utils";

const variantStyles: Record<string, string> = {
  default: "bg-primary text-primary-foreground",
  secondary: "bg-secondary text-secondary-foreground",
  outline: "border border-border text-foreground",
  success: "bg-green-100 text-green-800 border border-green-200",
  warning: "bg-yellow-100 text-yellow-800 border border-yellow-200",
  destructive: "bg-red-100 text-red-800 border border-red-200",
  muted: "bg-muted text-muted-foreground"
};

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: keyof typeof variantStyles;
}

export function Badge({ className, variant = "default", ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold",
        variantStyles[variant] ?? variantStyles.default,
        className
      )}
      {...props}
    />
  );
}
