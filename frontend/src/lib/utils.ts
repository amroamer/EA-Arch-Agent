import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind class merger — shadcn convention. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
