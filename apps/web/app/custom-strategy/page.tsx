import CustomStrategyEditor from "@/components/CustomStrategyEditor";

export default function CustomStrategyPage() {
  return (
    <main className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-8">
      <div>
        <h1 className="text-xl font-semibold text-ink">Stratégie custom</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Écris ta propre stratégie en Python (contrat{" "}
          <code className="rounded bg-bg-raised px-1 py-0.5 text-xs">generate_signals(df, params)</code>{" "}
          en mode vectorisé, ou{" "}
          <code className="rounded bg-bg-raised px-1 py-0.5 text-xs">on_bar(context, bar)</code> en
          mode event-driven). Le code est exécuté dans un sandbox isolé (subprocess séparé, imports
          restreints à pandas/numpy/pandas-ta-classic, sans accès réseau ni disque, CPU/mémoire/temps
          plafonnés) — aucune API n&apos;est jamais appelée en direct.
        </p>
      </div>
      <CustomStrategyEditor />
    </main>
  );
}