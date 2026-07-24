import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import LogInPage from './pages/LogInPage';
import SignUpPage from './pages/SignUpPage';
import ProfileSetupPage from './pages/ProfileSetupPage';
import RecommendationPage from './pages/RecommendationPage';
import CookingPage from './pages/CookingPage';
import TakeoutPage from './pages/TakeoutPage';
import FeedbackPage from './pages/FeedbackPage';

function guarded(element, options) {
  return <ProtectedRoute {...options}>{element}</ProtectedRoute>;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LogInPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/setup" element={guarded(<ProfileSetupPage />, { requireProfile: false })} />
          <Route path="/profile" element={guarded(<ProfileSetupPage edit />)} />
          <Route path="/nominate" element={guarded(<RecommendationPage />)} />
          <Route path="/cooking" element={guarded(<CookingPage />)} />
          <Route path="/takeout" element={guarded(<TakeoutPage />)} />
          <Route path="/feedback" element={guarded(<FeedbackPage />)} />
          <Route path="*" element={<Navigate to="/nominate" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
