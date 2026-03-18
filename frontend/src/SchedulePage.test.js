import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import SchedulePage from "./SchedulePage";

jest.mock("./firebase", () => ({
  auth: {
    currentUser: {
      uid: "user-123",
      email: "student@example.com",
    },
  },
}));

jest.mock("react-router-dom", () => ({
  useParams: () => ({}),
}), { virtual: true });

const mockFetch = (url) => {
  if (url.includes("/availability/connected")) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ connected: false }),
    });
  }

  if (url.includes("/users/user-123/courses")) {
    return Promise.resolve({
      ok: true,
      json: async () => [],
    });
  }

  if (url.endsWith("/users")) {
    return Promise.resolve({
      ok: true,
      json: async () => [
        { email: "friend@example.com", full_name: "Friend Student" },
      ],
    });
  }

  if (url.includes("/availability?")) {
    return Promise.resolve({
      ok: true,
      json: async () => ({ availability: {} }),
    });
  }

  return Promise.resolve({
    ok: true,
    json: async () => ([]),
  });
};

describe("SchedulePage", () => {
  beforeEach(() => {
    global.fetch = jest.fn(mockFetch);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test("shows the Google Calendar empty state before a calendar is connected", async () => {
    render(<SchedulePage />);

    expect(
      await screen.findByRole("heading", { name: /connect google calendar to get started/i })
    ).toBeInTheDocument();
    expect(
      screen.getByText(/connect your calendar to sync your busy times/i)
    ).toBeInTheDocument();
  });

  test("shows a validation error when scheduling a meeting with missing required fields", async () => {
    render(<SchedulePage />);

    await screen.findByRole("heading", { name: /connect google calendar to get started/i });

    fireEvent.click(screen.getByRole("button", { name: /\+ schedule meeting/i }));
    fireEvent.click(screen.getByRole("button", { name: /^schedule meeting$/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/please fill in all required fields/i).length).toBeGreaterThan(0);
    });
  });
});
