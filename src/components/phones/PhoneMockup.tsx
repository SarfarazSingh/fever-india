import type { ReactNode } from "react";

export function PhoneMockup({ children, label }: { children: ReactNode; label: string }) {
  return (
    <div className="mx-auto w-full max-w-[340px]">
      <div className="rounded-[32px] border border-white/15 bg-ink p-2 shadow-[0_30px_80px_rgba(0,0,0,0.45)]">
        <div className="overflow-hidden rounded-[26px] bg-[#071018]">
          <div className="flex justify-center bg-black pt-2" aria-hidden="true">
            <div className="h-4 w-24 rounded-b-2xl bg-[#0b0b0d]" />
          </div>
          <div className="h-[420px] max-h-[46vh] overflow-hidden">{children}</div>
        </div>
      </div>
      <p className="mt-3 text-center text-[14px] text-soft">{label}</p>
    </div>
  );
}
