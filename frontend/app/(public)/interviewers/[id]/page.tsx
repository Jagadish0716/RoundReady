import { PublicInterviewerProfile } from "@/components/public/public-interviewer-profile";

export default async function PublicInterviewerPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <PublicInterviewerProfile id={id} />;
}
