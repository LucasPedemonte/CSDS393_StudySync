import { render, screen } from "@testing-library/react";
import App from "./App";

jest.mock("react-router-dom", () => ({
  BrowserRouter: ({ children }) => <div>{children}</div>,
  Routes: ({ children }) => <div>{children}</div>,
  Route: ({ element }) => element ?? null,
  Navigate: () => <div>Navigate</div>,
  Outlet: () => <div>Outlet</div>,
  NavLink: ({ children }) => <div>{children}</div>,
  Link: ({ children }) => <div>{children}</div>,
  useParams: () => ({ courseId: "1" }),
  useNavigate: () => jest.fn(),
  useLocation: () => ({ pathname: "/home" }),
}), { virtual: true });

jest.mock("./LoginPage", () => () => <div>Login Page</div>);
jest.mock("./HomePage", () => () => <div>Home Page</div>);
jest.mock("./SchedulePage", () => () => <div>Schedule Page</div>);
jest.mock("./ChatPage", () => () => <div>Chat Page</div>);
jest.mock("./ResourcesPage", () => () => <div>Resources Page</div>);
jest.mock("./DashboardPage", () => () => <div>Dashboard Page</div>);
jest.mock("./ProtectedRoute", () => ({ children }) => <div>{children}</div>);
jest.mock("./Navbar", () => () => <div>Navbar</div>);
jest.mock("./ClassHeader", () => () => <div>Class Header</div>);

test("renders the application shell", () => {
  render(<App />);

  expect(screen.getByText("Login Page")).toBeInTheDocument();
  expect(screen.getAllByText("Navbar").length).toBeGreaterThan(0);
  expect(screen.getAllByText("Outlet").length).toBeGreaterThan(0);
});
