/** Starts the interface: typefaces, styles, then the app itself. */
import "@fontsource/instrument-serif/400.css";
import "@fontsource/instrument-serif/400-italic.css";
import "@fontsource/instrument-sans/400.css";
import "@fontsource/instrument-sans/500.css";
import "@fontsource/instrument-sans/600.css";
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/500.css";

import "./styles/tokens.css";
import "./styles/base.css";
import "./styles/shell.css";
import "./styles/pages.css";
import "./styles/explore.css";
import "./styles/viewport.css";
import "./styles/panels.css";

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
