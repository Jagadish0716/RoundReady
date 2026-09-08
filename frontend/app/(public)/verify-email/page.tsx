import { Suspense } from "react";

import { VerifyEmail } from "@/components/auth/verify-email";
import { LoadingState } from "@/components/states/loading-state";

export default function VerifyEmailPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <VerifyEmail />
    </Suspense>
  );
}
