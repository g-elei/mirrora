import React from "react";
import { createRoot } from "react-dom/client";
import MirroraCompanion from "./MirroraCompanion";
import "./index.css";

const root = document.getElementById("root");
if (!root) throw new Error("root element missing");
createRoot(root).render(<MirroraCompanion />);