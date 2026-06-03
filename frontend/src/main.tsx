import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";

const rootElement = document.getElementById("root");
if (!rootElement) throw new Error("Root element #root not found");
ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <div>Adjents</div>
  </React.StrictMode>
);
