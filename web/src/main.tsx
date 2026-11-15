/** Starts the interface: the typeface, the styles, then the app itself. */
import "@fontsource-variable/hanken-grotesk";

import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/shell.css";
import "./styles/home.css";
import "./styles/viewer.css";
import "./styles/details.css";
import "./styles/skyhero.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("The page is missing its #root element.");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
