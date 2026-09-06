/**
 * @vitest-environment happy-dom
 */

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { PasswordInput } from "../components/ui/PasswordInput";
import { PasswordStrength, getPasswordStrength } from "../components/ui/PasswordStrength";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { AuthCard } from "../components/ui/AuthCard";
import { UserMenu } from "../components/UserMenu";
import LoginPage from "../app/login/page";
import SignupPage from "../app/signup/page";
import ForgotPasswordPage from "../app/forgot-password/page";
import ResetPasswordPage from "../app/reset-password/page";

// Mock next/navigation
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/",
}));

// Mock next/link to render simple anchors
vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

describe("Phase 4 Public and Auth UI Components", () => {
  let container: HTMLDivElement;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
  });

  afterEach(() => {
    document.body.removeChild(container);
  });

  it("1. PasswordInput toggles visibility and updates ARIA attributes", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<PasswordInput id="test-pwd" placeholder="Enter password" />);
    });

    const input = container.querySelector("input") as HTMLInputElement;
    const button = container.querySelector("button") as HTMLButtonElement;

    expect(input.type).toBe("password");
    expect(button.getAttribute("aria-pressed")).toBe("false");
    expect(button.getAttribute("aria-label")).toBe("Show password");

    // Click toggle button
    await act(async () => {
      button.click();
    });

    expect(input.type).toBe("text");
    expect(button.getAttribute("aria-pressed")).toBe("true");
    expect(button.getAttribute("aria-label")).toBe("Hide password");
  });

  it("2. PasswordStrength accurately calculates strength tiers", () => {
    expect(getPasswordStrength("").score).toBe(0);
    expect(getPasswordStrength("abc").score).toBe(1);
    expect(getPasswordStrength("abcdefgh").label).toBe("Weak");
    expect(getPasswordStrength("Abcdefgh1").label).toBe("Good");
    expect(getPasswordStrength("Abcdefgh1!@#").label).toBe("Strong");
  });

  it("3. Button renders loading state and disabled properties", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <Button variant="primary" isLoading={true}>
          Submit Action
        </Button>
      );
    });

    const button = container.querySelector("button") as HTMLButtonElement;
    expect(button.disabled).toBe(true);
    expect(container.textContent).toContain("Submit Action");
  });

  it("4. Input renders accessible error message and aria-invalid", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<Input label="Email" error="Invalid email address" />);
    });

    const input = container.querySelector("input") as HTMLInputElement;
    const errorMsg = container.querySelector('[role="alert"]');

    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(errorMsg?.textContent).toBe("Invalid email address");
  });

  it("5. AuthCard renders title, subtitle, and children properly", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(
        <AuthCard title="Test Auth Title" subtitle="Sub header text">
          <div id="auth-child">Child Content</div>
        </AuthCard>
      );
    });

    expect(container.textContent).toContain("Test Auth Title");
    expect(container.textContent).toContain("Sub header text");
    expect(container.querySelector("#auth-child")).not.toBeNull();
  });

  it("6. UserMenu displays username and toggles popover options", async () => {
    const root = createRoot(container);
    const onSettingsMock = vi.fn();

    await act(async () => {
      root.render(
        <UserMenu
          userName="Alice Engineer"
          userEmail="alice@devmind.ai"
          onOpenSettings={onSettingsMock}
        />
      );
    });

    expect(container.textContent).toContain("Alice Engineer");
    expect(container.textContent).toContain("alice@devmind.ai");

    // Click trigger to open menu
    const trigger = container.querySelector("button") as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });

    expect(container.textContent).toContain("SESSION PROFILE");
    expect(container.textContent).toContain("Workspace Settings");
  });

  it("7. LoginPage validates empty email and password inputs", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<LoginPage />);
    });

    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      submitBtn.click();
    });

    expect(container.textContent).toContain("Please enter your email address.");
    expect(container.textContent).toContain("Please enter your password.");
  });

  it("8. SignupPage validates required full name, email, and password length", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<SignupPage />);
    });

    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      submitBtn.click();
    });

    expect(container.textContent).toContain("Please enter your full name.");
    expect(container.textContent).toContain("Please enter your email address.");
    expect(container.textContent).toContain("Please enter a password.");
  });

  // Helper to trigger React controlled input change in Happy DOM
  function setInputValue(input: HTMLInputElement, value: string) {
    const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
      window.HTMLInputElement.prototype,
      "value"
    )?.set;
    if (nativeInputValueSetter) {
      nativeInputValueSetter.call(input, value);
    } else {
      input.value = value;
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.dispatchEvent(new Event("change", { bubbles: true }));
  }

  it("9. ForgotPasswordPage shows pending backend notice upon submission", async () => {
    vi.useFakeTimers();
    const root = createRoot(container);

    await act(async () => {
      root.render(<ForgotPasswordPage />);
    });

    expect(container.textContent).toContain("UI Preview: Backend password reset service is pending.");

    const emailInput = container.querySelector('input[type="email"]') as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(emailInput, "developer@example.com");
    });

    await act(async () => {
      submitBtn.click();
    });

    await act(async () => {
      vi.runAllTimers();
    });

    expect(container.textContent).toContain("Backend password reset service is not yet configured.");
    vi.useRealTimers();
  });

  it("10. ResetPasswordPage validates mismatched passwords", async () => {
    const root = createRoot(container);
    await act(async () => {
      root.render(<ResetPasswordPage />);
    });

    const inputs = container.querySelectorAll('input[type="password"]');
    const pwdInput = inputs[0] as HTMLInputElement;
    const confirmInput = inputs[1] as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(pwdInput, "SecretPassword123!");
      setInputValue(confirmInput, "DifferentPassword123!");
    });

    await act(async () => {
      submitBtn.click();
    });

    expect(container.textContent).toContain("Passwords do not match.");
  });
});
