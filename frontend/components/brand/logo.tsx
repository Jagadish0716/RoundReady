import Image from "next/image";

type LogoProps = {
  variant?: "responsive" | "horizontal" | "symbol";
  priority?: boolean;
  className?: string;
};

export function Logo({
  variant = "responsive",
  priority = false,
  className = "",
}: LogoProps) {
  if (variant === "symbol") {
    return (
      <Image
        src="/brand/favicon-32x32.png"
        alt="RoundReady"
        width={32}
        height={32}
        priority={priority}
        className={`h-8 w-8 ${className}`}
      />
    );
  }

  const horizontal = (
    <Image
      src="/brand/roundready-horizontal-logo.png"
      alt="RoundReady"
      width={819}
      height={179}
      priority={priority}
      sizes="(max-width: 639px) 0px, 180px"
      className={`h-auto w-[180px] ${className}`}
    />
  );

  if (variant === "horizontal") return horizontal;

  return (
    <>
      <span className="sm:hidden">
        <Logo variant="symbol" priority={priority} className={className} />
      </span>
      <span className="hidden sm:inline-block">{horizontal}</span>
    </>
  );
}
