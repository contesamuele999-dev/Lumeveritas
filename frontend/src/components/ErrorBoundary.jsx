import { Component } from "react";

/* Senza questo, un errore di render lasciava una pagina completamente bianca:
   l'utente non capiva se il sito fosse rotto o la connessione caduta. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // eslint-disable-next-line no-console
    console.error("Errore di render:", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    const it = (document.documentElement.lang || "it") === "it";
    return (
      <div className="min-h-[60vh] flex flex-col items-center justify-center gap-4 px-6 text-center" data-testid="error-boundary">
        <div className="font-mono-caps text-accent">{it ? "QUALCOSA È ANDATO STORTO" : "SOMETHING WENT WRONG"}</div>
        <h1 className="font-serif-display text-3xl md:text-5xl leading-tight max-w-2xl">
          {it ? "Questa pagina non è riuscita a caricarsi." : "This page failed to load."}
        </h1>
        <p className="text-muted-foreground max-w-md">
          {it
            ? "Il resto del sito funziona. Ricarica la pagina: se il problema resta, riprova tra qualche minuto."
            : "The rest of the site still works. Reload the page; if it persists, try again in a few minutes."}
        </p>
        <div className="flex flex-wrap gap-3 justify-center">
          <button
            data-testid="error-reload"
            onClick={() => window.location.reload()}
            className="h-11 px-5 bg-foreground text-background hover:bg-accent transition-colors font-mono-caps"
          >
            {it ? "Ricarica" : "Reload"}
          </button>
          <button
            data-testid="error-home"
            onClick={() => { window.location.href = "/"; }}
            className="h-11 px-5 border border-foreground hover:bg-secondary transition-colors font-mono-caps"
          >
            {it ? "Torna alle notizie" : "Back to the news"}
          </button>
        </div>
      </div>
    );
  }
}
