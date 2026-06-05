import * as React from "react"

import { cn } from "@/lib/utils"

type Variant = "default" | "success" | "destructive" | "muted"

const styles: Record<Variant, string> = {
  default: "bg-primary text-primary-foreground",
  success: "bg-[hsl(var(--success))] text-white",
  destructive: "bg-destructive text-white",
  muted: "bg-muted text-muted-foreground",
}

export function Badge({
  variant = "default",
  className,
  ...props
}: React.HTMLAttributes<HTMLSpanElement> & { variant?: Variant }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium",
        styles[variant],
        className,
      )}
      {...props}
    />
  )
}
