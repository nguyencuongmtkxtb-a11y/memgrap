import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Network, Link2, Clock, FileCode2 } from 'lucide-react'

interface StatsData {
  entityCount: number
  edgeCount: number
  sessionCount: number
  codeFileCount: number
  recentEpisodes: Array<{
    _id: string
    content?: string
    created_at?: string
  }>
  health: { neo4j: string; groupId: string; llmModel: string }
}

const CARDS = [
  { key: 'entityCount' as const, label: 'Entities', icon: Network },
  { key: 'edgeCount' as const, label: 'Facts', icon: Link2 },
  { key: 'sessionCount' as const, label: 'Sessions', icon: Clock },
  { key: 'codeFileCount' as const, label: 'Code Files', icon: FileCode2 },
]

export function StatCards({ stats }: { stats: StatsData }) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        {CARDS.map(({ key, label, icon: Icon }) => (
          <Card key={key} className="bg-card border-border">
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {label}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {stats[key].toLocaleString()}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm font-medium">System Health</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 text-sm">
          <span>
            Neo4j:{' '}
            <Badge
              variant={
                stats.health.neo4j === 'ok' ? 'default' : 'destructive'
              }
            >
              {stats.health.neo4j}
            </Badge>
          </span>
          <span>
            Group:{' '}
            <code className="text-xs bg-muted px-1 rounded">
              {stats.health.groupId}
            </code>
          </span>
          <span>
            LLM:{' '}
            <code className="text-xs bg-muted px-1 rounded">
              {stats.health.llmModel}
            </code>
          </span>
        </CardContent>
      </Card>

      <Card className="bg-card border-border">
        <CardHeader>
          <CardTitle className="text-sm font-medium">Recent Activity</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {stats.recentEpisodes.length === 0 && (
            <p className="text-sm text-muted-foreground">
              No recent activity.
            </p>
          )}
          {stats.recentEpisodes.map((ep) => (
            <div
              key={ep._id}
              className="text-sm border-b border-border pb-2 last:border-0"
            >
              <p className="truncate text-foreground">
                {ep.content ?? '(no content)'}
              </p>
              {ep.created_at && (
                <p className="text-xs text-muted-foreground mt-0.5">
                  {ep.created_at.replace('T', ' ').slice(0, 19)}
                </p>
              )}
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
