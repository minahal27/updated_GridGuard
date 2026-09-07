import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { DatasetProvider } from "./context/DatasetContext";
import { RequireAuth, RequireAdmin } from "./components/RouteGuards";
import Layout from "./components/Layout";

import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import DatasetsPage from "./pages/DatasetsPage";
import AnomaliesPage from "./pages/AnomaliesPage";
import ConsumerDetailPage from "./pages/ConsumerDetailPage";
import AlertsPage from "./pages/AlertsPage";
import ReportsPage from "./pages/ReportsPage";
import MLModelsPage from "./pages/MLModelsPage";
import ThresholdsPage from "./pages/ThresholdsPage";
import LogsPage from "./pages/LogsPage";
import SettingsPage from "./pages/SettingsPage";
import FeedersPage from "./pages/FeedersPage";

import DataFiltersPage from "./pages/DataFiltersPage";

import SplashPage from "./pages/SplashPage";

function AuthedApp({ children }) {
  return (
    <RequireAuth>
      <DatasetProvider>{children}</DatasetProvider>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/welcome" element={<SplashPage />} />
          <Route path="/login" element={<LoginPage />} />

          <Route
            element={
              <AuthedApp>
                <Layout />
              </AuthedApp>
            }
          >
            <Route path="/" element={<DashboardPage />} />
            <Route path="/filters" element={<DataFiltersPage />} />
            <Route path="/datasets" element={<DatasetsPage />} />
            <Route path="/anomalies" element={<AnomaliesPage />} />
            <Route path="/feeders" element={<FeedersPage />} />
            <Route path="/consumers/:datasetId/:consumerId" element={<ConsumerDetailPage />} />
            <Route path="/alerts" element={<AlertsPage />} />
            <Route path="/reports" element={<ReportsPage />} />
            <Route path="/settings" element={<SettingsPage />} />

            <Route
              path="/models"
              element={
                <RequireAdmin>
                  <MLModelsPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/thresholds"
              element={
                <RequireAdmin>
                  <ThresholdsPage />
                </RequireAdmin>
              }
            />
            <Route
              path="/logs"
              element={
                <RequireAdmin>
                  <LogsPage />
                </RequireAdmin>
              }
            />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
