"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function PasswordField({
  id,
  label,
  value,
  error,
  disabled,
  icon,
  onChange,
}: {
  id: string;
  label: string;
  value: string;
  error?: string;
  disabled: boolean;
  icon?: ReactNode;
  onChange(value: string): void;
}) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        {icon ? (
          <span className="pointer-events-none absolute top-1/2 left-4 z-10 -translate-y-1/2 text-slate-400 [&>svg]:h-5 [&>svg]:w-5">
            {icon}
          </span>
        ) : null}
        <Input
          id={id}
          name={id}
          type={visible ? "text" : "password"}
          value={value}
          disabled={disabled}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${id}-error` : undefined}
          autoComplete="current-password"
          placeholder="Enter your password"
          className={`h-14 rounded-xl border-slate-200 pr-12 text-base focus-visible:border-blue-500 focus-visible:ring-blue-500/20 ${icon ? "pl-12" : ""}`}
          onChange={(event) => onChange(event.target.value)}
        />
        <Button
          type="button"
          variant="outline"
          size="sm"
          disabled={disabled}
          aria-label={visible ? "Hide password" : "Show password"}
          className="absolute top-1/2 right-1 h-10 w-10 -translate-y-1/2 border-0 bg-transparent px-0 text-slate-500 hover:bg-blue-50 hover:text-blue-700"
          onClick={() => setVisible((current) => !current)}
        >
          {visible ? <EyeOff aria-hidden /> : <Eye aria-hidden />}
        </Button>
      </div>
      {error ? (
        <p id={`${id}-error`} className="text-sm text-red-700">
          {error}
        </p>
      ) : null}
    </div>
  );
}
