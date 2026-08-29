import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

// Generare un briefing richiede decine di secondi, e su istanza gratuita si somma il
// risveglio del backend: un limite basso taglierebbe risposte valide. Serve però un
// limite, altrimenti una richiesta persa lascia lo scheletro di caricamento a girare
// per sempre e l'app sembra bloccata.
export const api = axios.create({ baseURL: API, timeout: 120000 });

api.interceptors.request.use((config) => {
  const t = localStorage.getItem("lv_token");
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});
