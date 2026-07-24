export default function BrandPanel() {
  return (
    <aside className="hidden lg:flex w-[43%] flex-shrink-0 flex-col bg-yellow px-12 py-12">
      <div className="flex items-center justify-between font-mono text-sm tracking-caps text-ink">
        <span>DAILY MEAL NOMINATIONS</span>
        <span>EST. 2025</span>
      </div>

      <div className="flex flex-grow flex-col justify-center">
        <h1 className="font-display uppercase leading-[0.95] text-ink text-[clamp(64px,8vw,108px)]">
          What
          <br />
          to eat
          <br />
          <span className="text-outline">Tonight</span> ?
        </h1>
        <p className="mt-8 max-w-[420px] text-lg leading-relaxed text-ink">
          NOMinate learns what you love and nominates one dish a day — then helps you
          cook it or find it nearby.
        </p>
      </div>
    </aside>
  );
}
