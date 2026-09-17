export function FounderPhoto() {
  return (
    <div className="relative flex aspect-[4/5] w-full max-w-sm items-center justify-center overflow-hidden rounded-3xl border border-blue-100 bg-gradient-to-br from-blue-100 via-white to-indigo-100 text-center shadow-[0_25px_60px_-35px_rgba(30,64,175,0.45)]">
      <div className="px-8">
        <span className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-blue-600 text-2xl font-bold text-white shadow-lg">
          JV
        </span>
        <p className="mt-4 font-semibold text-slate-800">Jagadish</p>
        <p className="mt-1 text-sm text-slate-600">Founder, RoundReady</p>
      </div>
    </div>
  );
}
