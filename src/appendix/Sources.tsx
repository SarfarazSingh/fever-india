import { SOURCES } from "../data/evidence";
import { SceneContainer } from "../components/presentation/SceneContainer";

export function Sources() {
  const evidence = SOURCES.filter((item) => item.group === "evidence");
  const hypotheses = SOURCES.filter((item) => item.group === "hypothesis");
  return (
    <SceneContainer scroll>
      <p className="text-[14px] tracking-[0.16em] text-gold uppercase">15 — Appendix</p>
      <h2 className="mt-2 font-display text-[clamp(36px,4vw,60px)] leading-none font-medium">Sources and assumptions</h2>
      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <section className="rounded-3xl border border-fever/40 p-4">
          <h3 className="font-display text-[28px] text-link">Verified public evidence</h3>
          <div className="mt-3 space-y-3">
            {evidence.map((item) => <Card key={item.id} title={item.title} date={item.date} detail={item.detail} href={item.href} />)}
          </div>
        </section>
        <section className="rounded-3xl border border-gold/40 p-4">
          <h3 className="font-display text-[28px] text-gold">Strategy hypotheses</h3>
          <div className="mt-3 space-y-3">
            {hypotheses.map((item) => <Card key={item.id} title={item.title} date={item.date} detail={item.detail} />)}
          </div>
        </section>
      </div>
      <p className="mt-4 text-[15px] text-soft">Historic press releases are not treated as a live inventory or a sales report. Every synthetic figure in the model is marked illustrative.</p>
    </SceneContainer>
  );
}

function Card({ title, date, detail, href }: { title: string; date: string; detail: string; href?: string }) {
  return (
    <article className="border-t border-white/10 pt-3">
      <p className="text-[13px] text-soft">{date}</p>
      <h4 className="font-display text-[18px]">{title}</h4>
      <p className="text-[15px] leading-snug">{detail}</p>
      {href && <a className="text-[15px] text-link underline" href={href} target="_blank" rel="noreferrer">Open</a>}
    </article>
  );
}
