# India, Reimagined

An independent, interactive growth-strategy proposal for a Fever India interview. It is not a Fever product, dashboard, or approved plan.

Presented by Sarfaraz Singh Wahad · October 2026.

## Run

```bash
npm install
npm run dev
```

Production check:

```bash
npm test
npm run build
```

## How to present

- Arrow keys or Space move between scenes. F toggles fullscreen. S toggles presenter notes. Escape closes panels.
- The opening state applies a **+15% localization lift** so the discovery scene and the Growth Lab start from the same assumption. **Reset to base case** returns that lift to 0%.
- Partner channel cards, the retention slider, and the localization control all write to one scenario.
- City scores and the 90-day model are synthetic. Published audience figures are confined to scene 02 and the sources appendix. The 84% figure is stated intent, dated 24 June 2026, not a repeat-booking rate.

## Model

`src/lib/financialModel.ts` is the only place the 90-day maths lives. Contribution margin is before marketing spend and partner fees. Repeat probability adds at most one extra booking. The output is a contribution proxy, not lifetime value or company profit.

The India outline is Natural Earth 1:50m, filtered to India and stored locally.
