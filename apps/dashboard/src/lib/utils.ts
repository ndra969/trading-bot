import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** Format a monetary value with its unit (USC for cent accounts, else USD). */
export function money(value: number, unit = "USD"): string {
  const sign = value < 0 ? "-" : ""
  return `${sign}${Math.abs(value).toFixed(2)} ${unit}`
}

export function pct(value: number): string {
  return `${value.toFixed(1)}%`
}
