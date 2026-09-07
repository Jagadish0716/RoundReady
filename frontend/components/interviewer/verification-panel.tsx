"use client";

import { useCallback, useEffect, useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiClientError } from "@/lib/api/client";
import {
  getOwnVerification,
  saveVerificationEvidence,
  submitVerification,
} from "@/lib/api/interviewer";
import type { EvidenceType, VerificationDetail } from "@/types/interviewer";

const evidenceFields: Array<[EvidenceType, string, string]> = [
  ["linkedin", "LinkedIn URL", "https://www.linkedin.com/in/…"],
  ["company_email", "Company email", "you@company.com"],
  ["github_or_portfolio", "GitHub or portfolio URL", "https://…"],
  [
    "supporting_document",
    "Private document reference (optional)",
    "private-object://…",
  ],
];

export function VerificationPanel() {
  const { request } = useAuth();
  const [detail, setDetail] = useState<VerificationDetail | null>(null);
  const [values, setValues] = useState<Partial<Record<EvidenceType, string>>>(
    {},
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const current = await getOwnVerification(request);
      setDetail(current);
      setValues(
        Object.fromEntries(
          current.evidence.map((item) => [
            item.evidence_type,
            item.value_reference,
          ]),
        ),
      );
    } catch (caught) {
      if (!(caught instanceof ApiClientError && caught.status === 404))
        setError(
          caught instanceof Error
            ? caught.message
            : "Unable to load verification.",
        );
    }
  }, [request]);

  useEffect(() => {
    let active = true;
    getOwnVerification(request)
      .then((current) => {
        if (!active) return;
        setDetail(current);
        setValues(
          Object.fromEntries(
            current.evidence.map((item) => [
              item.evidence_type,
              item.value_reference,
            ]),
          ),
        );
      })
      .catch((caught: unknown) => {
        if (
          active &&
          !(caught instanceof ApiClientError && caught.status === 404)
        )
          setError(
            caught instanceof Error
              ? caught.message
              : "Unable to load verification.",
          );
      });
    return () => {
      active = false;
    };
  }, [request]);

  async function save(type: EvidenceType) {
    const value = values[type]?.trim();
    if (!value) return;
    setBusy(type);
    setError(null);
    try {
      setDetail(await saveVerificationEvidence(request, type, value));
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to save evidence.",
      );
    } finally {
      setBusy(null);
    }
  }

  async function submit() {
    setBusy("submit");
    setError(null);
    try {
      await submitVerification(request);
      await load();
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : "Unable to submit verification.",
      );
    } finally {
      setBusy(null);
    }
  }

  if (!detail) return null;
  const locked = detail.status === "verified" || detail.status === "suspended";

  return (
    <section
      className="space-y-4 rounded-lg border bg-white p-5"
      aria-labelledby="verification-heading"
    >
      <div>
        <h2 id="verification-heading" className="text-lg font-semibold">
          Verification
        </h2>
        <p className="text-sm text-slate-600">
          Status:{" "}
          <span className="font-medium uppercase">
            {detail.status.replace("_", " ")}
          </span>
        </p>
      </div>
      {(detail.rejection_reason || detail.suspension_reason) && (
        <p
          role="status"
          className="rounded-md bg-amber-50 p-3 text-sm text-amber-900"
        >
          {detail.rejection_reason ?? detail.suspension_reason}
        </p>
      )}
      <div className="grid gap-4 sm:grid-cols-2">
        {evidenceFields.map(([type, label, placeholder]) => (
          <div key={type}>
            <Label htmlFor={`verification-${type}`}>{label}</Label>
            <div className="mt-2 flex gap-2">
              <Input
                id={`verification-${type}`}
                value={values[type] ?? ""}
                placeholder={placeholder}
                disabled={locked || busy !== null}
                onChange={(event) =>
                  setValues((current) => ({
                    ...current,
                    [type]: event.target.value,
                  }))
                }
              />
              <Button
                type="button"
                variant="outline"
                disabled={locked || busy !== null || !values[type]?.trim()}
                onClick={() => void save(type)}
              >
                Save
              </Button>
            </div>
            <p className="mt-1 text-xs text-slate-500">
              Review:{" "}
              {detail.evidence.find((item) => item.evidence_type === type)
                ?.status ?? "not submitted"}
            </p>
          </div>
        ))}
      </div>
      <p className="text-xs text-slate-500">
        Contact, professional evidence, and a manual screening call are reviewed
        separately. Self-entered details do not grant verification.
      </p>
      {error && (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {(detail.status === "pending" || detail.status === "rejected") && (
        <Button
          type="button"
          disabled={busy !== null}
          onClick={() => void submit()}
        >
          {busy === "submit" ? "Submitting…" : "Submit for review"}
        </Button>
      )}
    </section>
  );
}
