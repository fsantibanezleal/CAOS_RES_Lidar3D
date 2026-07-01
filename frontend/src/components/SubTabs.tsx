// Per-page sub-tabs (ADR-0016: every content page is tabbed, like the reference product). Client-only state.
import { type JSX, useState } from 'react';

export type SubTab = { id: string; label: string; body: JSX.Element };

export function SubTabs({ tabs }: { tabs: SubTab[] }) {
  const [active, setActive] = useState(tabs[0]?.id);
  const cur = tabs.find((t) => t.id === active) ?? tabs[0];
  return (
    <>
      <div className="subtabs" role="tablist">
        {tabs.map((t) => (
          <button key={t.id} role="tab" aria-selected={t.id === active}
            className={'stab' + (t.id === active ? ' on' : '')} onClick={() => setActive(t.id)}>{t.label}</button>
        ))}
      </div>
      <div className="subtab-body">{cur?.body}</div>
    </>
  );
}
