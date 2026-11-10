import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router-dom';
import TopBar from '../components/common/TopBar';
import { useAuthStore } from '../stores/auth';
import LoginPage from '../pages/LoginPage';
import ProcessListPage from '../pages/ProcessListPage';
import StepEditorPage from '../pages/StepEditorPage';
import BoardPage from '../pages/BoardPage';
import RunDetailPage from '../pages/RunDetailPage';
import InterventionPage from '../pages/InterventionPage';
import MaterialsPage from '../pages/MaterialsPage';

function RequireAuth() {
  const token = useAuthStore((state) => state.token);
  const location = useLocation();
  if (!token) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return (
    <>
      <TopBar />
      <main>
        <Outlet />
      </main>
    </>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<RequireAuth />}>
        <Route path="/" element={<Navigate to="/processes" replace />} />
        <Route path="/processes" element={<ProcessListPage />} />
        <Route path="/processes/:processId/edit" element={<StepEditorPage />} />
        <Route path="/board" element={<BoardPage />} />
        <Route path="/runs/:runId" element={<RunDetailPage />} />
        <Route path="/interventions" element={<InterventionPage />} />
        <Route path="/materials" element={<MaterialsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/processes" replace />} />
    </Routes>
  );
}
