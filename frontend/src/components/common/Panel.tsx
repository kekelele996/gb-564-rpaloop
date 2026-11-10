import type { ReactNode } from 'react';

interface PanelProps {
  kicker?: string;
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  tight?: boolean;
  className?: string;
}

export default function Panel({ kicker, title, actions, children, tight, className }: PanelProps) {
  return (
    <section className={`panel ${className || ''}`}>
      {(kicker || title || actions) && (
        <header className="panel-head">
          <div>
            {kicker ? <div className="panel-kicker">{kicker}</div> : null}
            {title ? <div className="panel-title">{title}</div> : null}
          </div>
          {actions ? <div className="right flex align-center gap-8">{actions}</div> : null}
        </header>
      )}
      <div className={`panel-body ${tight ? 'tight' : ''}`}>{children}</div>
    </section>
  );
}
