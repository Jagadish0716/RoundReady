import { afterEach, describe, expect, it, vi } from "vitest";

import { openRazorpayCheckout } from "@/lib/payments/razorpay";

const checkout = {
  key_id: "rzp_test_roundready",
  order_id: "order_test_1",
  amount: 20000,
  currency: "INR",
};

describe("Razorpay Checkout", () => {
  afterEach(() => {
    delete window.Razorpay;
    vi.restoreAllMocks();
  });

  it.each([
    ["submitted", "success"],
    ["dismissed", "dismiss"],
    ["failed", "failure"],
  ] as const)(
    "reports %s without trusting it as capture",
    async (expected, event) => {
      let options:
        | ConstructorParameters<NonNullable<typeof window.Razorpay>>[0]
        | undefined;
      let failed: (() => void) | undefined;
      const open = vi.fn(() => {
        if (event === "success") options?.handler();
        if (event === "dismiss") options?.modal.ondismiss();
        if (event === "failure") failed?.();
      });
      window.Razorpay = class {
        constructor(value: NonNullable<typeof options>) {
          options = value;
        }
        open = open;
        on(_name: "payment.failed", handler: () => void) {
          failed = handler;
        }
      };

      await expect(openRazorpayCheckout(checkout)).resolves.toBe(expected);
      expect(options).toMatchObject({
        key: checkout.key_id,
        order_id: checkout.order_id,
        amount: 20000,
        currency: "INR",
        name: "RoundReady",
      });
      expect(open).toHaveBeenCalledOnce();
    },
  );
});
