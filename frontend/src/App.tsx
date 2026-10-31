import { Routes, Route, Link, useLocation } from "react-router-dom";
import TechnicianConsole from "./pages/TechnicianConsole";
import SupervisorDashboard from "./pages/SupervisorDashboard";

export default function App() {
  const location = useLocation();
  const isDashboard = location.pathname === "/dashboard";

  return (
    <div className="min-h-screen flex flex-col">
      <nav className="bg-gray-900 border-b border-gray-800 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xl font-bold tracking-tight text-blue-400">
            AeroLog
          </span>
          <span className="text-xs text-gray-500 hidden sm:inline">
            Aircraft Maintenance Voice Agent
          </span>
        </div>
        <div className="flex gap-1">
          <Link
            to="/"
            className={`px-3 py-1 rounded text-sm ${
              !isDashboard
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Technician
          </Link>
          <Link
            to="/dashboard"
            className={`px-3 py-1 rounded text-sm ${
              isDashboard
                ? "bg-blue-600 text-white"
                : "text-gray-400 hover:text-white"
            }`}
          >
            Dashboard
          </Link>
        </div>
      </nav>
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<TechnicianConsole />} />
          <Route path="/dashboard" element={<SupervisorDashboard />} />
        </Routes>
      </main>
    </div>
  );
}
