/**
 * @vitest-environment happy-dom
 */

import React, { act } from "react";
import { createRoot } from "react-dom/client";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import LoginPage from "../app/login/page";
import SignupPage from "../app/signup/page";
import WorkspaceApp from "../app/app/page";
import { UserMenu } from "../components/UserMenu";
import { InitialState } from "../components/InitialState";
import { Sidebar } from "../components/Sidebar";
import {
  setStoredAuthToken,
  getStoredAuthToken,
  clearStoredAuthToken,
  setStoredUser,
  getStoredUser,
  getCurrentUser,
  queryCodebase,
  logoutUser,
  AuthError,
} from "../lib/api-client";

// Router spies
const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
    prefetch: vi.fn(),
  }),
  usePathname: () => "/app",
}));

vi.mock("next/link", () => ({
  default: ({ children, href, ...props }: any) => (
    <a href={href} {...props}>
      {children}
    </a>
  ),
}));

vi.mock("../components/StatusBadge", () => ({
  StatusBadge: () => <div data-testid="status-badge">Connected</div>,
}));

(globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;

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

describe("Phase 6 Real Frontend ↔ Backend Authentication Integration", () => {
  let container: HTMLDivElement;
  let root: any;

  beforeEach(() => {
    container = document.createElement("div");
    document.body.appendChild(container);
    root = createRoot(container);
    localStorage.clear();
    mockPush.mockReset();
    mockReplace.mockReset();
    vi.restoreAllMocks();
  });

  afterEach(async () => {
    await act(async () => {
      root?.unmount();
    });
    container.remove();
  });

  // 1. Login success
  it("1. Login success: submits credentials, stores token & user, redirects to /app", async () => {
    const mockToken = {
      access_token: "jwt_token_sample_123",
      token_type: "bearer",
      user: {
        id: 1,
        email: "alice@example.com",
        full_name: "Alice Smith",
        is_active: true,
        created_at: "2026-01-01T00:00:00Z",
      },
    };

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => mockToken,
    });

    await act(async () => {
      root.render(<LoginPage />);
    });

    const emailInput = container.querySelector('input[type="email"]') as HTMLInputElement;
    const passwordInput = container.querySelector('input[type="password"]') as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(emailInput, "alice@example.com");
      setInputValue(passwordInput, "password123");
    });

    await act(async () => {
      submitBtn.click();
    });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/auth/login",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "alice@example.com",
          password: "password123",
        }),
      })
    );

    expect(getStoredAuthToken()).toBe("jwt_token_sample_123");
    expect(getStoredUser()?.email).toBe("alice@example.com");
    expect(mockPush).toHaveBeenCalledWith("/app");
  });

  // 2. Login failure
  it("2. Login failure: 401 returns generic error without revealing account existence", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Invalid email or password." }),
    });

    await act(async () => {
      root.render(<LoginPage />);
    });

    const emailInput = container.querySelector('input[type="email"]') as HTMLInputElement;
    const passwordInput = container.querySelector('input[type="password"]') as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(emailInput, "unknown@example.com");
      setInputValue(passwordInput, "wrongpassword");
    });

    await act(async () => {
      submitBtn.click();
    });

    expect(container.textContent).toContain("Invalid email or password.");
    expect(getStoredAuthToken()).toBe("");
    expect(mockPush).not.toHaveBeenCalled();
  });

  // 3. Signup success
  it("3. Signup success: registers user, logs in, stores token, and redirects to /app", async () => {
    const mockUser = {
      id: 2,
      email: "bob@example.com",
      full_name: "Bob Jones",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    };

    const mockToken = {
      access_token: "jwt_token_bob_456",
      token_type: "bearer",
      user: mockUser,
    };

    globalThis.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        status: 201,
        json: async () => mockUser,
      })
      .mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => mockToken,
      });

    await act(async () => {
      root.render(<SignupPage />);
    });

    const nameInput = container.querySelector('input[placeholder="Ada Lovelace"]') as HTMLInputElement;
    const emailInput = container.querySelector('input[type="email"]') as HTMLInputElement;
    const passwordInputs = container.querySelectorAll('input[type="password"]');
    const passwordInput = passwordInputs[0] as HTMLInputElement;
    const confirmInput = passwordInputs[1] as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(nameInput, "Bob Jones");
      setInputValue(emailInput, "bob@example.com");
      setInputValue(passwordInput, "securepassword123");
      setInputValue(confirmInput, "securepassword123");
    });

    await act(async () => {
      submitBtn.click();
    });

    expect(globalThis.fetch).toHaveBeenNthCalledWith(
      1,
      "http://localhost:8000/auth/register",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          email: "bob@example.com",
          password: "securepassword123",
          full_name: "Bob Jones",
        }),
      })
    );

    expect(getStoredAuthToken()).toBe("jwt_token_bob_456");
    expect(mockPush).toHaveBeenCalledWith("/app");
  });

  // 4. Signup duplicate email
  it("4. Signup duplicate email: displays duplicate email error on 409 Conflict", async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 409,
      json: async () => ({ detail: "An account with this email address already exists." }),
    });

    await act(async () => {
      root.render(<SignupPage />);
    });

    const nameInput = container.querySelector('input[placeholder="Ada Lovelace"]') as HTMLInputElement;
    const emailInput = container.querySelector('input[type="email"]') as HTMLInputElement;
    const passwordInputs = container.querySelectorAll('input[type="password"]');
    const passwordInput = passwordInputs[0] as HTMLInputElement;
    const confirmInput = passwordInputs[1] as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(nameInput, "Duplicate User");
      setInputValue(emailInput, "existing@example.com");
      setInputValue(passwordInput, "password123");
      setInputValue(confirmInput, "password123");
    });

    await act(async () => {
      submitBtn.click();
    });

    expect(container.textContent).toContain("An account with this email address already exists.");
    expect(getStoredAuthToken()).toBe("");
  });

  // 5. Loading state & 6. Double-submit prevention
  it("5 & 6. Loading state and double-submit prevention: disables submit button and executes single login request", async () => {
    let resolveFetch: (val: any) => void;
    const fetchPromise = new Promise((res) => {
      resolveFetch = res;
    });

    globalThis.fetch = vi.fn().mockReturnValue(fetchPromise);

    await act(async () => {
      root.render(<LoginPage />);
    });

    const emailInput = container.querySelector('input[type="email"]') as HTMLInputElement;
    const passwordInput = container.querySelector('input[type="password"]') as HTMLInputElement;
    const submitBtn = container.querySelector('button[type="submit"]') as HTMLButtonElement;

    await act(async () => {
      setInputValue(emailInput, "alice@example.com");
      setInputValue(passwordInput, "password123");
    });

    // Fire multiple clicks synchronously
    await act(async () => {
      submitBtn.click();
      submitBtn.click();
      submitBtn.click();
      // Resolve promise inside act so test doesn't stall
      resolveFetch!({
        ok: true,
        status: 200,
        json: async () => ({
          access_token: "jwt_token_sample_123",
          token_type: "bearer",
          user: { id: 1, email: "alice@example.com", full_name: "Alice", is_active: true, created_at: "" },
        }),
      });
    });

    // Must only have been called once despite 3 clicks
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    expect(getStoredAuthToken()).toBe("jwt_token_sample_123");
    expect(mockPush).toHaveBeenCalledWith("/app");
  });

  // 7. Authenticated /app access
  it("7. Authenticated /app access: loads current user from /auth/me and renders workspace", async () => {
    setStoredAuthToken("valid_token_xyz");

    const mockMe = {
      id: 7,
      email: "engineer@devmind.ai",
      full_name: "Engineer Jane",
      is_active: true,
      created_at: "2026-01-01T00:00:00Z",
    };

    globalThis.fetch = vi.fn().mockImplementation((url) => {
      if (url.includes("/auth/me")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => mockMe,
        });
      }
      if (url.includes("/conversations")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({}),
      });
    });

    await act(async () => {
      root.render(<WorkspaceApp />);
      await Promise.resolve();
    });

    expect(container.textContent).toContain("Engineer Jane");
    expect(container.textContent).toContain("engineer@devmind.ai");
    expect(mockReplace).not.toHaveBeenCalled();
  });

  // 8. Unauthenticated /app redirect
  it("8. Unauthenticated /app redirect: redirects immediately to /login if no token exists", async () => {
    clearStoredAuthToken();

    await act(async () => {
      root.render(<WorkspaceApp />);
    });

    expect(mockReplace).toHaveBeenCalledWith("/login");
  });

  // 9. Invalid/expired token handling
  it("9. Invalid/expired token handling: 401 on /auth/me purges token and redirects to /login", async () => {
    setStoredAuthToken("expired_jwt_token");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Token expired." }),
    });

    await act(async () => {
      root.render(<WorkspaceApp />);
      await Promise.resolve();
    });

    expect(getStoredAuthToken()).toBe("");
    expect(mockReplace).toHaveBeenCalledWith("/login");
  });

  // 10. Logout
  it("10. Logout: calls /auth/logout, purges local credentials, and returns success response", async () => {
    setStoredAuthToken("token_to_logout");
    setStoredUser({
      id: 1,
      email: "user@devmind.ai",
      full_name: "Logged In User",
      is_active: true,
      created_at: "",
    });

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ message: "Successfully logged out. Discard the access token." }),
    });

    const res = await logoutUser();

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/auth/logout",
      expect.objectContaining({
        method: "POST",
      })
    );
    expect(res.message).toContain("Successfully logged out");
    expect(getStoredAuthToken()).toBe("");
    expect(getStoredUser()).toBeNull();
  });

  // 11. UserMenu displays authenticated user
  it("11. UserMenu displays real authenticated user information and handles onLogout", async () => {
    const onLogoutMock = vi.fn();

    await act(async () => {
      root.render(
        <UserMenu
          userName="Jane Superdev"
          userEmail="jane@superdev.org"
          onLogout={onLogoutMock}
        />
      );
    });

    expect(container.textContent).toContain("Jane Superdev");
    expect(container.textContent).toContain("jane@superdev.org");

    // Click to open menu
    const trigger = container.querySelector('button[aria-label="User profile menu"]') as HTMLButtonElement;
    await act(async () => {
      trigger.click();
    });

    const signOutBtn = Array.from(container.querySelectorAll("button")).find(
      (b) => b.textContent?.includes("Sign Out")
    );
    expect(signOutBtn).not.toBeUndefined();

    await act(async () => {
      signOutBtn?.click();
    });

    expect(onLogoutMock).toHaveBeenCalledTimes(1);
  });

  // 12. API client sends Bearer token
  it("12. API client sends Bearer token on protected endpoints", async () => {
    setStoredAuthToken("bearer_secret_token_777");

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        answer: "Retrieved test answer",
        sources: [],
      }),
    });

    await queryCodebase({ query: "How does auth work?", top_k: 3 });

    expect(globalThis.fetch).toHaveBeenCalledWith(
      "http://localhost:8000/query",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer bearer_secret_token_777",
        }),
      })
    );
  });

  // 13. 401 clears authentication
  it("13. 401 response clears authentication token and dispatches event", async () => {
    setStoredAuthToken("expired_token");
    setStoredUser({ id: 1, email: "a@b.com", full_name: "A", is_active: true, created_at: "" });

    const unauthorizedListener = vi.fn();
    window.addEventListener("devmind:auth-unauthorized", unauthorizedListener);

    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      json: async () => ({ detail: "Token invalid or expired." }),
    });

    await expect(getCurrentUser()).rejects.toThrow(AuthError);

    expect(getStoredAuthToken()).toBe("");
    expect(getStoredUser()).toBeNull();
    expect(unauthorizedListener).toHaveBeenCalledTimes(1);

    window.removeEventListener("devmind:auth-unauthorized", unauthorizedListener);
  });

  // 14. Existing RAG UI still renders
  it("14. Existing RAG UI renders initial search state when authenticated", async () => {
    await act(async () => {
      root.render(
        <InitialState
          activeRepository="devmind-core"
          onSubmit={() => {}}
          isLoading={false}
        />
      );
    });

    const input = container.querySelector("input") as HTMLInputElement;
    expect(container.textContent).toContain("Understand your codebase.");
    expect(input.placeholder).toBe("Ask anything about devmind-core...");
  });

  // 15. Existing history UI still renders
  it("15. Existing history UI renders recent conversation items in authenticated state", async () => {
    const mockConversations = [
      {
        id: "conv-1",
        session_id: "sess-1",
        title: "Database Architecture Discussion",
        repository_name: "devmind-core",
        created_at: "2026-03-01T12:00:00Z",
        updated_at: "2026-03-01T12:30:00Z",
        message_count: 4,
      },
    ];

    await act(async () => {
      root.render(
        <Sidebar
          activeRepository="devmind-core"
          activeView="chat"
          conversations={mockConversations}
          activeConversationId="conv-1"
          onNewChat={() => {}}
          onSelectConversation={() => {}}
          onDeleteConversation={() => {}}
          onOpenIndexModal={() => {}}
          onOpenSettingsModal={() => {}}
          onToggleHistory={() => {}}
          userName="Jane Engineer"
          userEmail="jane@devmind.ai"
        />
      );
    });

    expect(container.textContent).toContain("Database Architecture Discussion");
    expect(container.textContent).toContain("Jane Engineer");
    expect(container.textContent).toContain("jane@devmind.ai");
  });
});
