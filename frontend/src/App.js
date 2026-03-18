import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from "react-router-dom";
import LoginPage from "./LoginPage";
import HomePage from "./HomePage";
import SchedulePage from "./SchedulePage";
import ChatPage from "./ChatPage";
import ResourcesPage from "./ResourcesPage";
import DashboardPage from "./DashboardPage";
import ProtectedRoute from "./ProtectedRoute";
import Navbar from "./Navbar";
import ClassHeader from "./ClassHeader";

// Layout for Global Pages (Home, Dashboard, Discussion)
const GlobalLayout = () => (
  <div className="page with-navbar">
    <Navbar />
    <Outlet />
  </div>
);

// Layout for Class Pages (with Navbar + Class Header + Secondary Nav)
const ClassLayout = () => (
  <div className="page with-navbar">
    <Navbar />
    <ClassHeader />
    <div className="page-content">
      <Outlet />
    </div>
  </div>
);

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LoginPage />} />

        {/* Global Pages with Top Navbar Only */}
        <Route element={<ProtectedRoute><GlobalLayout /></ProtectedRoute>}>
          <Route path="/home" element={<HomePage />} />
          <Route path="/dashboard" element={<DashboardPage isClassScoped={false} />} />
          <Route path="/inbox" element={<ChatPage isGlobal={true} />} />
        </Route>

        {/* Class Pages with Navbar + Class Header + Secondary Nav */}
        <Route element={<ProtectedRoute><ClassLayout /></ProtectedRoute>}>
          <Route path="/class/:courseId/summary" element={<DashboardPage isClassScoped={true} />} />
          <Route path="/class/:courseId/resources" element={<ResourcesPage />} />
          <Route path="/class/:courseId/chat" element={<ChatPage isGlobal={false} />} />
          <Route path="/class/:courseId/schedule" element={<SchedulePage />} />
        </Route>

        <Route path="*" element={<Navigate to="/home" />} />
      </Routes>
    </Router>
  );
}

export default App;
