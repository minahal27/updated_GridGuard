import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { GridPulse } from "./Common";

export function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <CenteredPulse />;
  if (!user) return <Navigate to="/welcome" replace />;
  return children;
}

export function RequireAdmin({ children }) {
  const { user, loading, isAdmin } = useAuth();
  if (loading) return <CenteredPulse />;
  if (!user) return <Navigate to="/welcome" replace />;
  if (!isAdmin) return <Navigate to="/" replace />;
  return children;
}

function CenteredPulse() {
  return (
    <div className="flex items-center justify-center" style={{ minHeight: "100vh" }}>
      <GridPulse label="Authenticating" />
    </div>
  );
}
