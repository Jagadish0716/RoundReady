import { PublicDiscovery } from "@/components/public/public-discovery";

export default function CandidateInterviewsPage() {
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <PublicDiscovery authenticated />
    </div>
  );
}
