import React from "react";
import ReactDOM from "react-dom/client";
import "@/index.css";
import App from "@/App";

/* Qui c'era un QueryClientProvider di @tanstack/react-query: nessun componente usa
   useQuery, quindi la libreria finiva nel bundle senza fare nulla. Le chiamate passano
   tutte da axios in @/lib/api. */

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  });
}
