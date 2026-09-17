const CHECKOUT_SCRIPT = "https://checkout.razorpay.com/v1/checkout.js";

type CheckoutOutcome = "submitted" | "dismissed" | "failed";

interface RazorpayOptions {
  key: string;
  order_id: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  handler(): void;
  modal: { ondismiss(): void };
  theme: { color: string };
}

interface RazorpayInstance {
  open(): void;
  on(event: "payment.failed", handler: () => void): void;
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => RazorpayInstance;
  }
}

let scriptPromise: Promise<void> | null = null;

export function loadRazorpayCheckout(): Promise<void> {
  if (typeof window === "undefined")
    return Promise.reject(new Error("Checkout requires a browser"));
  if (window.Razorpay) return Promise.resolve();
  if (scriptPromise) return scriptPromise;

  scriptPromise = new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      `script[src="${CHECKOUT_SCRIPT}"]`,
    );
    const script = existing ?? document.createElement("script");
    const loaded = () =>
      window.Razorpay
        ? resolve()
        : reject(new Error("Razorpay Checkout did not initialize"));
    script.addEventListener("load", loaded, { once: true });
    script.addEventListener(
      "error",
      () => reject(new Error("Razorpay Checkout could not be loaded")),
      { once: true },
    );
    if (!existing) {
      script.src = CHECKOUT_SCRIPT;
      script.async = true;
      document.head.appendChild(script);
    }
  }).catch((error) => {
    scriptPromise = null;
    throw error;
  });
  return scriptPromise!;
}

export async function openRazorpayCheckout(checkout: {
  key_id: string;
  order_id: string;
  amount: number;
  currency: string;
}): Promise<CheckoutOutcome> {
  await loadRazorpayCheckout();
  return new Promise((resolve, reject) => {
    if (!window.Razorpay) {
      reject(new Error("Razorpay Checkout is unavailable"));
      return;
    }
    let settled = false;
    const finish = (outcome: CheckoutOutcome) => {
      if (settled) return;
      settled = true;
      resolve(outcome);
    };
    const instance = new window.Razorpay({
      key: checkout.key_id,
      order_id: checkout.order_id,
      amount: checkout.amount,
      currency: checkout.currency,
      name: "RoundReady",
      description: "Mock interview session",
      handler: () => finish("submitted"),
      modal: { ondismiss: () => finish("dismissed") },
      theme: { color: "#2563eb" },
    });
    instance.on("payment.failed", () => finish("failed"));
    instance.open();
  });
}
