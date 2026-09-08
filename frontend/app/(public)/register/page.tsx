import { Suspense } from "react";

import { RegisterForm } from "@/components/auth/register-form";
import { LoadingState } from "@/components/states/loading-state";

export default function RegisterPage() {
  return (
    <Suspense fallback={<LoadingState />}>
      <RegisterForm />
    </Suspense>
  );
}
