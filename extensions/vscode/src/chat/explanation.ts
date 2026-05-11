import type { Detection } from "../types";

const EXPLANATIONS: Record<string, Record<string, string>> = {
  pii: {
    ssn: "This text contains a Social Security Number — a high-value identifier that should never be sent to an LLM.",
    email: "An email address was found. Consider whether sharing it with an external LLM is intended.",
    phone: "A phone number was detected.",
    credit_card: "A credit card number was found — sending it to an LLM is a data-loss risk.",
    default: "Personally identifiable information was detected.",
  },
  injection: {
    default:
      "This text contains a prompt injection attempt — instructions designed to override the LLM's behavior or reveal its system prompt.",
  },
  secrets: {
    api_key: "An API key or token was detected. Sending live credentials to an LLM is a secrets-leakage risk.",
    default: "A secret or credential was detected.",
  },
  toxicity: {
    default: "This text contains language that may violate content policies.",
  },
};

export function explain(d: Detection): string {
  const byDetector = EXPLANATIONS[d.detector];
  if (!byDetector) {
    return `Detection from ${d.detector} detector (type: ${d.type}).`;
  }
  return byDetector[d.type] ?? byDetector["default"] ?? `${d.detector}/${d.type} detected.`;
}
