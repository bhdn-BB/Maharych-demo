import { describe, expect, it } from "vitest";

import { loginSchema, registerSchema } from "@/lib/auth-schemas";

// The Go API enforces the same rule since lab 6 (auth.ValidatePassword):
// 8+ characters, an upper-case letter and a digit. Keep both in sync.
const valid = { email: "user@example.com", password: "Secret-Pass1", confirmPassword: "Secret-Pass1" };

function errorsFor(values: Partial<typeof valid>) {
  const result = registerSchema.safeParse({ ...valid, ...values });
  return result.success ? {} : result.error.flatten().fieldErrors;
}

describe("registerSchema", () => {
  it("accepts a policy-compliant password", () => {
    expect(registerSchema.safeParse(valid).success).toBe(true);
  });

  it.each([
    ["too short", "Abcde1", "at least 8 characters"],
    ["no upper-case letter", "lowercase1", "uppercase letter"],
    ["no digit", "NoDigitsHere", "one number"],
  ])("rejects a password that is %s", (_label, password, message) => {
    const errors = errorsFor({ password, confirmPassword: password });
    expect(errors.password?.join(" ")).toContain(message);
  });

  it("reports a mismatched confirmation on the confirmation field", () => {
    const errors = errorsFor({ confirmPassword: "Secret-Pass2" });
    expect(errors.confirmPassword).toEqual(["Passwords don't match"]);
    expect(errors.password).toBeUndefined();
  });

  it("rejects a malformed email", () => {
    expect(errorsFor({ email: "not-an-email" }).email).toEqual(["Please enter a valid email"]);
  });
});

describe("loginSchema", () => {
  it("does not apply the sign-up policy so legacy accounts can still sign in", () => {
    expect(loginSchema.safeParse({ email: "user@example.com", password: "1" }).success).toBe(true);
  });

  it("requires a password", () => {
    const result = loginSchema.safeParse({ email: "user@example.com", password: "" });
    expect(result.success).toBe(false);
  });
});
