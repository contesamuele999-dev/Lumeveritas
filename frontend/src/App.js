import "@/App.css";
import { lazy } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { HelmetProvider } from "react-helmet-async";
import { AuthProvider } from "@/context/AuthContext";
import { LangProvider } from "@/context/LangContext";
import { ExplainProvider } from "@/components/ClickableText";
import AppShell from "@/components/AppShell";
import ScrollToTop from "@/components/ScrollToTop";
import HomePage from "@/pages/HomePage";

/* Solo la home è nel bundle iniziale: le altre pagine arrivano quando servono.
   Prima ogni visitatore scaricava anche profilo, login, salvati e pagina pubblica
   prima di poter leggere la prima notizia. */
const AskPage = lazy(() => import("@/pages/AskPage"));
const SavedPage = lazy(() => import("@/pages/SavedPage"));
const ProfilePage = lazy(() => import("@/pages/ProfilePage"));
const LoginPage = lazy(() => import("@/pages/LoginPage"));
const RegisterPage = lazy(() => import("@/pages/RegisterPage"));
const PublicBriefingPage = lazy(() => import("@/pages/PublicBriefingPage"));

function App() {
  return (
    <HelmetProvider>
      <LangProvider>
        <AuthProvider>
          <ExplainProvider>
            <BrowserRouter>
              <ScrollToTop />
              <Toaster position="top-center" richColors closeButton />
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/ask" element={<AskPage />} />
                  <Route path="/saved" element={<SavedPage />} />
                  <Route path="/profile" element={<ProfilePage />} />
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/s/:id" element={<PublicBriefingPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Route>
              </Routes>
            </BrowserRouter>
          </ExplainProvider>
        </AuthProvider>
      </LangProvider>
    </HelmetProvider>
  );
}

export default App;
