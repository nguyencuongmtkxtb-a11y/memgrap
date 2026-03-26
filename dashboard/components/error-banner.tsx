export function ErrorBanner({ message }: { message?: string }) {
  return (
    <div className="rounded-md bg-destructive/10 border border-destructive/20 px-4 py-3 text-sm text-destructive">
      {message ?? 'Neo4j unreachable — ensure docker compose is running.'}
    </div>
  )
}
