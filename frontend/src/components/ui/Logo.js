/*
 * LocalPulse logo mark: the storefront-with-growth-arrow artwork
 * (public/brand/localpulse-logo.png), shown as a rounded app-style tile.
 * Use <LogoMark size={36} /> anywhere the brand icon should appear.
 */
export function LogoMark({ size = 36, className = '' }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src="/brand/localpulse-logo.png"
      alt="LocalPulse"
      width={size}
      height={size}
      draggable={false}
      className={`shrink-0 rounded-[22%] select-none ${className}`}
      style={{ width: size, height: size }}
    />
  );
}

export default LogoMark;
