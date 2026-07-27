import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { api } from "@/lib/api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchMe = useCallback(async () => {
    const t = localStorage.getItem("lv_token");
    if (!t) { setUser(null); setLoading(false); return; }
    try {
      const { data } = await api.get("/auth/me/full");
      setUser(data);
    } catch (e) {
      localStorage.removeItem("lv_token");
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchMe(); }, [fetchMe]);

  const login = async (email, password) => {
    const { data } = await api.post("/auth/login", { email, password });
    localStorage.setItem("lv_token", data.token);
    await fetchMe();
    return data.user;
  };

  const register = async (email, password, name) => {
    const { data } = await api.post("/auth/register", { email, password, name });
    localStorage.setItem("lv_token", data.token);
    await fetchMe();
    return data.user;
  };

  const logout = () => {
    localStorage.removeItem("lv_token");
    setUser(null);
  };

  const updatePrefs = async (patch) => {
    await api.put("/auth/preferences", patch);
    await fetchMe();
    return user;
  };

  const addCustomTopic = async (label) => {
    const { data } = await api.post("/topics/custom", { label });
    await fetchMe();
    return data;
  };

  const removeCustomTopic = async (key) => {
    await api.delete(`/topics/custom/${encodeURIComponent(key)}`);
    await fetchMe();
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, updatePrefs, addCustomTopic, removeCustomTopic, refresh: fetchMe }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
