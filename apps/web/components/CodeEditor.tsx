"use client";

import Editor, { type OnMount } from "@monaco-editor/react";

// Sprint 7 -- wrapper fin autour de Monaco (l'éditeur de VS Code), thémé pour
// coller à la palette "terminal de marché" du reste du projet (voir
// tailwind.config.ts) plutôt que le thème clair par défaut. Volontairement
// minimal : la logique de sauvegarde/test/validation vit dans
// CustomStrategyEditor.tsx, ce composant ne fait que rendre l'éditeur.

interface Props {
  value: string;
  onChange: (value: string) => void;
  height?: string;
  readOnly?: boolean;
}

export default function CodeEditor({ value, onChange, height = "420px", readOnly = false }: Props) {
  const handleMount: OnMount = (editor, monaco) => {
    monaco.editor.defineTheme("probatio-dark", {
      base: "vs-dark",
      inherit: true,
      rules: [],
      colors: {
        "editor.background": "#111720", // bg-panel
        "editor.lineHighlightBackground": "#161d28", // bg-raised
        "editorLineNumber.foreground": "#5b6472", // ink-faint
        "editorCursor.foreground": "#22d3b6", // signal
      },
    });
    monaco.editor.setTheme("probatio-dark");
    editor.updateOptions({ fontSize: 13, fontFamily: "var(--font-mono)" });
  };

  return (
    <div className="overflow-hidden rounded-md border border-border">
      <Editor
        height={height}
        defaultLanguage="python"
        value={value}
        onChange={(v) => onChange(v ?? "")}
        onMount={handleMount}
        options={{
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          readOnly,
          tabSize: 4,
          automaticLayout: true,
          padding: { top: 12, bottom: 12 },
        }}
      />
    </div>
  );
}