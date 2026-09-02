export function EmptyState({
  message = "Nothing here yet.",
}: {
  message?: string;
}) {
  return <p className="text-neutral-600">{message}</p>;
}
