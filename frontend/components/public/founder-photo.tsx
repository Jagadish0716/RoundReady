"use client";

import Image from "next/image";
import { useState } from "react";

export function FounderPhoto() {
  const [missing, setMissing] = useState(false);

  return (
    <div className="flex aspect-[4/5] w-full max-w-sm items-center justify-center overflow-hidden rounded-lg border border-neutral-200 bg-neutral-100 text-center">
      {missing ? (
        <div className="px-8 text-sm text-neutral-600">Founder photo</div>
      ) : (
        <Image
          src="/images/founder/jagadish.jpg"
          alt="Jagadish, founder of RoundReady"
          width={320}
          height={400}
          className="h-full w-full object-cover"
          onError={() => setMissing(true)}
        />
      )}
    </div>
  );
}
