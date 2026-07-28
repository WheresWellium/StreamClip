interface BrandBlockProps {
  title: string;
  subtitle?: string;
  logoSrc?: string;
  showLogoMark: boolean;
  accentColor: string;
}

/** Matches the header mark — hard frame, no soft bloom. */
function LogoMark({ accentColor }: { accentColor: string }) {
  return (
    <span
      className="sc-loading__mark"
      style={{ borderColor: accentColor, color: accentColor }}
      aria-hidden="true"
    >
      <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
        <path d="M2 21l21-9L2 3v7l15 2-15 2z" />
      </svg>
    </span>
  );
}

export function BrandBlock({
  title,
  subtitle,
  logoSrc,
  showLogoMark,
  accentColor,
}: BrandBlockProps) {
  return (
    <div className="sc-loading__brand">
      {logoSrc ? (
        // eslint-disable-next-line @next/next/no-img-element -- static brand asset
        <img className="sc-loading__logo" src={logoSrc} alt="" />
      ) : showLogoMark ? (
        <LogoMark accentColor={accentColor} />
      ) : null}
      <h1 className="sc-loading__title">{title}</h1>
      {subtitle ? <p className="sc-loading__subtitle">{subtitle}</p> : null}
    </div>
  );
}
