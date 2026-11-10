import type { CSSProperties } from 'react';

export type LampTone = 'ok' | 'warn' | 'danger' | 'active' | 'idle';

interface StatusLampProps {
  tone: LampTone;
  label?: string;
  size?: number;
}

export default function StatusLamp({ tone, label, size }: StatusLampProps) {
  const style: CSSProperties | undefined = size
    ? { width: size, height: size, borderRadius: '50%' }
    : undefined;
  return (
    <span className="flex align-center gap-8">
      <span className={`lamp ${tone}`} style={style} aria-hidden="true" />
      {label ? <span className="tiny muted">{label}</span> : null}
    </span>
  );
}
