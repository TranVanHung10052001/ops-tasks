// Ahamove brand lockup — orange motion mark + wordmark.
// Inline SVG so it inherits theme colors and needs no asset file.

export function AhaMark({ size = 22 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      className="shrink-0"
    >
      <rect width="24" height="24" rx="6" fill="#F55F00" />
      {/* double chevron — speed / forward / delivery */}
      <path
        d="M7 7.5 L11.5 12 L7 16.5"
        stroke="#FFFFFF"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M12.5 7.5 L17 12 L12.5 16.5"
        stroke="#FFFFFF"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.55"
      />
    </svg>
  );
}

export default function Logo() {
  return (
    <div className="flex items-center gap-2">
      <AhaMark size={22} />
      <span className="font-display text-md font-semibold tracking-tight text-text-primary leading-none">
        Aha<span className="text-accent-amber">move</span>
      </span>
    </div>
  );
}
